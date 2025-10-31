from transformers import WhisperForConditionalGeneration, WhisperProcessor
import torch
import librosa
import numpy as np
from model import BaseSTTModel, ModelFactory


@ModelFactory.register("whisper")
class WhisperModel(BaseSTTModel):
    """Whisper model implementation with proper device management"""
    
    def __init__(self, model_path: str, config: dict):
        super().__init__(model_path, config)
        self.device = None
        self.dtype = None
        self._is_loaded = False
    
    def _get_device(self):
        """Get proper device configuration"""
        device_config = self.config.get("device", "auto")
        
        if device_config == "auto":
            if torch.cuda.is_available():
                device = "cuda"
            elif torch.backends.mps.is_available():
                device = "mps"
            else:
                device = "cpu"
        else:
            device = device_config
        
        return device
    
    def load_model(self):
        """Load Whisper model and processor with proper error handling"""
        try:
            # Determine dtype
            dtype_config = self.config.get("torch_dtype", "float16")
            if dtype_config == "float16" and torch.cuda.is_available():
                self.dtype = torch.float16
            else:
                self.dtype = torch.float32
            
            # Determine device
            self.device = self._get_device()
            
            print(f"Loading Whisper model...")
            print(f"  Model: {self.model_path}")
            print(f"  Device: {self.device}")
            print(f"  Dtype: {self.dtype}")
            
            # Try to load model - check if it's quantized
            try:
                # First attempt: normal loading
                self.model = WhisperForConditionalGeneration.from_pretrained(
                    self.model_path,
                    torch_dtype=self.dtype,
                    low_cpu_mem_usage=True,
                    device_map=self.device if self.device == "cuda" else None
                )
                
                # Check if model is quantized
                is_quantized = any(
                    hasattr(param, 'quant_state') or 
                    '8bit' in str(type(param)) or 
                    '4bit' in str(type(param))
                    for param in self.model.parameters()
                )
                
                if is_quantized:
                    print("  ✓ Model is quantized (8-bit/4-bit)")
                    print("  ✓ Skipping .to() call (model already on correct device)")
                    # Model is already on the correct device, don't call .to()
                else:
                    # Not quantized, safe to move to device
                    self.model = self.model.to(self.device)
                    
            except Exception as e:
                # If first attempt fails, try with device_map="auto"
                print(f"  ⚠ First load attempt failed, trying with device_map='auto'")
                self.model = WhisperForConditionalGeneration.from_pretrained(
                    self.model_path,
                    torch_dtype=self.dtype,
                    low_cpu_mem_usage=True,
                    device_map="auto"
                )
                print("  ✓ Loaded with device_map='auto'")
            
            self.model.eval()  # Set to evaluation mode
            
            # Load processor
            self.processor = WhisperProcessor.from_pretrained(
                self.model_path,
                language="turkish",
                task="transcribe"
            )
            
            # Configure generation
            self.model.config.forced_decoder_ids = None
            self.model.generation_config.language = "turkish"
            self.model.generation_config.task = "transcribe"
            
            # Optional: Use better_transformer if available
            try:
                if self.device == "cuda" and hasattr(self.model, "to_bettertransformer"):
                    self.model = self.model.to_bettertransformer()
                    print("  ✓ Using BetterTransformer optimization")
            except:
                pass
            
            self._is_loaded = True
            print(f"✓ Model loaded successfully")
            
        except Exception as e:
            print(f"✗ Error loading model: {e}")
            raise
    
    def transcribe(self, audio_path: str) -> str:
        """Transcribe audio file with proper error handling"""
        if self.model is None or self.processor is None:
            raise RuntimeError("Model not loaded. Call load_model() first.")
        
        try:
            # Load audio
            audio, sr = librosa.load(audio_path, sr=16000, mono=True)
            
            # Handle empty or very short audio
            if len(audio) < 1600:  # Less than 0.1 seconds
                return ""
            
            # Process audio
            input_features = self.processor(
                audio,
                sampling_rate=16000,
                return_tensors="pt"
            ).input_features
            
            # Get the actual device of the model (important for quantized models)
            try:
                model_device = next(self.model.parameters()).device
            except StopIteration:
                model_device = self.device
            
            # Move to device and match dtype
            # For quantized models, only move to device, don't change dtype
            try:
                input_features = input_features.to(device=model_device, dtype=self.dtype)
            except Exception:
                # If dtype conversion fails (e.g., for quantized models), just move to device
                input_features = input_features.to(device=model_device)
            
            # Generate transcription
            with torch.no_grad():
                predicted_ids = self.model.generate(
                    input_features,
                    max_new_tokens=self.config.get("max_new_tokens", 400),
                    num_beams=self.config.get("num_beams", 5),
                    language="turkish",
                    task="transcribe",
                    do_sample=False,
                    temperature=1.0
                )
            
            # Decode
            transcription = self.processor.batch_decode(
                predicted_ids,
                skip_special_tokens=True
            )[0]
            
            return transcription.strip()
            
        except Exception as e:
            print(f"⚠ Error transcribing {audio_path}: {e}")
            return ""
    
    def batch_transcribe(self, audio_paths: list) -> list:
        """Batch transcribe multiple audio files (more efficient)"""
        if self.model is None or self.processor is None:
            raise RuntimeError("Model not loaded. Call load_model() first.")
        
        results = []
        batch_size = self.config.get("batch_size", 1)
        
        # Process in batches
        for i in range(0, len(audio_paths), batch_size):
            batch_paths = audio_paths[i:i + batch_size]
            batch_audios = []
            valid_indices = []
            
            # Load batch audios
            for idx, path in enumerate(batch_paths):
                try:
                    audio, sr = librosa.load(path, sr=16000, mono=True)
                    if len(audio) >= 1600:
                        batch_audios.append(audio)
                        valid_indices.append(idx)
                except Exception as e:
                    print(f"⚠ Error loading {path}: {e}")
            
            if not batch_audios:
                results.extend([{"transcription": "", "error": "Failed to load audio"}] * len(batch_paths))
                continue
            
            try:
                # Process batch
                input_features = self.processor(
                    batch_audios,
                    sampling_rate=16000,
                    return_tensors="pt",
                    padding=True
                ).input_features
                
                # Get the actual device of the model
                try:
                    model_device = next(self.model.parameters()).device
                except StopIteration:
                    model_device = self.device
                
                # Move to device (handle quantized models)
                try:
                    input_features = input_features.to(device=model_device, dtype=self.dtype)
                except Exception:
                    input_features = input_features.to(device=model_device)
                
                # Generate
                with torch.no_grad():
                    predicted_ids = self.model.generate(
                        input_features,
                        max_new_tokens=self.config.get("max_new_tokens", 400),
                        num_beams=self.config.get("num_beams", 5),
                        language="turkish",
                        task="transcribe"
                    )
                
                # Decode
                transcriptions = self.processor.batch_decode(
                    predicted_ids,
                    skip_special_tokens=True
                )
                
                # Collect results
                batch_results = [{"transcription": "", "error": "Skipped"}] * len(batch_paths)
                for idx, trans in zip(valid_indices, transcriptions):
                    batch_results[idx] = {"transcription": trans.strip(), "error": None}
                
                results.extend(batch_results)
                
            except Exception as e:
                print(f"⚠ Error in batch processing: {e}")
                results.extend([{"transcription": "", "error": str(e)}] * len(batch_paths))
        
        return results
    
    def cleanup(self):
        """Cleanup model resources"""
        try:
            if self.model is not None:
                del self.model
                self.model = None
            
            if self.processor is not None:
                del self.processor
                self.processor = None
            
            self._is_loaded = False
            
            # Clear CUDA cache if using GPU
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
                torch.cuda.synchronize()
            
            print("✓ Model cleanup completed")
            
        except Exception as e:
            print(f"⚠ Warning during cleanup: {e}")