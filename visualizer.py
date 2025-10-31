import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
import pandas as pd
import numpy as np
from typing import Dict, List, Any
import json
from pathlib import Path

class BenchmarkVisualizer:
    """Plotly ile modern ve interaktif görselleştirmeler"""
    
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
            'grid': '#e8e8e8'
        }
        
        # Plotly template ayarları
        self.template = self._create_template()
    
    def _create_template(self):
        """Modern monochrome Plotly template"""
        return go.layout.Template(
            layout=go.Layout(
                font=dict(family="Inter, SF Pro Display, -apple-system, sans-serif", size=13, color=self.colors['primary']),
                paper_bgcolor=self.colors['background'],
                plot_bgcolor=self.colors['background'],
                title=dict(font=dict(size=20, color=self.colors['primary'], family="Inter")),
                xaxis=dict(
                    gridcolor=self.colors['grid'],
                    linecolor=self.colors['lightest'],
                    zerolinecolor=self.colors['lightest'],
                    title=dict(font=dict(size=14, color=self.colors['medium']))
                ),
                yaxis=dict(
                    gridcolor=self.colors['grid'],
                    linecolor=self.colors['lightest'],
                    zerolinecolor=self.colors['lightest'],
                    title=dict(font=dict(size=14, color=self.colors['medium']))
                ),
                hoverlabel=dict(
                    bgcolor=self.colors['dark'],
                    font=dict(color=self.colors['background'], size=12)
                ),
                margin=dict(l=80, r=40, t=100, b=80)
            )
        )
    
    def _save_figure(self, fig, filename: str):
        """Plotly figürünü HTML olarak kaydet"""
        config = {
            'displayModeBar': True,
            'displaylogo': False,
            'modeBarButtonsToRemove': ['pan2d', 'lasso2d', 'select2d'],
            'toImageButtonOptions': {
                'format': 'png',
                'filename': filename.replace('.html', ''),
                'height': 800,
                'width': 1400,
                'scale': 2
            }
        }
        
        fig.write_html(
            self.output_dir / filename,
            config=config,
            include_plotlyjs='cdn'
        )
    
    def create_wer_comparison(self, results: Dict[str, Dict[str, Any]], 
                             filename: str = "wer_comparison.html"):
        """WER karşılaştırma grafiği"""
        models = list(results.keys())
        wer_mean = [results[m]['aggregated']['wer_mean'] for m in models]
        wer_std = [results[m]['aggregated']['wer_std'] for m in models]
        
        # En iyi modeli vurgula
        best_idx = np.argmin(wer_mean)
        colors = [self.colors['primary'] if i == best_idx else self.colors['medium'] 
                 for i in range(len(models))]
        
        fig = go.Figure()
        
        fig.add_trace(go.Bar(
            y=models,
            x=wer_mean,
            error_x=dict(type='data', array=wer_std, color=self.colors['dark'], thickness=2),
            orientation='h',
            marker=dict(
                color=colors,
                line=dict(color=self.colors['dark'], width=2)
            ),
            text=[f'{v:.2f}%' for v in wer_mean],
            textposition='outside',
            textfont=dict(size=14, color=self.colors['primary'], family='Inter'),
            hovertemplate='<b>%{y}</b><br>WER: %{x:.2f}%<br>Std: ±%{error_x.array:.2f}%<extra></extra>'
        ))
        
        fig.update_layout(
            template=self.template,
            title=dict(
                text='<b>Word Error Rate Comparison</b>',
                x=0.5,
                xanchor='center',
                font=dict(size=24, color=self.colors['primary'])
            ),
            xaxis_title='<b>WER (%)</b>',
            yaxis_title='',
            height=400 + len(models) * 60,
            showlegend=False,
            hovermode='closest'
        )
        
        self._save_figure(fig, filename)
    
    def create_cer_comparison(self, results: Dict[str, Dict[str, Any]], 
                             filename: str = "cer_comparison.html"):
        """CER karşılaştırma grafiği"""
        models = list(results.keys())
        cer_mean = [results[m]['aggregated']['cer_mean'] for m in models]
        cer_std = [results[m]['aggregated']['cer_std'] for m in models]
        
        best_idx = np.argmin(cer_mean)
        colors = [self.colors['primary'] if i == best_idx else self.colors['medium'] 
                 for i in range(len(models))]
        
        fig = go.Figure()
        
        fig.add_trace(go.Bar(
            y=models,
            x=cer_mean,
            error_x=dict(type='data', array=cer_std, color=self.colors['dark'], thickness=2),
            orientation='h',
            marker=dict(
                color=colors,
                line=dict(color=self.colors['dark'], width=2)
            ),
            text=[f'{v:.2f}%' for v in cer_mean],
            textposition='outside',
            textfont=dict(size=14, color=self.colors['primary'], family='Inter'),
            hovertemplate='<b>%{y}</b><br>CER: %{x:.2f}%<br>Std: ±%{error_x.array:.2f}%<extra></extra>'
        ))
        
        fig.update_layout(
            template=self.template,
            title=dict(
                text='<b>Character Error Rate Comparison</b>',
                x=0.5,
                xanchor='center',
                font=dict(size=24, color=self.colors['primary'])
            ),
            xaxis_title='<b>CER (%)</b>',
            yaxis_title='',
            height=400 + len(models) * 60,
            showlegend=False,
            hovermode='closest'
        )
        
        self._save_figure(fig, filename)
    
    def create_latency_comparison(self, results: Dict[str, Dict[str, Any]],
                                 filename: str = "latency_comparison.html"):
        """Latency karşılaştırma grafiği"""
        models = list(results.keys())
        latency_mean = [results[m]['aggregated']['latency_mean'] for m in models]
        latency_std = [results[m]['aggregated']['latency_std'] for m in models]
        
        best_idx = np.argmin(latency_mean)
        colors = [self.colors['primary'] if i == best_idx else self.colors['medium']
                 for i in range(len(models))]
        
        fig = go.Figure()
        
        fig.add_trace(go.Bar(
            y=models,
            x=latency_mean,
            error_x=dict(type='data', array=latency_std, color=self.colors['dark'], thickness=2),
            orientation='h',
            marker=dict(
                color=colors,
                line=dict(color=self.colors['dark'], width=2)
            ),
            text=[f'{v:.3f}s' for v in latency_mean],
            textposition='outside',
            textfont=dict(size=14, color=self.colors['primary'], family='Inter'),
            hovertemplate='<b>%{y}</b><br>Latency: %{x:.3f}s<br>Std: ±%{error_x.array:.3f}s<extra></extra>'
        ))
        
        fig.update_layout(
            template=self.template,
            title=dict(
                text='<b>Latency Comparison</b>',
                x=0.5,
                xanchor='center',
                font=dict(size=24, color=self.colors['primary'])
            ),
            xaxis_title='<b>Average Latency (seconds)</b>',
            yaxis_title='',
            height=400 + len(models) * 60,
            showlegend=False,
            hovermode='closest'
        )
        
        self._save_figure(fig, filename)
    
    def create_throughput_comparison(self, results: Dict[str, Dict[str, Any]],
                                    filename: str = "throughput_comparison.html"):
        """Throughput karşılaştırma grafiği"""
        models = list(results.keys())
        throughput_mean = [results[m]['aggregated']['throughput_mean'] for m in models]
        throughput_std = [results[m]['aggregated']['throughput_std'] for m in models]
        
        best_idx = np.argmax(throughput_mean)
        colors = [self.colors['primary'] if i == best_idx else self.colors['medium']
                 for i in range(len(models))]
        
        fig = go.Figure()
        
        fig.add_trace(go.Bar(
            y=models,
            x=throughput_mean,
            error_x=dict(type='data', array=throughput_std, color=self.colors['dark'], thickness=2),
            orientation='h',
            marker=dict(
                color=colors,
                line=dict(color=self.colors['dark'], width=2)
            ),
            text=[f'{v:.1f}' for v in throughput_mean],
            textposition='outside',
            textfont=dict(size=14, color=self.colors['primary'], family='Inter'),
            hovertemplate='<b>%{y}</b><br>Throughput: %{x:.1f} chars/s<br>Std: ±%{error_x.array:.1f}<extra></extra>'
        ))
        
        fig.update_layout(
            template=self.template,
            title=dict(
                text='<b>Throughput Comparison</b>',
                x=0.5,
                xanchor='center',
                font=dict(size=24, color=self.colors['primary'])
            ),
            xaxis_title='<b>Throughput (chars/s)</b>',
            yaxis_title='',
            height=400 + len(models) * 60,
            showlegend=False,
            hovermode='closest'
        )
        
        self._save_figure(fig, filename)
    
    def create_latency_distribution(self, results: Dict[str, Dict[str, Any]],
                                   filename: str = "latency_distribution.html"):
        """Latency dağılım grafiği (box + violin)"""
        data_list = []
        for model_name, model_results in results.items():
            latencies = [r.get('latency', 0) for r in model_results.get('detailed_results', [])]
            data_list.extend([{'Model': model_name, 'Latency': lat} for lat in latencies])
        
        df = pd.DataFrame(data_list)
        
        fig = go.Figure()
        
        models = df['Model'].unique()
        color_map = {models[i]: [self.colors['primary'], self.colors['medium'], self.colors['light']][i % 3] 
                    for i in range(len(models))}
        
        for model in models:
            model_data = df[df['Model'] == model]['Latency']
            
            fig.add_trace(go.Violin(
                y=model_data,
                name=model,
                box_visible=True,
                meanline_visible=True,
                fillcolor=color_map[model],
                opacity=0.6,
                line=dict(color=self.colors['dark'], width=2),
                marker=dict(line=dict(color=self.colors['dark'], width=1)),
                hovertemplate='<b>%{fullData.name}</b><br>Latency: %{y:.3f}s<extra></extra>'
            ))
        
        fig.update_layout(
            template=self.template,
            title=dict(
                text='<b>Latency Distribution by Model</b>',
                x=0.5,
                xanchor='center',
                font=dict(size=24, color=self.colors['primary'])
            ),
            yaxis_title='<b>Latency (seconds)</b>',
            xaxis_title='',
            height=600,
            showlegend=True,
            legend=dict(
                orientation="h",
                yanchor="bottom",
                y=1.02,
                xanchor="center",
                x=0.5,
                font=dict(size=12)
            ),
            hovermode='closest'
        )
        
        self._save_figure(fig, filename)
    
    def create_error_distribution(self, results: Dict[str, Dict[str, Any]],
                                 filename: str = "error_distribution.html"):
        """WER dağılım histogramı"""
        data_list = []
        for model_name, model_results in results.items():
            wers = [r.get('wer', 0) for r in model_results.get('detailed_results', [])]
            data_list.extend([{'Model': model_name, 'WER': wer} for wer in wers])
        
        df = pd.DataFrame(data_list)
        
        fig = go.Figure()
        
        models = df['Model'].unique()
        color_map = {models[i]: [self.colors['primary'], self.colors['medium'], self.colors['light']][i % 3] 
                    for i in range(len(models))}
        
        for model in models:
            model_data = df[df['Model'] == model]['WER']
            
            fig.add_trace(go.Histogram(
                x=model_data,
                name=model,
                opacity=0.7,
                marker=dict(
                    color=color_map[model],
                    line=dict(color=self.colors['dark'], width=1.5)
                ),
                hovertemplate='<b>%{fullData.name}</b><br>WER Range: %{x}<br>Count: %{y}<extra></extra>'
            ))
        
        fig.update_layout(
            template=self.template,
            title=dict(
                text='<b>WER Distribution Across Samples</b>',
                x=0.5,
                xanchor='center',
                font=dict(size=24, color=self.colors['primary'])
            ),
            xaxis_title='<b>Word Error Rate (%)</b>',
            yaxis_title='<b>Frequency</b>',
            barmode='overlay',
            height=600,
            showlegend=True,
            legend=dict(
                orientation="h",
                yanchor="bottom",
                y=1.02,
                xanchor="center",
                x=0.5,
                font=dict(size=12)
            ),
            hovermode='closest'
        )
        
        self._save_figure(fig, filename)
    
    def create_radar_chart(self, results: Dict[str, Dict[str, Any]],
                          filename: str = "performance_radar.html"):
        """Performance radar chart"""
        categories = ['WER<br>(lower better)', 'CER<br>(lower better)', 
                     'Latency<br>(lower better)', 'Throughput<br>(higher better)']
        
        fig = go.Figure()
        
        models = list(results.keys())
        color_map = {models[i]: [self.colors['primary'], self.colors['medium'], self.colors['light']][i % 3] 
                    for i in range(len(models))}
        
        for model_name in models:
            agg = results[model_name]['aggregated']
            
            # Normalize values (0-1, higher is better)
            wer_norm = max(0, 1 - (agg['wer_mean'] / 100))
            cer_norm = max(0, 1 - (agg['cer_mean'] / 100))
            lat_norm = max(0, 1 - min(agg['latency_mean'] / 5, 1))
            thr_norm = min(agg['throughput_mean'] / 1000, 1)
            
            values = [wer_norm, cer_norm, lat_norm, thr_norm]
            
            fig.add_trace(go.Scatterpolar(
                r=values,
                theta=categories,
                fill='toself',
                name=model_name,
                line=dict(color=color_map[model_name], width=3),
                fillcolor=color_map[model_name],
                opacity=0.3,
                hovertemplate='<b>%{fullData.name}</b><br>%{theta}: %{r:.2f}<extra></extra>'
            ))
        
        fig.update_layout(
            template=self.template,
            title=dict(
                text='<b>Overall Performance Radar</b>',
                x=0.5,
                xanchor='center',
                font=dict(size=24, color=self.colors['primary'])
            ),
            polar=dict(
                radialaxis=dict(
                    visible=True,
                    range=[0, 1],
                    showticklabels=True,
                    tickfont=dict(size=10),
                    gridcolor=self.colors['grid']
                ),
                angularaxis=dict(
                    gridcolor=self.colors['grid']
                )
            ),
            height=700,
            showlegend=True,
            legend=dict(
                orientation="h",
                yanchor="bottom",
                y=-0.15,
                xanchor="center",
                x=0.5,
                font=dict(size=12)
            ),
            hovermode='closest'
        )
        
        self._save_figure(fig, filename)
    
    def create_latency_percentiles(self, results: Dict[str, Dict[str, Any]],
                                   filename: str = "latency_percentiles.html"):
        """Latency percentile karşılaştırması"""
        models = list(results.keys())
        
        p50s = [results[m]['aggregated']['latency_p50'] for m in models]
        p95s = [results[m]['aggregated']['latency_p95'] for m in models]
        p99s = [results[m]['aggregated']['latency_p99'] for m in models]
        
        fig = go.Figure()
        
        fig.add_trace(go.Bar(
            name='P50',
            x=models,
            y=p50s,
            marker=dict(color=self.colors['primary'], line=dict(color=self.colors['dark'], width=2)),
            text=[f'{v:.3f}s' for v in p50s],
            textposition='outside',
            hovertemplate='<b>%{x}</b><br>P50: %{y:.3f}s<extra></extra>'
        ))
        
        fig.add_trace(go.Bar(
            name='P95',
            x=models,
            y=p95s,
            marker=dict(color=self.colors['medium'], line=dict(color=self.colors['dark'], width=2)),
            text=[f'{v:.3f}s' for v in p95s],
            textposition='outside',
            hovertemplate='<b>%{x}</b><br>P95: %{y:.3f}s<extra></extra>'
        ))
        
        fig.add_trace(go.Bar(
            name='P99',
            x=models,
            y=p99s,
            marker=dict(color=self.colors['light'], line=dict(color=self.colors['dark'], width=2)),
            text=[f'{v:.3f}s' for v in p99s],
            textposition='outside',
            hovertemplate='<b>%{x}</b><br>P99: %{y:.3f}s<extra></extra>'
        ))
        
        fig.update_layout(
            template=self.template,
            title=dict(
                text='<b>Latency Percentiles Comparison</b>',
                x=0.5,
                xanchor='center',
                font=dict(size=24, color=self.colors['primary'])
            ),
            xaxis_title='',
            yaxis_title='<b>Latency (seconds)</b>',
            barmode='group',
            height=600,
            showlegend=True,
            legend=dict(
                orientation="h",
                yanchor="bottom",
                y=1.02,
                xanchor="center",
                x=0.5,
                font=dict(size=12)
            ),
            hovermode='x unified'
        )
        
        self._save_figure(fig, filename)
    
    def create_summary_dashboard(self, results: Dict[str, Dict[str, Any]],
                                filename: str = "summary_dashboard.html"):
        """Comprehensive summary dashboard with subplots"""
        models = list(results.keys())
        
        fig = make_subplots(
            rows=2, cols=2,
            subplot_titles=('<b>WER Comparison</b>', '<b>Latency Comparison</b>',
                          '<b>Error Rate Overview</b>', '<b>Performance Score</b>'),
            specs=[[{"type": "bar"}, {"type": "bar"}],
                   [{"type": "bar"}, {"type": "bar"}]],
            vertical_spacing=0.15,
            horizontal_spacing=0.12
        )
        
        # 1. WER Comparison
        wers = [results[m]['aggregated']['wer_mean'] for m in models]
        best_wer_idx = np.argmin(wers)
        wer_colors = [self.colors['primary'] if i == best_wer_idx else self.colors['medium'] 
                     for i in range(len(models))]
        
        fig.add_trace(
            go.Bar(x=models, y=wers, marker=dict(color=wer_colors, line=dict(color=self.colors['dark'], width=2)),
                   text=[f'{v:.2f}%' for v in wers], textposition='outside',
                   name='WER', showlegend=False,
                   hovertemplate='<b>%{x}</b><br>WER: %{y:.2f}%<extra></extra>'),
            row=1, col=1
        )
        
        # 2. Latency Comparison
        latencies = [results[m]['aggregated']['latency_mean'] for m in models]
        best_lat_idx = np.argmin(latencies)
        lat_colors = [self.colors['primary'] if i == best_lat_idx else self.colors['medium']
                     for i in range(len(models))]
        
        fig.add_trace(
            go.Bar(x=models, y=latencies, marker=dict(color=lat_colors, line=dict(color=self.colors['dark'], width=2)),
                   text=[f'{v:.3f}s' for v in latencies], textposition='outside',
                   name='Latency', showlegend=False,
                   hovertemplate='<b>%{x}</b><br>Latency: %{y:.3f}s<extra></extra>'),
            row=1, col=2
        )
        
        # 3. Error Rate Overview (WER + CER)
        cers = [results[m]['aggregated']['cer_mean'] for m in models]
        
        fig.add_trace(
            go.Bar(x=models, y=wers, name='WER', 
                   marker=dict(color=self.colors['primary'], line=dict(color=self.colors['dark'], width=2)),
                   hovertemplate='<b>%{x}</b><br>WER: %{y:.2f}%<extra></extra>'),
            row=2, col=1
        )
        
        fig.add_trace(
            go.Bar(x=models, y=cers, name='CER',
                   marker=dict(color=self.colors['medium'], line=dict(color=self.colors['dark'], width=2)),
                   hovertemplate='<b>%{x}</b><br>CER: %{y:.2f}%<extra></extra>'),
            row=2, col=1
        )
        
        # 4. Performance Score
        scores = []
        for m in models:
            agg = results[m]['aggregated']
            score = (
                (100 - agg['wer_mean']) * 0.4 +
                (100 - agg['cer_mean']) * 0.3 +
                (5 - min(agg['latency_mean'], 5)) / 5 * 100 * 0.2 +
                min(agg['throughput_mean'] / 10, 10) * 10 * 0.1
            )
            scores.append(score)
        
        best_score_idx = np.argmax(scores)
        score_colors = [self.colors['primary'] if i == best_score_idx else self.colors['medium']
                       for i in range(len(models))]
        
        fig.add_trace(
            go.Bar(x=models, y=scores, marker=dict(color=score_colors, line=dict(color=self.colors['dark'], width=2)),
                   text=[f'{v:.1f}' for v in scores], textposition='outside',
                   name='Score', showlegend=False,
                   hovertemplate='<b>%{x}</b><br>Score: %{y:.1f}<extra></extra>'),
            row=2, col=2
        )
        
        # Update layout
        fig.update_xaxes(title_text="", row=1, col=1)
        fig.update_xaxes(title_text="", row=1, col=2)
        fig.update_xaxes(title_text="", row=2, col=1)
        fig.update_xaxes(title_text="", row=2, col=2)
        
        fig.update_yaxes(title_text="<b>WER (%)</b>", row=1, col=1)
        fig.update_yaxes(title_text="<b>Latency (s)</b>", row=1, col=2)
        fig.update_yaxes(title_text="<b>Error Rate (%)</b>", row=2, col=1)
        fig.update_yaxes(title_text="<b>Score</b>", row=2, col=2)
        
        fig.update_layout(
            template=self.template,
            title=dict(
                text='<b>Benchmark Performance Dashboard</b>',
                x=0.5,
                xanchor='center',
                font=dict(size=28, color=self.colors['primary'])
            ),
            height=1000,
            showlegend=True,
            legend=dict(
                orientation="h",
                yanchor="bottom",
                y=-0.08,
                xanchor="center",
                x=0.5,
                font=dict(size=12)
            ),
            hovermode='closest'
        )
        
        self._save_figure(fig, filename)
    
    def create_multi_metric_comparison(self, results: Dict[str, Dict[str, Any]], 
                                      filename: str = "metrics_comparison.html"):
        """Tüm metrikleri oluştur"""
        self.create_wer_comparison(results)
        self.create_cer_comparison(results)
        self.create_latency_comparison(results)
        self.create_throughput_comparison(results)
        self.create_latency_percentiles(results)
    
    def create_summary_report(self, results: Dict[str, Dict[str, Any]],
                            filename: str = "summary_report.html"):
        """Özet rapor oluştur"""
        self.create_summary_dashboard(results)
        self.create_radar_chart(results)
        self.create_error_distribution(results)
    
    def save_json_report(self, results: Dict[str, Dict[str, Any]],
                        filename: str = "results.json"):
        """JSON raporu kaydet"""
        with open(self.output_dir / filename, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2, ensure_ascii=False)