#!/bin/bash
set -e

echo "🚀 Setting up MCP-CLI development environment..."

# Check Python version
if ! command -v python3.12 &> /dev/null; then
    echo "❌ Python 3.12 is required but not found"
    exit 1
fi

# Check Node.js version
if ! command -v node &> /dev/null; then
    echo "❌ Node.js is required but not found"
    exit 1
fi

# Create Python virtual environment if it doesn't exist
if [ ! -d "venv" ]; then
    echo "📦 Creating Python virtual environment..."
    python3.12 -m venv venv
fi

# Activate virtual environment
echo "🔄 Activating virtual environment..."
source venv/bin/activate

# Install Python dependencies
echo "📥 Installing Python dependencies..."
pip install pytest pytest-asyncio pydantic anyio

# Install Node.js dependencies
echo "📥 Installing Node.js dependencies..."
npm install

# Create server config if it doesn't exist
if [ ! -f "server_config.json" ]; then
    echo "⚙️ Creating server configuration..."
    cp server_config.json.example server_config.json
fi

# Check for get_default_environment function
if ! grep -q "get_default_environment" transport/stdio/stdio_server_parameters.py; then
    echo "🔧 Adding get_default_environment function..."
    cat >> transport/stdio/stdio_server_parameters.py << 'EOL'

def get_default_environment() -> Dict[str, str]:
    """Get the default environment variables for server processes."""
    return {
        "PYTHONUNBUFFERED": "1",  # Ensure Python output is unbuffered
        "NODE_NO_WARNINGS": "1",   # Suppress Node.js warnings
        "PATH": "/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin"  # Basic PATH
    }
EOL
fi

echo "✅ Setup complete! You can now run tests with: python -m pytest test_server_manager.py -v"
