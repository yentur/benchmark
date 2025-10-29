import jiwer
import numpy as np
from typing import List, Dict, Any
import re

def normalize_text(text: str) -> str:
    """Normalize text for WER calculation"""
    # Convert to lowercase
    text = text.lower()
    
    # Remove punctuation
    text = re.sub(r'[^\w\s]', '', text)
    
    # Normalize whitespace
    text = ' '.join(text.split())
    
    return text

def calculate_wer(reference: str, hypothesis: str) -> float:
    """Calculate Word Error Rate"""
    ref_normalized = normalize_text(reference)
    hyp_normalized = normalize_text(hypothesis)
    
    if not ref_normalized:
        return 0.0
    
    try:
        wer = jiwer.wer(ref_normalized, hyp_normalized)
        return wer * 100  # Convert to percentage
    except:
        return 100.0

def calculate_cer(reference: str, hypothesis: str) -> float:
    """Calculate Character Error Rate"""
    ref_normalized = normalize_text(reference)
    hyp_normalized = normalize_text(hypothesis)
    
    if not ref_normalized:
        return 0.0
    
    try:
        cer = jiwer.cer(ref_normalized, hyp_normalized)
        return cer * 100  # Convert to percentage
    except:
        return 100.0

def aggregate_metrics(results: List[Dict[str, Any]]) -> Dict[str, float]:
    """Aggregate metrics from multiple results"""
    wers = [r.get("wer", 0) for r in results if "wer" in r]
    cers = [r.get("cer", 0) for r in results if "cer" in r]
    latencies = [r.get("latency", 0) for r in results if "latency" in r]
    throughputs = [r.get("throughput", 0) for r in results if "throughput" in r]
    
    aggregated = {
        "wer_mean": np.mean(wers) if wers else 0.0,
        "wer_std": np.std(wers) if wers else 0.0,
        "wer_min": np.min(wers) if wers else 0.0,
        "wer_max": np.max(wers) if wers else 0.0,
        "cer_mean": np.mean(cers) if cers else 0.0,
        "cer_std": np.std(cers) if cers else 0.0,
        "latency_mean": np.mean(latencies) if latencies else 0.0,
        "latency_std": np.std(latencies) if latencies else 0.0,
        "latency_p50": np.percentile(latencies, 50) if latencies else 0.0,
        "latency_p95": np.percentile(latencies, 95) if latencies else 0.0,
        "latency_p99": np.percentile(latencies, 99) if latencies else 0.0,
        "throughput_mean": np.mean(throughputs) if throughputs else 0.0,
        "throughput_std": np.std(throughputs) if throughputs else 0.0,
        "total_samples": len(results)
    }
    
    return aggregated

def format_duration(seconds: float) -> str:
    """Format duration in human readable format"""
    if seconds < 60:
        return f"{seconds:.2f}s"
    elif seconds < 3600:
        minutes = int(seconds // 60)
        secs = seconds % 60
        return f"{minutes}m {secs:.0f}s"
    else:
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        return f"{hours}h {minutes}m"

def calculate_audio_duration(audio_path: str) -> float:
    """Calculate audio file duration"""
    import librosa
    try:
        audio, sr = librosa.load(audio_path, sr=None)
        return len(audio) / sr
    except:
        return 0.0