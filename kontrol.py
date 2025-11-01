from transformers import WhisperProcessor

checkpoint_path = "/home/ubuntu/tts-demo/whisper-multi-train/Whisper-Finetune/output/whisper-large-v3-turbo/checkpoint-26000"
base_model = "openai/whisper-large-v3-turbo"

# Processor'ı yükle ve checkpoint'e kaydet
processor = WhisperProcessor.from_pretrained(base_model)
processor.save_pretrained(checkpoint_path)

print(f"✓ Processor kaydedildi: {checkpoint_path}")
