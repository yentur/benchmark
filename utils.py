import jiwer
import numpy as np
from typing import List, Dict, Any
import re


def normalize_text(text: str) -> str:
    """
    Normalize text for WER/CER calculation
    - Lowercase
    - Remove punctuation
    - Normalize whitespace
    """
    if not text:
        return ""
    
    # Convert to lowercase
    text = text.lower()
    
    # Remove punctuation
    text = re.sub(r'[^\w\s]', '', text)
    
    # Normalize whitespace
    text = ' '.join(text.split())
    
    return text


def calculate_wer(reference: str, hypothesis: str) -> float:
    """
    Calculate Word Error Rate (WER)
    Returns percentage (0-100)
    """
    if not reference or not reference.strip():
        return 0.0 if not hypothesis or not hypothesis.strip() else 100.0
    
    ref_normalized = normalize_text(reference)
    hyp_normalized = normalize_text(hypothesis)
    
    if not ref_normalized:
        return 0.0
    
    try:
        wer = jiwer.wer(ref_normalized, hyp_normalized)
        return min(wer * 100, 100.0)  # Cap at 100%
    except Exception as e:
        print(f"⚠ Warning calculating WER: {e}")
        return 100.0


def calculate_cer(reference: str, hypothesis: str) -> float:
    """
    Calculate Character Error Rate (CER)
    Returns percentage (0-100)
    """
    if not reference or not reference.strip():
        return 0.0 if not hypothesis or not hypothesis.strip() else 100.0
    
    ref_normalized = normalize_text(reference)
    hyp_normalized = normalize_text(hypothesis)
    
    if not ref_normalized:
        return 0.0
    
    try:
        cer = jiwer.cer(ref_normalized, hyp_normalized)
        return min(cer * 100, 100.0)  # Cap at 100%
    except Exception as e:
        print(f"⚠ Warning calculating CER: {e}")
        return 100.0


def aggregate_metrics(results: List[Dict[str, Any]]) -> Dict[str, float]:
    """
    Aggregate metrics from multiple results
    Returns statistics for WER, CER, latency, and throughput
    """
    if not results:
        return {
            "wer_mean": 0.0,
            "wer_std": 0.0,
            "wer_min": 0.0,
            "wer_max": 0.0,
            "cer_mean": 0.0,
            "cer_std": 0.0,
            "cer_min": 0.0,
            "cer_max": 0.0,
            "latency_mean": 0.0,
            "latency_std": 0.0,
            "latency_min": 0.0,
            "latency_max": 0.0,
            "latency_p50": 0.0,
            "latency_p95": 0.0,
            "latency_p99": 0.0,
            "throughput_mean": 0.0,
            "throughput_std": 0.0,
            "throughput_min": 0.0,
            "throughput_max": 0.0,
            "total_samples": 0
        }
    
    # Extract metrics
    wers = [r.get("wer", 0) for r in results if "wer" in r and r["wer"] is not None]
    cers = [r.get("cer", 0) for r in results if "cer" in r and r["cer"] is not None]
    latencies = [r.get("latency", 0) for r in results if "latency" in r and r["latency"] is not None]
    throughputs = [r.get("throughput", 0) for r in results if "throughput" in r and r["throughput"] is not None]
    
    def safe_stat(values, stat_func, default=0.0):
        """Safely calculate statistics"""
        try:
            return float(stat_func(values)) if values else default
        except:
            return default
    
    aggregated = {
        # WER statistics
        "wer_mean": safe_stat(wers, np.mean),
        "wer_std": safe_stat(wers, np.std),
        "wer_min": safe_stat(wers, np.min),
        "wer_max": safe_stat(wers, np.max),
        
        # CER statistics
        "cer_mean": safe_stat(cers, np.mean),
        "cer_std": safe_stat(cers, np.std),
        "cer_min": safe_stat(cers, np.min),
        "cer_max": safe_stat(cers, np.max),
        
        # Latency statistics
        "latency_mean": safe_stat(latencies, np.mean),
        "latency_std": safe_stat(latencies, np.std),
        "latency_min": safe_stat(latencies, np.min),
        "latency_max": safe_stat(latencies, np.max),
        "latency_p50": safe_stat(latencies, lambda x: np.percentile(x, 50)),
        "latency_p95": safe_stat(latencies, lambda x: np.percentile(x, 95)),
        "latency_p99": safe_stat(latencies, lambda x: np.percentile(x, 99)),
        
        # Throughput statistics
        "throughput_mean": safe_stat(throughputs, np.mean),
        "throughput_std": safe_stat(throughputs, np.std),
        "throughput_min": safe_stat(throughputs, np.min),
        "throughput_max": safe_stat(throughputs, np.max),
        
        # Count
        "total_samples": len(results)
    }
    
    return aggregated


def format_duration(seconds: float) -> str:
    """
    Format duration in human readable format
    Examples:
        - 45.2 -> "45.20s"
        - 125.0 -> "2m 5s"
        - 3725.0 -> "1h 2m"
    """
    if seconds < 60:
        return f"{seconds:.2f}s"
    elif seconds < 3600:
        minutes = int(seconds // 60)
        secs = seconds % 60
        return f"{minutes}m {secs:.0f}s"
    else:
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        if secs > 0:
            return f"{hours}h {minutes}m {secs}s"
        return f"{hours}h {minutes}m"


def calculate_audio_duration(audio_path: str) -> float:
    """
    Calculate audio file duration in seconds
    """
    try:
        import librosa
        audio, sr = librosa.load(audio_path, sr=None)
        return len(audio) / sr
    except Exception as e:
        print(f"⚠ Warning: Could not calculate duration for {audio_path}: {e}")
        return 0.0


def format_metrics_table(results: Dict[str, Any]) -> str:
    """
    Format results as a nice ASCII table
    """
    if not results:
        return "No results available"
    
    lines = []
    lines.append("\n" + "=" * 100)
    lines.append(f"{'Model':<40} {'WER':<12} {'CER':<12} {'Latency':<15} {'Throughput':<15}")
    lines.append("=" * 100)
    
    for model_name, model_results in results.items():
        agg = model_results.get('aggregated', {})
        
        wer = f"{agg.get('wer_mean', 0):.2f}%"
        cer = f"{agg.get('cer_mean', 0):.2f}%"
        latency = f"{agg.get('latency_mean', 0):.3f}s"
        throughput = f"{agg.get('throughput_mean', 0):.1f} ch/s"
        
        lines.append(f"{model_name:<40} {wer:<12} {cer:<12} {latency:<15} {throughput:<15}")
    
    lines.append("=" * 100 + "\n")
    
    return "\n".join(lines)


def print_progress_bar(iteration: int, total: int, prefix: str = '', suffix: str = '', 
                      length: int = 50, fill: str = '█'):
    """
    Print a progress bar (alternative to tqdm for simple cases)
    """
    percent = f"{100 * (iteration / float(total)):.1f}"
    filled_length = int(length * iteration // total)
    bar = fill * filled_length + '-' * (length - filled_length)
    print(f'\r{prefix} |{bar}| {percent}% {suffix}', end='')
    
    if iteration == total:
        print()