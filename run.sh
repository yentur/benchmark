#!/bin/bash

# Speech-to-Text Benchmark Runner
# Bu script benchmark sistemini başlatır

echo "=========================================="
echo "  STT Benchmark System"
echo "=========================================="
echo ""

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "❌ Virtual environment bulunamadı!"
    echo "Lütfen önce şunu çalıştırın:"
    echo "  python -m venv venv"
    echo "  source venv/bin/activate"
    echo "  pip install -r requirements.txt"
    exit 1
fi

# Activate virtual environment
echo "🔧 Virtual environment aktive ediliyor..."
source venv/bin/activate

# Check if dependencies are installed
if ! python -c "import transformers" 2>/dev/null; then
    echo "❌ Bağımlılıklar yüklenmemiş!"
    echo "Yükleniyor..."
    pip install -r requirements.txt
fi

# Create results directory
mkdir -p results
mkdir -p static

echo ""
echo "🚀 Her iki mod da başlatılıyor..."
echo "API: http://localhost:8000"
echo ""

# Start API in background
python api.py &
API_PID=$!
echo "API PID: $API_PID"
echo ""
echo "Dashboard hazır olana kadar bekleyin (5 saniye)..."
sleep 5
echo ""
echo "Dashboard açılıyor: http://localhost:8000"

# Open browser (works on Mac and Linux)
if [[ "$OSTYPE" == "darwin"* ]]; then
    open http://localhost:8000
else
    xdg-open http://localhost:8000 2>/dev/null || echo "Tarayıcınızda manuel olarak açın: http://localhost:8000"
fi

echo ""
echo "🚀 Benchmark başlatılıyor..."
python main.py

echo ""
echo "API çalışıyor. Durdurmak için Ctrl+C"
# Wait for API process
wait $API_PID

echo ""
echo "✅ Tamamlandı!"
