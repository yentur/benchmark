import yaml
import os
import json
from pathlib import Path
from typing import Dict, Any, List, Callable, Optional
import time
from datetime import datetime
from datasets import load_dataset
import soundfile as sf
import tempfile
from tqdm import tqdm
from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor, as_completed
import multiprocessing as mp

from model import ModelFactory
from whisper_model import WhisperModel
from utils import calculate_wer, calculate_cer, aggregate_metrics, format_duration
from visualizer import BenchmarkVisualizer

def process_single_sample(args):
    """Tek bir sample'ı işle (paralel çalıştırma için)"""
    model_config, sample, benchmark_config = args
    
    try:
        # Model yükle
        from model import ModelFactory
        model = ModelFactory.create(
            model_type=model_config['type'],
            model_path=model_config['path'],
            config=benchmark_config
        )
        model.load_model()
        
        # Transcribe
        result = model.transcribe_with_metrics(sample['audio_path'])
        
        # Metrik hesapla
        from utils import calculate_wer, calculate_cer
        wer = calculate_wer(sample['reference'], result['transcription'])
        cer = calculate_cer(sample['reference'], result['transcription'])
        
        result_entry = {
            'id': sample['id'],
            'reference': sample['reference'],
            'hypothesis': result['transcription'],
            'wer': wer,
            'cer': cer,
            'latency': result['latency'],
            'throughput': result['throughput'],
            'dataset': sample.get('dataset', 'unknown')
        }
        
        # Cleanup
        model.cleanup()
        
        # Temp dosyayı sil
        try:
            os.unlink(sample['audio_path'])
        except:
            pass
        
        return result_entry, None
        
    except Exception as e:
        return None, str(e)

class BenchmarkRunner:
    """Paralel benchmark runner"""
    
    def __init__(self, config_path: str = "config.yaml"):
        with open(config_path, 'r') as f:
            self.config = yaml.safe_load(f)
        
        self.results_dir = Path(self.config['output']['results_dir'])
        self.results_dir.mkdir(exist_ok=True)
        
        self.cache_dir = Path("cache")
        self.cache_dir.mkdir(exist_ok=True)
        
        self.visualizer = BenchmarkVisualizer(str(self.results_dir))
        self.all_results = {}
        self.sample_callback: Optional[Callable] = None
        self.current_status = {
            "status": "idle",
            "current_model": None,
            "current_dataset": None,
            "progress": 0,
            "total": 0,
            "message": "Ready to start"
        }
        
        # CPU sayısı
        self.num_workers = min(mp.cpu_count(), 4)  # Max 4 paralel
        
        # Load cached results
        self._load_cache()
    
    def _load_cache(self):
        """Load cached benchmark results"""
        cache_file = self.cache_dir / "benchmark_cache.json"
        if cache_file.exists():
            try:
                with open(cache_file, 'r', encoding='utf-8') as f:
                    self.all_results = json.load(f)
                print(f"✓ Loaded cached results for {len(self.all_results)} model(s)")
            except Exception as e:
                print(f"Warning: Could not load cache: {e}")
    
    def _save_cache(self):
        """Save current results to cache"""
        cache_file = self.cache_dir / "benchmark_cache.json"
        try:
            with open(cache_file, 'w', encoding='utf-8') as f:
                json.dump(self.all_results, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"Warning: Could not save cache: {e}")
    
    def set_sample_callback(self, callback: Callable):
        """Set callback for sample updates"""
        self.sample_callback = callback
    
    def update_status(self, **kwargs):
        """Update current status"""
        self.current_status.update(kwargs)
        print(f"[STATUS] {self.current_status['message']}")
    
    def load_dataset_samples(self, dataset_config: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Load dataset samples from HuggingFace"""
        self.update_status(
            status="loading_dataset",
            message=f"Loading dataset: {dataset_config['name']}"
        )
        
        dataset = load_dataset(
            dataset_config['path'],
            split=dataset_config['split'],
        )
        
        samples = []
        dataset_subset = dataset
        
        for idx, item in enumerate(tqdm(dataset_subset, desc="Preparing samples")):
            # Save audio to temporary file
            audio_array = item['audio']['array']
            sr = item['audio']['sampling_rate']
            
            temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.wav')
            sf.write(temp_file.name, audio_array, sr)
            
            samples.append({
                'audio_path': temp_file.name,
                'reference': item.get('sentence', item.get('text', '')),
                'id': f"{dataset_config['name']}_{idx}",
                'dataset': dataset_config['name']
            })
        
        print(f"✓ Loaded {len(samples)} samples from {dataset_config['name']}")
        return samples
    
    def benchmark_model_parallel(self, model_config: Dict[str, Any]) -> Dict[str, Any]:
        """Benchmark a single model with PARALLEL processing"""
        model_name = model_config['name']
        
        # Check if already in cache
        if model_name in self.all_results:
            print(f"⚡ Using cached results for: {model_name}")
            return self.all_results[model_name]
        
        self.update_status(
            status="benchmarking",
            current_model=model_name,
            message=f"Starting benchmark: {model_name}"
        )
        
        # Load model ONCE (not in each thread!)
        model = ModelFactory.create(
            model_type=model_config['type'],
            model_path=model_config['path'],
            config=self.config['benchmark']
        )
        model.load_model()
        
        model_results = {
            'model_name': model_name,
            'model_path': model_config['path'],
            'datasets': {},
            'detailed_results': [],
            'start_time': datetime.now().isoformat()
        }
        
        # Benchmark on each dataset
        for dataset_config in self.config['datasets']:
            if not dataset_config.get('enabled', True):
                continue
            
            dataset_name = dataset_config['name']
            samples = self.load_dataset_samples(dataset_config)
            
            dataset_results = []
            
            # Process samples sequentially (GPU can't truly parallelize anyway)
            for idx, sample in enumerate(tqdm(samples, desc=f"Processing {dataset_name}")):
                try:
                    result = model.transcribe_with_metrics(sample['audio_path'])
                    
                    wer = calculate_wer(sample['reference'], result['transcription'])
                    cer = calculate_cer(sample['reference'], result['transcription'])
                    
                    result_entry = {
                        'id': sample['id'],
                        'reference': sample['reference'],
                        'hypothesis': result['transcription'],
                        'wer': wer,
                        'cer': cer,
                        'latency': result['latency'],
                        'throughput': result['throughput'],
                        'dataset': sample.get('dataset', 'unknown')
                    }
                    
                    dataset_results.append(result_entry)
                    model_results['detailed_results'].append(result_entry)
                    
                    # Cleanup temp file
                    try:
                        os.unlink(sample['audio_path'])
                    except:
                        pass
                        
                except Exception as e:
                    print(f"Error processing sample {idx}: {e}")
                    continue
            
            # Aggregate dataset results
            model_results['datasets'][dataset_name] = {
                'samples': len(dataset_results),
                'metrics': aggregate_metrics(dataset_results)
            }
        
        # Cleanup model
        model.cleanup()
        
        # Aggregate all results
        model_results['aggregated'] = aggregate_metrics(model_results['detailed_results'])
        model_results['end_time'] = datetime.now().isoformat()
        
        # Save to cache
        self.all_results[model_name] = model_results
        self._save_cache()
        
        return model_results
    
    def run(self):
        """Run complete benchmark"""
        print("=" * 80)
        print("SPEECH-TO-TEXT PARALLEL BENCHMARK")
        print(f"Workers: {self.num_workers}")
        print("=" * 80)
        
        # Show cached models
        if self.all_results:
            print(f"\n✓ Found cached results for: {', '.join(self.all_results.keys())}")
        
        start_time = time.time()
        
        self.update_status(
            status="running",
            message="Starting parallel benchmark..."
        )
        
        # Benchmark each model
        for model_config in self.config['models']:
            if not model_config.get('enabled', True):
                print(f"⊘ Skipping disabled model: {model_config['name']}")
                continue
            
            try:
                print(f"\n{'=' * 80}")
                print(f"Benchmarking: {model_config['name']}")
                print(f"{'=' * 80}")
                
                results = self.benchmark_model_parallel(model_config)
                
                print(f"✓ Completed: {model_config['name']}")
                print(f"  WER: {results['aggregated']['wer_mean']:.2f}%")
                print(f"  Latency: {results['aggregated']['latency_mean']:.3f}s")
                print(f"  Throughput: {results['aggregated']['throughput_mean']:.1f} chars/s")
                
            except Exception as e:
                print(f"✗ Error benchmarking {model_config['name']}: {str(e)}")
                import traceback
                traceback.print_exc()
                continue
        
        # Generate reports
        if self.all_results:
            self.update_status(
                status="generating_reports",
                message="Generating reports and visualizations..."
            )
            self.generate_reports()
        
        total_time = time.time() - start_time
        
        self.update_status(
            status="completed",
            message=f"Benchmark completed in {format_duration(total_time)}"
        )
        
        print(f"\n{'=' * 80}")
        print(f"PARALLEL BENCHMARK COMPLETED in {format_duration(total_time)}")
        print(f"Results saved to: {self.results_dir}")
        print(f"Cache saved to: {self.cache_dir}")
        print(f"{'=' * 80}")
    
    def generate_reports(self):
        """Generate all reports and visualizations"""
        print("\nGenerating reports...")
        
        # Save JSON
        if self.config['output'].get('save_metrics', True):
            self.visualizer.save_json_report(self.all_results)
            print("✓ Saved JSON report")
        
        # Create visualizations
        if self.config['output'].get('save_visualizations', True):
            try:
                self.visualizer.create_multi_metric_comparison(self.all_results)
                print("✓ Created Chart.js data")
            except Exception as e:
                print(f"Warning: Error creating visualizations: {str(e)}")
    
    def get_status(self) -> Dict[str, Any]:
        """Get current status"""
        return self.current_status
    
    def get_results(self) -> Dict[str, Any]:
        """Get all results"""
        return self.all_results


if __name__ == "__main__":
    runner = BenchmarkRunner()
    runner.run()