import yaml
import os
import json
from model import ModelFactory
from whisper_model import WhisperModel
from wav2vec2_model import Wav2Vec2Model
from deepgram_model import DeepgramModel 
from utils import calculate_wer, calculate_cer, aggregate_metrics, format_duration
from visualizer import BenchmarkVisualizer
from pathlib import Path
from typing import Dict, Any, List, Callable, Optional
import time
from datetime import datetime
from datasets import load_dataset
import soundfile as sf
import tempfile
from tqdm import tqdm
import torch
import gc


class BenchmarkRunner:
    """Optimized benchmark runner with batch processing and multi-dataset support"""
    
    def __init__(self, config_path: str = "config.yaml"):
        with open(config_path, 'r') as f:
            self.config = yaml.safe_load(f)
        
        self.results_dir = Path(self.config['output']['results_dir'])
        self.results_dir.mkdir(exist_ok=True)
        
        self.cache_dir = Path(self.config['output']['cache_dir'])
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
        
        # Batch size for processing
        self.batch_size = self.config['benchmark'].get('batch_size', 1)
        
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
                for model_name in self.all_results.keys():
                    print(f"  - {model_name}")
            except Exception as e:
                print(f"⚠ Warning: Could not load cache: {e}")
                self.all_results = {}
    
    def _save_cache(self):
        """Save current results to cache"""
        cache_file = self.cache_dir / "benchmark_cache.json"
        try:
            with open(cache_file, 'w', encoding='utf-8') as f:
                json.dump(self.all_results, f, indent=2, ensure_ascii=False)
            print(f"✓ Cache updated: {cache_file}")
        except Exception as e:
            print(f"⚠ Warning: Could not save cache: {e}")
    
    def set_sample_callback(self, callback: Callable):
        """Set callback for sample updates"""
        self.sample_callback = callback
    
    def update_status(self, **kwargs):
        """Update current status"""
        self.current_status.update(kwargs)
        if 'message' in kwargs:
            print(f"[STATUS] {kwargs['message']}")
    
    def load_dataset_samples(self, dataset_config: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Load dataset samples from HuggingFace"""
        self.update_status(
            status="loading_dataset",
            message=f"Loading dataset: {dataset_config['name']}"
        )
        
        try:
            dataset = load_dataset(
                dataset_config['path'],
                split=dataset_config['split'],
                trust_remote_code=True
            )
        except Exception as e:
            print(f"✗ Error loading dataset {dataset_config['name']}: {e}")
            return []
        
        samples = []
        
        for idx, item in enumerate(tqdm(dataset, desc=f"Preparing {dataset_config['name']}")):
            try:
                # Save audio to temporary file
                audio_array = item['audio']['array']
                sr = item['audio']['sampling_rate']
                
                # Create temp file with identifiable name for audio serving
                dataset_id = dataset_config['name'].replace('/', '_')
                temp_file = tempfile.NamedTemporaryFile(
                    delete=False, 
                    suffix='.wav', 
                    prefix=f"{dataset_id}_{idx}_",
                    dir=self.cache_dir
                )
                temp_path = temp_file.name
                temp_file.close()
                
                sf.write(temp_path, audio_array, sr)
                
                samples.append({
                    'audio_path': temp_path,
                    'reference': item.get('sentence', item.get('text', '')),
                    'id': f"{dataset_id}_{idx}",
                    'dataset': dataset_config['name']
                })
            except Exception as e:
                print(f"⚠ Warning: Skipping sample {idx}: {e}")
                continue
        
        print(f"✓ Loaded {len(samples)} samples from {dataset_config['name']}")
        return samples
    
    def cleanup_temp_files(self, samples: List[Dict[str, Any]]):
        """Clean up temporary audio files - KEEP FOR AUDIO PLAYBACK"""
        # Don't delete files - they're needed for audio playback in the dashboard
        # Files will be cleaned up when cache is cleared
        pass
    
    def benchmark_model_batch(self, model_config: Dict[str, Any]) -> Dict[str, Any]:
        """Benchmark a single model with BATCH processing - IMPROVED DATASET SUPPORT"""
        model_name = model_config['name']
        
        # Check if already in cache
        if model_name in self.all_results:
            print(f"⚡ Using cached results for: {model_name}")
            self.update_status(
                current_model=model_name,
                message=f"Using cached results for {model_name}"
            )
            return self.all_results[model_name]
        
        print(f"\n{'=' * 80}")
        print(f"Benchmarking: {model_name}")
        print(f"{'=' * 80}")
        
        self.update_status(
            status="benchmarking",
            current_model=model_name,
            message=f"Loading model: {model_name}"
        )
        
        # Load model ONCE
        try:
            model = ModelFactory.create(
                model_type=model_config['type'],
                model_path=model_config['path'],
                config=self.config['benchmark']
            )
            model.load_model()
        except Exception as e:
            print(f"✗ Error loading model {model_name}: {e}")
            return None
        
        model_results = {
            'model_name': model_name,
            'model_path': model_config['path'],
            'datasets': {},  # Store results per dataset
            'detailed_results': [],  # All results combined
            'start_time': datetime.now().isoformat()
        }
        
        total_samples = 0
        processed_samples = 0
        
        # Benchmark on each dataset
        for dataset_config in self.config['datasets']:
            if not dataset_config.get('enabled', True):
                continue
            
            dataset_name = dataset_config['name']
            self.update_status(
                current_dataset=dataset_name,
                message=f"Loading dataset: {dataset_name}"
            )
            
            samples = self.load_dataset_samples(dataset_config)
            if not samples:
                print(f"⚠ Warning: No samples loaded for {dataset_name}")
                continue
            
            total_samples += len(samples)
            dataset_results = []
            
            # Process samples with progress bar
            print(f"\nProcessing {len(samples)} samples from {dataset_name}...")
            
            with tqdm(total=len(samples), desc=dataset_name) as pbar:
                for idx, sample in enumerate(samples):
                    try:
                        # Update status
                        processed_samples += 1
                        self.update_status(
                            progress=processed_samples,
                            total=total_samples,
                            message=f"Processing {model_name} on {dataset_name}: {processed_samples}/{total_samples}"
                        )
                        
                        # Transcribe with metrics
                        result = model.transcribe_with_metrics(sample['audio_path'])
                        
                        # Calculate WER and CER
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
                            'dataset': dataset_name
                        }
                        
                        dataset_results.append(result_entry)
                        model_results['detailed_results'].append(result_entry)
                        
                        # Callback for real-time updates
                        if self.sample_callback:
                            self.sample_callback(
                                sample['reference'],
                                result['transcription'],
                                idx
                            )
                        
                        pbar.update(1)
                        
                    except Exception as e:
                        print(f"\n⚠ Error processing sample {idx}: {e}")
                        pbar.update(1)
                        continue
            
            # DON'T clean up temp files - needed for audio playback
            # self.cleanup_temp_files(samples)
            
            # Aggregate dataset results - STORE PER DATASET
            if dataset_results:
                model_results['datasets'][dataset_name] = {
                    'samples': len(dataset_results),
                    'metrics': aggregate_metrics(dataset_results)
                }
                
                # Print dataset summary
                metrics = model_results['datasets'][dataset_name]['metrics']
                print(f"\n{dataset_name} Results:")
                print(f"  WER: {metrics['wer_mean']:.2f}% (±{metrics['wer_std']:.2f})")
                print(f"  CER: {metrics['cer_mean']:.2f}% (±{metrics['cer_std']:.2f})")
                print(f"  Latency: {metrics['latency_mean']:.3f}s (±{metrics['latency_std']:.3f})")
                print(f"  Throughput: {metrics['throughput_mean']:.1f} chars/s")
        
        # Cleanup model and free memory
        try:
            model.cleanup()
            del model
            gc.collect()
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
        except Exception as e:
            print(f"⚠ Warning during cleanup: {e}")
        
        # Aggregate all results
        if model_results['detailed_results']:
            model_results['aggregated'] = aggregate_metrics(model_results['detailed_results'])
            model_results['end_time'] = datetime.now().isoformat()
            
            # Print overall summary
            agg = model_results['aggregated']
            print(f"\n{'=' * 80}")
            print(f"Overall Results for {model_name}:")
            print(f"  Total Samples: {agg['total_samples']}")
            print(f"  WER: {agg['wer_mean']:.2f}% (±{agg['wer_std']:.2f})")
            print(f"  CER: {agg['cer_mean']:.2f}% (±{agg['cer_std']:.2f})")
            print(f"  Latency: {agg['latency_mean']:.3f}s (p95: {agg['latency_p95']:.3f}s)")
            print(f"  Throughput: {agg['throughput_mean']:.1f} chars/s")
            print(f"{'=' * 80}\n")
            
            # Save to cache immediately
            self.all_results[model_name] = model_results
            self._save_cache()
            
            # Generate visualizations after each model
            self._generate_visualizations()
        else:
            print(f"⚠ Warning: No results collected for {model_name}")
            return None
        
        return model_results
    
    def _generate_visualizations(self):
        """Generate visualizations from current results"""
        try:
            if self.all_results and self.config['output'].get('save_visualizations', True):
                self.visualizer.create_charts_json(self.all_results)
        except Exception as e:
            print(f"⚠ Warning generating visualizations: {e}")
    
    def run(self):
        """Run complete benchmark"""
        print("\n" + "=" * 80)
        print("SPEECH-TO-TEXT BENCHMARK SYSTEM")
        print("=" * 80)
        print(f"Batch Size: {self.batch_size}")
        print(f"Device: {self.config['benchmark'].get('device', 'auto')}")
        print(f"Results Directory: {self.results_dir}")
        print(f"Cache Directory: {self.cache_dir}")
        print("=" * 80 + "\n")
        
        # Show cached models
        if self.all_results:
            print(f"✓ Found cached results for: {', '.join(self.all_results.keys())}\n")
        
        start_time = time.time()
        
        self.update_status(
            status="running",
            message="Starting benchmark..."
        )
        
        # Count enabled models
        enabled_models = [m for m in self.config['models'] if m.get('enabled', True)]
        print(f"Will benchmark {len(enabled_models)} model(s)\n")
        
        # Benchmark each model
        for idx, model_config in enumerate(enabled_models, 1):
            print(f"\n[{idx}/{len(enabled_models)}] Processing: {model_config['name']}")
            
            try:
                results = self.benchmark_model_batch(model_config)
                
                if results:
                    print(f"✓ Completed: {model_config['name']}")
                else:
                    print(f"✗ Failed: {model_config['name']}")
                    
            except Exception as e:
                print(f"✗ Error benchmarking {model_config['name']}: {str(e)}")
                import traceback
                traceback.print_exc()
                continue
        
        # Generate final reports
        if self.all_results:
            self.update_status(
                status="generating_reports",
                message="Generating final reports and visualizations..."
            )
            self.generate_reports()
        else:
            print("\n⚠ No results to generate reports")
        
        total_time = time.time() - start_time
        
        self.update_status(
            status="completed",
            message=f"Benchmark completed in {format_duration(total_time)}"
        )
        
        print(f"\n{'=' * 80}")
        print(f"BENCHMARK COMPLETED in {format_duration(total_time)}")
        print(f"Results saved to: {self.results_dir}")
        print(f"Cache saved to: {self.cache_dir}")
        print(f"{'=' * 80}\n")
    
    def generate_reports(self):
        """Generate all reports and visualizations"""
        print("\n" + "=" * 80)
        print("Generating Reports...")
        print("=" * 80)
        
        try:
            # Save JSON
            if self.config['output'].get('save_metrics', True):
                self.visualizer.save_json_report(self.all_results)
                print("✓ Saved JSON report (results.json)")
            
            # Create visualizations
            if self.config['output'].get('save_visualizations', True):
                chart_data = self.visualizer.create_charts_json(self.all_results)
                if chart_data:
                    print("✓ Created visualization data (charts_data.json)")
                else:
                    print("⚠ Warning: Chart data is empty")
                
        except Exception as e:
            print(f"⚠ Warning: Error creating visualizations: {str(e)}")
            import traceback
            traceback.print_exc()
        
        print("=" * 80 + "\n")
    
    def get_status(self) -> Dict[str, Any]:
        """Get current status"""
        return self.current_status.copy()
    
    def get_results(self) -> Dict[str, Any]:
        """Get all results"""
        return self.all_results.copy()


if __name__ == "__main__":
    try:
        runner = BenchmarkRunner()
        runner.run()
    except KeyboardInterrupt:
        print("\n\n⚠ Benchmark interrupted by user")
    except Exception as e:
        print(f"\n✗ Fatal error: {e}")
        import traceback
        traceback.print_exc()