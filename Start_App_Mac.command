#!/bin/bash

# 1. Get the folder where this script is saved
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$DIR"

# 2. Check if Python is installed
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 is not installed. Please install it from python.org"
    exit 1
fi

# 3. Create Virtual Environment if it doesn't exist
if [ ! -d ".venv" ]; then
    echo "📦 Setting up the app for the first time..."
    python3 -m venv .venv
    source .venv/bin/activate
    
    echo "⬇️ Installing libraries..."
    pip install -r requirements.txt
    echo "✅ Setup Complete!"
else
    source .venv/bin/activate
fi

# 4. Run the App
streamlit run app.py