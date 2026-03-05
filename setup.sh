#!/bin/bash
# Setup script for Personal Assistant

echo "Setting up Personal Assistant..."

# Check Python version (macOS compatible)
python_version=$(python3 --version 2>&1 | awk '{print $2}' | cut -d. -f1,2)
echo "Found Python version: $python_version"

# Create virtual environment
echo "Creating virtual environment..."
python3 -m venv venv

# Activate virtual environment
source venv/bin/activate

# Upgrade pip
echo "Upgrading pip..."
pip install --upgrade pip

# Install dependencies
echo "Installing dependencies..."
pip install -r requirements.txt

# Create necessary directories
echo "Creating directories..."
mkdir -p data config logs

# Copy environment file
if [ ! -f .env ]; then
    echo "Creating .env file from template..."
    cp .env.example .env
    echo "Please edit .env file with your configuration!"
else
    echo ".env file already exists, skipping..."
fi

# Make scripts executable
chmod +x run.sh

echo ""
echo "Setup complete!"
echo ""
echo "Next steps:"
echo "1. Edit .env file with your configuration:"
echo "   nano .env"
echo ""
echo "2. (Optional) Set up Ollama for local LLM:"
echo "   curl https://ollama.ai/install.sh | sh"
echo "   ollama pull llama3.1:8b"
echo ""
echo "3. Start the server:"
echo "   ./run.sh"
echo "   or"
echo "   python -m src.cli server"
echo ""
echo "4. Try the CLI:"
echo "   python -m src.cli briefing"
echo "   python -m src.cli ask 'What can you help me with?'"
echo ""
