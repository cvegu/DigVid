#!/bin/bash
# Sonivo - Start Script

# Activate virtual environment if it exists
if [ -d "venv" ]; then
    source venv/bin/activate
fi

# Create necessary directories
mkdir -p uploads outputs

# Check for FFmpeg
if ! command -v ffmpeg &> /dev/null; then
    echo "❌ FFmpeg is not installed. Please install it first:"
    echo "   macOS: brew install ffmpeg"
    echo "   Ubuntu: sudo apt-get install ffmpeg"
    exit 1
fi

echo "🎵 Starting Sonivo server..."
echo "   Open http://localhost:8000 in your browser"
echo ""

uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
