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
        self._is_loaded = False
        
    @abstractmethod
    def load_model(self):
        """Load the model and processor"""
        pass
    
    @abstractmethod
    def transcribe(self, audio_path: str) -> str:
        """Transcribe audio file to text"""
        pass
    
    def transcribe_with_metrics(self, audio_path: str) -> Dict[str, Any]:
        """
        Transcribe and calculate performance metrics
        Returns: dict with transcription, latency, and throughput
        """
        if not self._is_loaded:
            raise RuntimeError("Model not loaded. Call load_model() first.")
        
        start_time = time.time()
        
        # Transcribe
        try:
            transcription = self.transcribe(audio_path)
        except Exception as e:
            print(f"⚠ Error transcribing {audio_path}: {e}")
            transcription = ""
        
        # Calculate latency
        latency = time.time() - start_time
        
        # Calculate approximate throughput (characters per second)
        throughput = len(transcription) / latency if latency > 0 else 0
        
        return {
            "transcription": transcription,
            "latency": latency,
            "throughput": throughput,
            "audio_path": audio_path
        }
    
    def batch_transcribe(self, audio_paths: List[str]) -> List[Dict[str, Any]]:
        """
        Transcribe multiple audio files
        Default implementation processes sequentially
        Override for batch processing support
        """
        results = []
        for audio_path in audio_paths:
            result = self.transcribe_with_metrics(audio_path)
            results.append(result)
        return results
    
    def get_memory_usage(self) -> Dict[str, float]:
        """
        Get model memory usage
        Returns: dict with memory stats in GB
        """
        memory_stats = {
            'allocated': 0.0,
            'reserved': 0.0,
            'max_allocated': 0.0
        }
        
        if torch.cuda.is_available():
            memory_stats['allocated'] = torch.cuda.memory_allocated() / 1024**3
            memory_stats['reserved'] = torch.cuda.memory_reserved() / 1024**3
            memory_stats['max_allocated'] = torch.cuda.max_memory_allocated() / 1024**3
        
        return memory_stats
    
    def cleanup(self):
        """
        Cleanup model resources
        Should be called when done with model
        """
        try:
            if self.model is not None:
                del self.model
                self.model = None
            
            if self.processor is not None:
                del self.processor
                self.processor = None
            
            self._is_loaded = False
            
            # Clear CUDA cache if available
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
                torch.cuda.synchronize()
            
        except Exception as e:
            print(f"⚠ Warning during cleanup: {e}")
    
    def __del__(self):
        """Cleanup on object destruction"""
        self.cleanup()
    
    def __enter__(self):
        """Context manager support"""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager cleanup"""
        self.cleanup()


class ModelFactory:
    """Factory for creating STT models"""
    
    _registry = {}
    
    @classmethod
    def register(cls, model_type: str):
        """
        Decorator to register model classes
        Usage:
            @ModelFactory.register("whisper")
            class WhisperModel(BaseSTTModel):
                ...
        """
        def decorator(model_class):
            cls._registry[model_type] = model_class
            return model_class
        return decorator
    
    @classmethod
    def create(cls, model_type: str, model_path: str, config: Dict[str, Any]) -> BaseSTTModel:
        """
        Create model instance
        
        Args:
            model_type: Type of model (e.g., "whisper")
            model_path: Path or identifier for the model
            config: Configuration dictionary
            
        Returns:
            Instance of BaseSTTModel subclass
            
        Raises:
            ValueError: If model type is not registered
        """
        if model_type not in cls._registry:
            available = ', '.join(cls._registry.keys())
            raise ValueError(
                f"Unknown model type: '{model_type}'. "
                f"Available types: {available}"
            )
        
        model_class = cls._registry[model_type]
        return model_class(model_path, config)
    
    @classmethod
    def list_available_types(cls) -> List[str]:
        """List all registered model types"""
        return list(cls._registry.keys())
    
    @classmethod
    def is_registered(cls, model_type: str) -> bool:
        """Check if a model type is registered"""
        return model_type in cls._registry