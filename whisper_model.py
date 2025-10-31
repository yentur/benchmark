from transformers import WhisperForConditionalGeneration, WhisperProcessor
import torch
import librosa
from model import BaseSTTModel, ModelFactory

@ModelFactory.register("whisper")
class WhisperModel(BaseSTTModel):
    """Whisper model implementation"""
    
    def load_model(self):
        """Load Whisper model and processor"""
        dtype = torch.float16 if self.config.get("torch_dtype") == "float16" else torch.float32
        
        # Parse device - convert "auto" to actual device
        device_config = self.config.get("device", "auto")
        if device_config == "auto":
            device = "cuda" if torch.cuda.is_available() else "cpu"
        else:
            device = device_config
        
        print(f"Loading Whisper model on device: {device}")
        
        # Load WITHOUT device_map to avoid meta device issues in multi-threaded context
        self.model = WhisperForConditionalGeneration.from_pretrained(
            self.model_path,
            torch_dtype=dtype,
            low_cpu_mem_usage=False  # Prevents meta device issues
        )
        
        # Manually move to device AFTER loading
        self.model = self.model.to(device)
        
        self.processor = WhisperProcessor.from_pretrained(
            self.model_path,
            language="turkish",
            task="transcribe"
        )
        
        # Model configuration
        self.model.config.forced_decoder_ids = None
        self.model.generation_config.language = "turkish"
        self.model.generation_config.task = "transcribe"
        
        print(f"✓ Loaded Whisper model on {device}: {self.model_path}")
        
    def transcribe(self, audio_path: str) -> str:
        """Transcribe audio file"""
        if self.model is None or self.processor is None:
            self.load_model()
        
        device = next(self.model.parameters()).device
        
        # Load and process audio
        audio, _ = librosa.load(audio_path, sr=16000)
        
        input_features = self.processor(
            audio,
            sampling_rate=16000,
            return_tensors="pt"
        ).input_features
        
        # Match device and dtype with model
        dtype = next(self.model.parameters()).dtype
        input_features = input_features.to(device=device, dtype=dtype)
        
        # Generate transcription
        with torch.no_grad():
            predicted_ids = self.model.generate(
                input_features,
                max_new_tokens=self.config.get("max_new_tokens", 400),
                num_beams=self.config.get("num_beams", 5),
                language="turkish",
                task="transcribe"
            )
        
        transcription = self.processor.batch_decode(
            predicted_ids,
            skip_special_tokens=True
        )[0]
        
        return transcription.strip()