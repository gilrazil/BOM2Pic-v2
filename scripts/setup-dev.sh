#!/bin/bash
# Development Environment Setup

echo "🛠️ Setting up BOM2Pic for LOCAL DEVELOPMENT..."

# Copy environment template if .env doesn't exist
if [ ! -f .env ]; then
    cp .env.example .env
    echo "✅ Created .env file from template"
    echo "📝 Please edit .env with your local settings"
else
    echo "ℹ️ .env file already exists"
fi

# Activate virtual environment
if [ -d "venv" ]; then
    source venv/bin/activate
    echo "✅ Activated virtual environment"
else
    echo "❌ Virtual environment not found. Run: python3 -m venv venv"
    exit 1
fi

# Install dependencies
pip install -r requirements.txt
echo "✅ Dependencies installed"

# Initialize database
python3 -c "from app.auth import init_database; init_database(); print('✅ Database initialized')"

echo "🚀 Development setup complete!"
echo "🌐 Run: uvicorn app.main:app --reload --host 0.0.0.0 --port 8000"
echo "🔗 Open: http://localhost:8000"
