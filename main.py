import yaml
import os
from pathlib import Path
from typing import Dict, Any, List
import time
from datetime import datetime
from datasets import load_dataset
import soundfile as sf
import tempfile
from tqdm import tqdm

from model import ModelFactory
from whisper_model import WhisperModel
from utils import calculate_wer, calculate_cer, aggregate_metrics, format_duration
from visualizer import BenchmarkVisualizer

class BenchmarkRunner:
    """Main benchmark runner"""
    
    def __init__(self, config_path: str = "config.yaml"):
        with open(config_path, 'r') as f:
            self.config = yaml.safe_load(f)
        
        self.results_dir = Path(self.config['output']['results_dir'])
        self.results_dir.mkdir(exist_ok=True)
        
        self.visualizer = BenchmarkVisualizer(str(self.results_dir))
        self.all_results = {}
        self.current_status = {
            "status": "idle",
            "current_model": None,
            "current_dataset": None,
            "progress": 0,
            "total": 0,
            "message": "Ready to start"
        }
    
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
                'id': f"{dataset_config['name']}_{idx}"
            })
        
        print(f"✓ Loaded {len(samples)} samples from {dataset_config['name']}")
        return samples
    
    def benchmark_model(self, model_config: Dict[str, Any]) -> Dict[str, Any]:
        """Benchmark a single model"""
        model_name = model_config['name']
        self.update_status(
            status="loading_model",
            current_model=model_name,
            message=f"Loading model: {model_name}"
        )
        
        # Create model
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
            self.update_status(
                current_dataset=dataset_name,
                message=f"Benchmarking {model_name} on {dataset_name}"
            )
            
            # Load samples
            samples = self.load_dataset_samples(dataset_config)
            
            # Process samples
            dataset_results = []
            self.update_status(
                progress=0,
                total=len(samples),
                message=f"Processing {len(samples)} samples"
            )
            
            for idx, sample in enumerate(tqdm(samples, desc=f"{model_name} - {dataset_name}")):
                try:
                    # Transcribe
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
                    
                    # Cleanup temp file
                    try:
                        os.unlink(sample['audio_path'])
                    except:
                        pass
                    
                    self.update_status(
                        progress=idx + 1,
                        message=f"Processed {idx + 1}/{len(samples)} samples"
                    )
                    
                except Exception as e:
                    print(f"Error processing sample {sample['id']}: {str(e)}")
                    continue
            
            # Aggregate dataset results
            model_results['datasets'][dataset_name] = {
                'samples': len(dataset_results),
                'metrics': aggregate_metrics(dataset_results)
            }
        
        # Aggregate all results
        model_results['aggregated'] = aggregate_metrics(model_results['detailed_results'])
        model_results['end_time'] = datetime.now().isoformat()
        
        # Cleanup
        model.cleanup()
        
        return model_results
    
    def run(self):
        """Run complete benchmark"""
        print("=" * 80)
        print("SPEECH-TO-TEXT BENCHMARK")
        print("=" * 80)
        
        start_time = time.time()
        
        self.update_status(
            status="running",
            message="Starting benchmark..."
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
                
                results = self.benchmark_model(model_config)
                self.all_results[model_config['name']] = results
                
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
        print(f"BENCHMARK COMPLETED in {format_duration(total_time)}")
        print(f"Results saved to: {self.results_dir}")
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
                print("✓ Created metrics comparison")
                
                self.visualizer.create_latency_distribution(self.all_results)
                print("✓ Created latency distribution")
                
                self.visualizer.create_summary_report(self.all_results)
                print("✓ Created summary report")
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