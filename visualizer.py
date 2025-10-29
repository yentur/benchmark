import matplotlib.pyplot as plt
import matplotlib
matplotlib.use('Agg')
import seaborn as sns
import pandas as pd
from typing import Dict, List, Any
import json
from pathlib import Path

# Set style - modern black and white
plt.style.use('seaborn-v0_8-darkgrid')
sns.set_palette("gray")

class BenchmarkVisualizer:
    """Create visualizations for benchmark results"""
    
    def __init__(self, output_dir: str = "results"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)
        
        # Set modern black and white theme
        self.colors = {
            'primary': '#000000',
            'secondary': '#333333',
            'accent': '#666666',
            'light': '#999999',
            'background': '#ffffff'
        }
    
    def create_comparison_chart(self, results: Dict[str, Dict[str, Any]], 
                               metric: str, title: str, filename: str):
        """Create comparison bar chart for a specific metric"""
        models = list(results.keys())
        values = [results[m]['aggregated'][metric] for m in models]
        
        fig, ax = plt.subplots(figsize=(12, 6))
        bars = ax.barh(models, values, color=self.colors['primary'], 
                       edgecolor=self.colors['secondary'], linewidth=2)
        
        # Add value labels
        for i, (bar, value) in enumerate(zip(bars, values)):
            ax.text(value + max(values) * 0.01, i, f'{value:.2f}',
                   va='center', fontsize=10, fontweight='bold')
        
        ax.set_xlabel(metric.replace('_', ' ').title(), fontsize=12, fontweight='bold')
        ax.set_title(title, fontsize=14, fontweight='bold', pad=20)
        ax.spines['top'].set_visible(False)
        ax.spines['right'].set_visible(False)
        ax.grid(axis='x', alpha=0.3, linestyle='--')
        
        plt.tight_layout()
        plt.savefig(self.output_dir / filename, dpi=300, bbox_inches='tight', 
                   facecolor='white', edgecolor='none')
        plt.close()
    
    def create_multi_metric_comparison(self, results: Dict[str, Dict[str, Any]], 
                                      filename: str = "metrics_comparison.png"):
        """Create comprehensive comparison chart"""
        metrics = ['wer_mean', 'latency_mean', 'throughput_mean']
        titles = ['Word Error Rate (%)', 'Latency (seconds)', 'Throughput (chars/s)']
        
        fig, axes = plt.subplots(1, 3, figsize=(18, 6))
        fig.suptitle('Model Performance Comparison', fontsize=16, fontweight='bold', y=1.02)
        
        for ax, metric, title in zip(axes, metrics, titles):
            models = list(results.keys())
            values = [results[m]['aggregated'][metric] for m in models]
            
            bars = ax.barh(models, values, color=self.colors['primary'],
                          edgecolor=self.colors['secondary'], linewidth=2)
            
            # Add value labels
            for i, (bar, value) in enumerate(zip(bars, values)):
                ax.text(value + max(values) * 0.01, i, f'{value:.2f}',
                       va='center', fontsize=9, fontweight='bold')
            
            ax.set_xlabel(title, fontsize=11, fontweight='bold')
            ax.spines['top'].set_visible(False)
            ax.spines['right'].set_visible(False)
            ax.grid(axis='x', alpha=0.3, linestyle='--')
        
        plt.tight_layout()
        plt.savefig(self.output_dir / filename, dpi=300, bbox_inches='tight',
                   facecolor='white', edgecolor='none')
        plt.close()
    
    def create_latency_distribution(self, results: Dict[str, Dict[str, Any]],
                                   filename: str = "latency_distribution.png"):
        """Create latency distribution chart"""
        fig, ax = plt.subplots(figsize=(14, 6))
        
        data = []
        for model_name, model_results in results.items():
            for result in model_results.get('detailed_results', []):
                data.append({
                    'Model': model_name,
                    'Latency': result.get('latency', 0)
                })
        
        df = pd.DataFrame(data)
        
        # Box plot
        bp = ax.boxplot([df[df['Model'] == m]['Latency'].values 
                         for m in df['Model'].unique()],
                        labels=df['Model'].unique(),
                        patch_artist=True,
                        widths=0.6)
        
        # Style boxes
        for patch in bp['boxes']:
            patch.set_facecolor(self.colors['light'])
            patch.set_edgecolor(self.colors['primary'])
            patch.set_linewidth(2)
        
        for whisker in bp['whiskers']:
            whisker.set(color=self.colors['secondary'], linewidth=1.5, linestyle='--')
        
        for cap in bp['caps']:
            cap.set(color=self.colors['secondary'], linewidth=2)
        
        for median in bp['medians']:
            median.set(color=self.colors['primary'], linewidth=2.5)
        
        ax.set_ylabel('Latency (seconds)', fontsize=12, fontweight='bold')
        ax.set_title('Latency Distribution by Model', fontsize=14, fontweight='bold', pad=20)
        ax.spines['top'].set_visible(False)
        ax.spines['right'].set_visible(False)
        ax.grid(axis='y', alpha=0.3, linestyle='--')
        
        plt.tight_layout()
        plt.savefig(self.output_dir / filename, dpi=300, bbox_inches='tight',
                   facecolor='white', edgecolor='none')
        plt.close()
    
    def create_summary_report(self, results: Dict[str, Dict[str, Any]],
                            filename: str = "summary_report.png"):
        """Create comprehensive summary report"""
        fig = plt.figure(figsize=(16, 10))
        gs = fig.add_gridspec(3, 2, hspace=0.3, wspace=0.3)
        
        # Title
        fig.suptitle('Benchmark Summary Report', fontsize=18, fontweight='bold', y=0.98)
        
        # 1. WER Comparison
        ax1 = fig.add_subplot(gs[0, 0])
        models = list(results.keys())
        wers = [results[m]['aggregated']['wer_mean'] for m in models]
        ax1.barh(models, wers, color=self.colors['primary'], 
                edgecolor=self.colors['secondary'], linewidth=2)
        ax1.set_xlabel('WER (%)', fontweight='bold')
        ax1.set_title('Word Error Rate', fontweight='bold')
        ax1.spines['top'].set_visible(False)
        ax1.spines['right'].set_visible(False)
        
        # 2. Latency Comparison
        ax2 = fig.add_subplot(gs[0, 1])
        latencies = [results[m]['aggregated']['latency_mean'] for m in models]
        ax2.barh(models, latencies, color=self.colors['secondary'],
                edgecolor=self.colors['primary'], linewidth=2)
        ax2.set_xlabel('Latency (s)', fontweight='bold')
        ax2.set_title('Average Latency', fontweight='bold')
        ax2.spines['top'].set_visible(False)
        ax2.spines['right'].set_visible(False)
        
        # 3. Throughput Comparison
        ax3 = fig.add_subplot(gs[1, 0])
        throughputs = [results[m]['aggregated']['throughput_mean'] for m in models]
        ax3.barh(models, throughputs, color=self.colors['accent'],
                edgecolor=self.colors['primary'], linewidth=2)
        ax3.set_xlabel('Throughput (chars/s)', fontweight='bold')
        ax3.set_title('Processing Throughput', fontweight='bold')
        ax3.spines['top'].set_visible(False)
        ax3.spines['right'].set_visible(False)
        
        # 4. Performance Score (lower WER + lower latency is better)
        ax4 = fig.add_subplot(gs[1, 1])
        scores = [100 - wer + (1/lat if lat > 0 else 0) * 10 
                 for wer, lat in zip(wers, latencies)]
        ax4.barh(models, scores, color=self.colors['light'],
                edgecolor=self.colors['primary'], linewidth=2)
        ax4.set_xlabel('Score (higher is better)', fontweight='bold')
        ax4.set_title('Overall Performance Score', fontweight='bold')
        ax4.spines['top'].set_visible(False)
        ax4.spines['right'].set_visible(False)
        
        # 5. Summary Table
        ax5 = fig.add_subplot(gs[2, :])
        ax5.axis('off')
        
        table_data = []
        headers = ['Model', 'WER (%)', 'CER (%)', 'Latency (s)', 
                  'Throughput', 'Samples']
        
        for model in models:
            agg = results[model]['aggregated']
            table_data.append([
                model,
                f"{agg['wer_mean']:.2f}",
                f"{agg['cer_mean']:.2f}",
                f"{agg['latency_mean']:.3f}",
                f"{agg['throughput_mean']:.1f}",
                f"{agg['total_samples']}"
            ])
        
        table = ax5.table(cellText=table_data, colLabels=headers,
                         cellLoc='center', loc='center',
                         colWidths=[0.2, 0.13, 0.13, 0.15, 0.15, 0.12])
        table.auto_set_font_size(False)
        table.set_fontsize(10)
        table.scale(1, 2.5)
        
        # Style table
        for i in range(len(headers)):
            table[(0, i)].set_facecolor(self.colors['primary'])
            table[(0, i)].set_text_props(weight='bold', color='white')
        
        for i in range(1, len(table_data) + 1):
            for j in range(len(headers)):
                if i % 2 == 0:
                    table[(i, j)].set_facecolor('#f5f5f5')
                table[(i, j)].set_edgecolor(self.colors['light'])
        
        plt.savefig(self.output_dir / filename, dpi=300, bbox_inches='tight',
                   facecolor='white', edgecolor='none')
        plt.close()
    
    def save_json_report(self, results: Dict[str, Dict[str, Any]],
                        filename: str = "results.json"):
        """Save results as JSON"""
        with open(self.output_dir / filename, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2, ensure_ascii=False)