from transformers import Wav2Vec2ForCTC, Wav2Vec2Processor
import torch
import librosa
from model import BaseSTTModel, ModelFactory

@ModelFactory.register("wav2vec2")
class Wav2Vec2Model(BaseSTTModel):
    """Wav2Vec2 model implementation"""

    def __init__(self, model_path: str, config: dict):
        super().__init__(model_path, config)
        self.device = None
        self._is_loaded = False

    def _get_device(self):
        """Get proper device configuration"""
        device_config = self.config.get("device", "auto")
        if device_config == "auto":
            return "cuda" if torch.cuda.is_available() else "cpu"
        return device_config

    def load_model(self):
        """Load Wav2Vec2 model and processor"""
        try:
            self.device = self._get_device()
            
            print(f"Loading Wav2Vec2 model...")
            print(f"  Model: {self.model_path}")
            print(f"  Device: {self.device}")

            # Load processor and model
            self.processor = Wav2Vec2Processor.from_pretrained(self.model_path)
            self.model = Wav2Vec2ForCTC.from_pretrained(self.model_path)
            
            self.model.to(self.device)
            self.model.eval()
            
            self._is_loaded = True
            print(f"✓ Model loaded successfully")

        except Exception as e:
            print(f"✗ Error loading Wav2Vec2 model: {e}")
            raise

    def transcribe(self, audio_path: str) -> str:
        """Transcribe a single audio file"""
        if not self._is_loaded:
            raise RuntimeError("Model not loaded. Call load_model() first.")

        try:
            # Load and resample audio
            audio, sr = librosa.load(audio_path, sr=16000, mono=True)

            if len(audio) == 0:
                return ""

            # Process audio
            input_values = self.processor(
                audio, 
                sampling_rate=16000, 
                return_tensors="pt", 
                padding=True
            ).input_values

            input_values = input_values.to(self.device)

            # Get logits
            with torch.no_grad():
                logits = self.model(input_values).logits

            # Decode logits to text
            predicted_ids = torch.argmax(logits, dim=-1)
            transcription = self.processor.batch_decode(predicted_ids)[0]
            
            return transcription.strip()

        except Exception as e:
            print(f"⚠ Error transcribing {audio_path}: {e}")
            return ""