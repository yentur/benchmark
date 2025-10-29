from abc import ABC, abstractmethod
from typing import Dict, Any, List
import time
import torch

class BaseSTTModel(ABC):
    """Base class for Speech-to-Text models"""
    
    def __init__(self, model_path: str, config: Dict[str, Any]):
        self.model_path = model_path
        self.config = config
        self.model = None
        self.processor = None
        
    @abstractmethod
    def load_model(self):
        """Load the model and processor"""
        pass
    
    @abstractmethod
    def transcribe(self, audio_path: str) -> str:
        """Transcribe audio file to text"""
        pass
    
    def transcribe_with_metrics(self, audio_path: str) -> Dict[str, Any]:
        """Transcribe and calculate metrics"""
        start_time = time.time()
        
        # Transcribe
        transcription = self.transcribe(audio_path)
        
        # Calculate latency
        latency = time.time() - start_time
        
        # Calculate approximate throughput (characters per second)
        throughput = len(transcription) / latency if latency > 0 else 0
        
        return {
            "transcription": transcription,
            "latency": latency,
            "throughput": throughput
        }
    
    def batch_transcribe(self, audio_paths: List[str]) -> List[Dict[str, Any]]:
        """Transcribe multiple audio files"""
        results = []
        for audio_path in audio_paths:
            result = self.transcribe_with_metrics(audio_path)
            result["audio_path"] = audio_path
            results.append(result)
        return results
    
    def get_memory_usage(self) -> float:
        """Get model memory usage in GB"""
        if torch.cuda.is_available():
            return torch.cuda.max_memory_allocated() / 1024**3
        return 0.0
    
    def cleanup(self):
        """Cleanup model resources"""
        if self.model is not None:
            del self.model
        if self.processor is not None:
            del self.processor
        if torch.cuda.is_available():
            torch.cuda.empty_cache()


class ModelFactory:
    """Factory for creating STT models"""
    
    _registry = {}
    
    @classmethod
    def register(cls, model_type: str):
        """Decorator to register model classes"""
        def decorator(model_class):
            cls._registry[model_type] = model_class
            return model_class
        return decorator
    
    @classmethod
    def create(cls, model_type: str, model_path: str, config: Dict[str, Any]) -> BaseSTTModel:
        """Create model instance"""
        if model_type not in cls._registry:
            raise ValueError(f"Unknown model type: {model_type}. Available: {list(cls._registry.keys())}")
        
        model_class = cls._registry[model_type]
        return model_class(model_path, config)