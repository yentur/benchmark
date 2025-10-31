import json
import numpy as np
from typing import Dict, List, Any
from pathlib import Path

class BenchmarkVisualizer:
    """Chart.js ile modern ve performanslı görselleştirmeler"""
    
    def __init__(self, output_dir: str = "results"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)
        
        # Modern monochrome renk paleti
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
            'gradient_end': 'rgba(0, 0, 0, 0.4)'
        }
    
    def _generate_chart_data(self, results: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
        """Tüm grafik verilerini hazırla"""
        models = list(results.keys())
        
        chart_data = {
            'models': models,
            'wer': {
                'mean': [results[m]['aggregated']['wer_mean'] for m in models],
                'std': [results[m]['aggregated']['wer_std'] for m in models]
            },
            'cer': {
                'mean': [results[m]['aggregated']['cer_mean'] for m in models],
                'std': [results[m]['aggregated']['cer_std'] for m in models]
            },
            'latency': {
                'mean': [results[m]['aggregated']['latency_mean'] for m in models],
                'std': [results[m]['aggregated']['latency_std'] for m in models],
                'p50': [results[m]['aggregated']['latency_p50'] for m in models],
                'p95': [results[m]['aggregated']['latency_p95'] for m in models],
                'p99': [results[m]['aggregated']['latency_p99'] for m in models]
            },
            'throughput': {
                'mean': [results[m]['aggregated']['throughput_mean'] for m in models],
                'std': [results[m]['aggregated']['throughput_std'] for m in models]
            },
            'distributions': {}
        }
        
        # Her model için detaylı dağılımlar
        for model_name in models:
            detailed = results[model_name].get('detailed_results', [])
            chart_data['distributions'][model_name] = {
                'wer': [r.get('wer', 0) for r in detailed],
                'cer': [r.get('cer', 0) for r in detailed],
                'latency': [r.get('latency', 0) for r in detailed]
            }
        
        # Performance skorları hesapla
        scores = []
        for m in models:
            agg = results[m]['aggregated']
            score = (
                (100 - agg['wer_mean']) * 0.4 +
                (100 - agg['cer_mean']) * 0.3 +
                (5 - min(agg['latency_mean'], 5)) / 5 * 100 * 0.2 +
                min(agg['throughput_mean'] / 10, 10) * 10 * 0.1
            )
            scores.append(round(score, 2))
        
        chart_data['performance_scores'] = scores
        
        return chart_data
    
    def create_charts_json(self, results: Dict[str, Dict[str, Any]]):
        """Tüm grafik verisini JSON olarak kaydet"""
        chart_data = self._generate_chart_data(results)
        
        output_file = self.output_dir / "charts_data.json"
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(chart_data, f, indent=2, ensure_ascii=False)
        
        print(f"✓ Chart data saved to: {output_file}")
        return chart_data
    
    def create_multi_metric_comparison(self, results: Dict[str, Dict[str, Any]]):
        """Chart.js için veri hazırla"""
        self.create_charts_json(results)
    
    def create_latency_distribution(self, results: Dict[str, Dict[str, Any]]):
        """Latency dağılımı için veri hazırla"""
        pass  # JSON'da zaten var
    
    def create_summary_report(self, results: Dict[str, Dict[str, Any]]):
        """Özet rapor için veri hazırla"""
        pass  # JSON'da zaten var
    
    def save_json_report(self, results: Dict[str, Dict[str, Any]], filename: str = "results.json"):
        """JSON raporu kaydet"""
        with open(self.output_dir / filename, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2, ensure_ascii=False)