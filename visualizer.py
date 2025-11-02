import json
import numpy as np
from typing import Dict, List, Any
from pathlib import Path


class BenchmarkVisualizer:
    """Modern visualization generator for benchmark results with multi-dataset support"""
    
    def __init__(self, output_dir: str = "results"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True, parents=True)
        
        # Modern monochrome color palette
        self.colors = {
            'primary': '#000000',
            'dark': '#1a1a1a',
            'medium': '#4a4a4a',
            'light': '#7a7a7a',
            'lighter': '#a0a0a0',
            'lightest': '#d0d0d0',
            'background': '#ffffff',
            'grid': '#e8e8e8',
            'gradient_start': 'rgba(0, 0, 0, 0.9)',
            'gradient_end': 'rgba(0, 0, 0, 0.4)',
            'success': '#22c55e',
            'warning': '#f59e0b',
            'error': '#ef4444'
        }
    
    def _calculate_performance_score(self, agg: Dict[str, float]) -> float:
        """
        Calculate overall performance score (0-100)
        Based on: WER (40%), CER (30%), Latency (20%), Throughput (10%)
        """
        wer_score = max(0, (100 - agg.get('wer_mean', 100))) * 0.4
        cer_score = max(0, (100 - agg.get('cer_mean', 100))) * 0.3
        
        # Latency score (5s = 0, 0s = 100)
        latency = agg.get('latency_mean', 5)
        latency_score = max(0, (5 - min(latency, 5)) / 5 * 100) * 0.2
        
        # Throughput score (normalize to 0-100)
        throughput = agg.get('throughput_mean', 0)
        throughput_score = min(throughput / 10, 10) * 10 * 0.1
        
        return round(wer_score + cer_score + latency_score + throughput_score, 2)
    
    def _generate_chart_data(self, results: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
        """Generate comprehensive chart data for all visualizations - HANDLES MULTIPLE DATASETS"""
        if not results:
            return {}
        
        models = list(results.keys())
        
        # Initialize chart data structure
        chart_data = {
            'models': models,
            'colors': self.colors,
            'timestamp': str(np.datetime64('now')),
            'performance_scores': [],
            'rankings': {},
            'wer': {
                'mean': [],
                'std': [],
                'min': [],
                'max': []
            },
            'cer': {
                'mean': [],
                'std': [],
                'min': [],
                'max': []
            },
            'latency': {
                'mean': [],
                'std': [],
                'min': [],
                'max': [],
                'p50': [],
                'p95': [],
                'p99': []
            },
            'throughput': {
                'mean': [],
                'std': [],
                'min': [],
                'max': []
            },
            'distributions': {},
            'datasets': {}  # NEW: Store per-dataset results
        }
        
        # Process each model - USE AGGREGATED RESULTS FOR OVERALL CHARTS
        for model_name in models:
            model_results = results[model_name]
            
            # Use aggregated metrics for overall comparison
            agg = model_results.get('aggregated', {})
            
            if not agg:
                # Fallback: compute from detailed_results if aggregated missing
                detailed = model_results.get('detailed_results', [])
                if detailed:
                    from utils import aggregate_metrics
                    agg = aggregate_metrics(detailed)
                else:
                    # Skip this model if no data
                    continue
            
            # WER metrics
            chart_data['wer']['mean'].append(round(agg.get('wer_mean', 0), 2))
            chart_data['wer']['std'].append(round(agg.get('wer_std', 0), 2))
            chart_data['wer']['min'].append(round(agg.get('wer_min', 0), 2))
            chart_data['wer']['max'].append(round(agg.get('wer_max', 0), 2))
            
            # CER metrics
            chart_data['cer']['mean'].append(round(agg.get('cer_mean', 0), 2))
            chart_data['cer']['std'].append(round(agg.get('cer_std', 0), 2))
            chart_data['cer']['min'].append(round(agg.get('cer_min', 0), 2))
            chart_data['cer']['max'].append(round(agg.get('cer_max', 0), 2))
            
            # Latency metrics
            chart_data['latency']['mean'].append(round(agg.get('latency_mean', 0), 3))
            chart_data['latency']['std'].append(round(agg.get('latency_std', 0), 3))
            chart_data['latency']['min'].append(round(agg.get('latency_min', 0), 3))
            chart_data['latency']['max'].append(round(agg.get('latency_max', 0), 3))
            chart_data['latency']['p50'].append(round(agg.get('latency_p50', 0), 3))
            chart_data['latency']['p95'].append(round(agg.get('latency_p95', 0), 3))
            chart_data['latency']['p99'].append(round(agg.get('latency_p99', 0), 3))
            
            # Throughput metrics
            chart_data['throughput']['mean'].append(round(agg.get('throughput_mean', 0), 1))
            chart_data['throughput']['std'].append(round(agg.get('throughput_std', 0), 1))
            chart_data['throughput']['min'].append(round(agg.get('throughput_min', 0), 1))
            chart_data['throughput']['max'].append(round(agg.get('throughput_max', 0), 1))
            
            # Detailed distributions
            detailed = model_results.get('detailed_results', [])
            chart_data['distributions'][model_name] = {
                'wer': [round(r.get('wer', 0), 2) for r in detailed if 'wer' in r],
                'cer': [round(r.get('cer', 0), 2) for r in detailed if 'cer' in r],
                'latency': [round(r.get('latency', 0), 3) for r in detailed if 'latency' in r],
                'throughput': [round(r.get('throughput', 0), 1) for r in detailed if 'throughput' in r]
            }
            
            # Performance score
            score = self._calculate_performance_score(agg)
            chart_data['performance_scores'].append(score)
            
            # NEW: Store per-dataset metrics
            datasets = model_results.get('datasets', {})
            for dataset_name, dataset_data in datasets.items():
                if dataset_name not in chart_data['datasets']:
                    chart_data['datasets'][dataset_name] = {}
                
                metrics = dataset_data.get('metrics', {})
                chart_data['datasets'][dataset_name][model_name] = {
                    'wer_mean': round(metrics.get('wer_mean', 0), 2),
                    'wer_std': round(metrics.get('wer_std', 0), 2),
                    'cer_mean': round(metrics.get('cer_mean', 0), 2),
                    'cer_std': round(metrics.get('cer_std', 0), 2),
                    'latency_mean': round(metrics.get('latency_mean', 0), 3),
                    'latency_std': round(metrics.get('latency_std', 0), 3),
                    'throughput_mean': round(metrics.get('throughput_mean', 0), 1),
                    'samples': dataset_data.get('samples', 0)
                }
        
        # Rankings - Find best models
        if models and chart_data['wer']['mean']:
            try:
                chart_data['rankings']['best_wer'] = models[
                    int(np.argmin(chart_data['wer']['mean']))
                ]
                
                chart_data['rankings']['best_cer'] = models[
                    int(np.argmin(chart_data['cer']['mean']))
                ]
                
                chart_data['rankings']['fastest'] = models[
                    int(np.argmin(chart_data['latency']['mean']))
                ]
                
                chart_data['rankings']['best_throughput'] = models[
                    int(np.argmax(chart_data['throughput']['mean']))
                ]
                
                chart_data['rankings']['best_overall'] = models[
                    int(np.argmax(chart_data['performance_scores']))
                ]
            except Exception as e:
                print(f"⚠ Warning calculating rankings: {e}")
        
        return chart_data
    
    def create_charts_json(self, results: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
        """Generate and save chart data as JSON"""
        print("Generating visualization data...")
        
        chart_data = self._generate_chart_data(results)
        
        if not chart_data:
            print("⚠ Warning: No chart data generated (empty results)")
            return {}
        
        output_file = self.output_dir / "charts_data.json"
        
        try:
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(chart_data, f, indent=2, ensure_ascii=False)
            
            print(f"✓ Chart data saved to: {output_file}")
            
            # Print rankings
            if chart_data.get('rankings'):
                print(f"\n📊 Rankings:")
                for metric, model in chart_data['rankings'].items():
                    if model:
                        print(f"  • {metric.replace('_', ' ').title()}: {model}")
            
            # Print dataset info
            if chart_data.get('datasets'):
                print(f"\n📁 Datasets: {len(chart_data['datasets'])} dataset(s)")
                for dataset_name in chart_data['datasets'].keys():
                    print(f"  • {dataset_name}")
            
            return chart_data
            
        except Exception as e:
            print(f"⚠ Error saving chart data: {e}")
            import traceback
            traceback.print_exc()
            return chart_data
    
    def save_json_report(self, results: Dict[str, Dict[str, Any]], filename: str = "results.json"):
        """Save complete results as JSON"""
        output_file = self.output_dir / filename
        
        try:
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(results, f, indent=2, ensure_ascii=False)
            
            print(f"✓ Results saved to: {output_file}")
            
            # Print summary
            print(f"\n📋 Summary:")
            print(f"  • Total models: {len(results)}")
            
            # Count unique datasets
            all_datasets = set()
            for model_results in results.values():
                datasets = model_results.get('datasets', {})
                all_datasets.update(datasets.keys())
            
            if all_datasets:
                print(f"  • Datasets tested: {len(all_datasets)}")
                for dataset in all_datasets:
                    print(f"    - {dataset}")
            
            total_samples = sum(
                r.get('aggregated', {}).get('total_samples', 0)
                for r in results.values()
            )
            print(f"  • Total samples processed: {total_samples}")
            
        except Exception as e:
            print(f"⚠ Error saving results: {e}")
            import traceback
            traceback.print_exc()