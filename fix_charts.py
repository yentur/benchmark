#!/usr/bin/env python3
"""
Quick fix script to regenerate chart data from existing results
Path: /Users/muva/Desktop/tts/benchmark/fix_charts.py

Usage:
    python fix_charts.py
"""

import json
from pathlib import Path
from visualizer import BenchmarkVisualizer


def fix_charts():
    """Regenerate chart data from existing results"""
    
    print("\n" + "=" * 80)
    print("CHART DATA FIX SCRIPT")
    print("=" * 80 + "\n")
    
    # Paths
    results_dir = Path("results")
    cache_dir = Path("cache")
    
    # Try to load results from cache first
    cache_file = cache_dir / "benchmark_cache.json"
    results_file = results_dir / "results.json"
    
    results = None
    source = None
    
    if cache_file.exists():
        print(f"✓ Found cache file: {cache_file}")
        try:
            with open(cache_file, 'r', encoding='utf-8') as f:
                results = json.load(f)
            source = "cache"
        except Exception as e:
            print(f"✗ Error loading cache: {e}")
    
    if not results and results_file.exists():
        print(f"✓ Found results file: {results_file}")
        try:
            with open(results_file, 'r', encoding='utf-8') as f:
                results = json.load(f)
            source = "results"
        except Exception as e:
            print(f"✗ Error loading results: {e}")
    
    if not results:
        print("\n✗ No results found!")
        print("\nPlease run the benchmark first:")
        print("  python main.py")
        print("\nOr start the API server:")
        print("  python api.py")
        return False
    
    print(f"✓ Loaded results from {source}")
    print(f"  Models found: {len(results)}")
    for model_name in results.keys():
        print(f"    - {model_name}")
    
    # Create visualizer
    viz = BenchmarkVisualizer(str(results_dir))
    
    # Generate chart data
    print("\n" + "-" * 80)
    print("Generating chart data...")
    print("-" * 80 + "\n")
    
    try:
        chart_data = viz.create_charts_json(results)
        
        if chart_data:
            print("\n✓ Chart data generated successfully!")
            print(f"  File: {results_dir / 'charts_data.json'}")
            
            # Print some stats
            if 'models' in chart_data:
                print(f"\n📊 Chart Data Stats:")
                print(f"  Models: {len(chart_data['models'])}")
                print(f"  Metrics: WER, CER, Latency, Throughput")
                
                if 'rankings' in chart_data:
                    print(f"\n🏆 Rankings:")
                    for metric, model in chart_data['rankings'].items():
                        print(f"    {metric.replace('_', ' ').title()}: {model}")
            
            print("\n✓ You can now refresh the dashboard at http://localhost:8000")
            return True
        else:
            print("\n✗ Chart data is empty!")
            return False
            
    except Exception as e:
        print(f"\n✗ Error generating chart data: {e}")
        import traceback
        traceback.print_exc()
        return False


def validate_chart_data():
    """Validate the generated chart data structure"""
    
    print("\n" + "=" * 80)
    print("VALIDATING CHART DATA")
    print("=" * 80 + "\n")
    
    chart_file = Path("results") / "charts_data.json"
    
    if not chart_file.exists():
        print(f"✗ Chart data file not found: {chart_file}")
        return False
    
    try:
        with open(chart_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # Required fields
        required_fields = ['models', 'wer', 'cer', 'latency', 'throughput', 'performance_scores']
        
        print("Checking required fields:")
        all_valid = True
        
        for field in required_fields:
            if field in data:
                print(f"  ✓ {field}")
                
                # Check nested structure for metrics
                if field in ['wer', 'cer', 'latency', 'throughput']:
                    required_subfields = ['mean', 'std', 'min', 'max']
                    for subfield in required_subfields:
                        if subfield in data[field]:
                            print(f"    ✓ {field}.{subfield} ({len(data[field][subfield])} values)")
                        else:
                            print(f"    ✗ {field}.{subfield} MISSING")
                            all_valid = False
            else:
                print(f"  ✗ {field} MISSING")
                all_valid = False
        
        if all_valid:
            print("\n✓ All required fields present!")
            print("\n📊 Data Summary:")
            print(f"  Models: {len(data.get('models', []))}")
            print(f"  Model names: {', '.join(data.get('models', []))}")
            return True
        else:
            print("\n✗ Some fields are missing!")
            return False
            
    except Exception as e:
        print(f"\n✗ Error validating chart data: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    print("\n" + "=" * 80)
    print("STT BENCHMARK - CHART FIX UTILITY")
    print("=" * 80)
    
    # Fix charts
    if fix_charts():
        print("\n" + "-" * 80)
        
        # Validate
        validate_chart_data()
        
        print("\n" + "=" * 80)
        print("FIX COMPLETED SUCCESSFULLY!")
        print("=" * 80)
        print("\nNext steps:")
        print("  1. Start the API server: python api.py")
        print("  2. Open browser: http://localhost:8000")
        print("  3. Check the Charts section")
        print("\nIf charts still don't show:")
        print("  - Clear browser cache (Ctrl+F5)")
        print("  - Check browser console (F12)")
        print("  - Verify charts_data.json exists in results/")
        print("=" * 80 + "\n")
    else:
        print("\n" + "=" * 80)
        print("FIX FAILED!")
        print("=" * 80)
        print("\nTroubleshooting:")
        print("  1. Make sure you have run the benchmark first")
        print("  2. Check if results/ or cache/ directory exists")
        print("  3. Run: python main.py")
        print("=" * 80 + "\n")