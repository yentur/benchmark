# deepgram_model.py (SDK YERİNE DOĞRUDAN HTTP API KULLANAN VERSİYON)

import os
import requests  # deepgram-sdk yerine requests kullanıyoruz
from typing import Dict, Any

from model import BaseSTTModel, ModelFactory

@ModelFactory.register("deepgram")
class DeepgramModel(BaseSTTModel):
    """Deepgram REST API'sini doğrudan kullanarak deşifre yapan model sınıfı"""

    def __init__(self, model_path: str, config: Dict[str, Any]):
        super().__init__(model_path, config)
        self.api_key = os.getenv("DEEPGRAM_API_KEY")
        if not self.api_key:
            raise ValueError("DEEPGRAM_API_KEY ortam değişkeni bulunamadı!")
        
        # API bilgilerini burada tanımlayalım
        self.api_url = "https://api.deepgram.com/v1/listen"
        self.headers = {
            "Authorization": f"Token {self.api_key}",
            # Benchmark sistemi .wav dosyaları oluşturduğu için Content-Type'ı güncelledik
            "Content-Type": "audio/wav"  
        }
        # Hangi modelin kullanılacağını config.yaml'daki 'path' alanından alıyoruz
        self.model_name = model_path
        self._is_loaded = False

    def load_model(self):
        """API tabanlı olduğu için model yükleme işlemi yok."""
        print("✓ Deepgram istemcisi (Doğrudan HTTP API) hazır.")
        self._is_loaded = True

    def transcribe(self, audio_path: str) -> str:
        """
        Bir ses dosyasını Deepgram'e HTTP POST isteği ile gönderir ve deşifreyi alır.
        """
        if not self._is_loaded:
            self.load_model()
        
        try:
            # API'ye gönderilecek parametreler
            params = {
                "model": self.model_name,
                "language": "tr",
                "smart_format": "true",
                "punctuate": "true"
            }

            # Ses dosyasını binary modda oku
            with open(audio_path, "rb") as audio_file:
                # POST isteğini yap
                response = requests.post(
                    self.api_url,
                    headers=self.headers,
                    params=params,
                    data=audio_file
                )
            
            # Yanıtı kontrol et
            if response.status_code == 200:
                result = response.json()
                transcript = result['results']['channels'][0]['alternatives'][0]['transcript']
                return transcript.strip()
            else:
                # Hata durumunda loglama yap
                print(f"⚠ Deepgram API Hatası (Kod: {response.status_code}): {response.text}")
                return ""

        except Exception as e:
            print(f"⚠ Deepgram deşifre sırasında beklenmedik hata ({audio_path}): {e}")
            return ""

    def cleanup(self):
        """API tabanlı olduğu için kaynak temizleme işlemi yok."""
        self._is_loaded = False
        print("✓ Deepgram modeli temizlendi.")