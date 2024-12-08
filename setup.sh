#!/bin/bash
set -e

echo "🚀 Setting up MCP-CLI development environment..."

# Get the absolute path of the script directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

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

# Check if Ollama is installed
if ! command -v ollama &> /dev/null; then
    echo "❌ Ollama is required but not found. Please install from https://ollama.ai"
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

# Upgrade pip
echo "📦 Upgrading pip..."
python -m pip install --upgrade pip

# Install project in editable mode with test dependencies
echo "📥 Installing project and dependencies..."
pip install -e ".[test]"

# Install Node.js dependencies
echo "📥 Installing Node.js dependencies..."
npm install
npm install -g @modelcontextprotocol/server-filesystem @modelcontextprotocol/server-github

# Create test directories if they don't exist
echo "🔧 Setting up test structure..."
mkdir -p tests/{unit,spec,integration}

# Run tests to verify setup
echo "🧪 Running tests..."
pytest tests/ -v

# Create server config if it doesn't exist
if [ ! -f "server_config.json" ]; then
    echo "⚙️ Creating server configuration..."
    cat > server_config.json << 'EOL'
{
  "version": "2.0.0",
  "mcpServers": {
    "filesystem": {
      "command": "npx",
      "args": [
        "-y",
        "@modelcontextprotocol/server-filesystem",
        "/Users/freebeiro/CascadeProjects/fetch_crawl4ai",
        "/Users/freebeiro/Documents/fcr/claudefiles"
      ]
    },
    "sqlite": {
      "command": "python",
      "args": [
        "-m",
        "mcp-server-sqlite",
        "--db-path",
        "/Users/freebeiro/Documents/fcr/claudefiles/claudefiles.db"
      ]
    },
    "github": {
      "command": "npx",
      "args": [
        "-y",
        "@modelcontextprotocol/server-github"
      ],
      "env": {
        "GITHUB_PERSONAL_ACCESS_TOKEN": ""
      }
    },
    "ollama": {
      "command": "ollama",
      "args": ["serve"],
      "config": {
        "model": "llama2",
        "host": "http://localhost:11434",
        "temperature": 0.7
      }
    }
  }
}
EOL
fi

# Create .env file if it doesn't exist
if [ ! -f ".env" ]; then
    echo "📝 Creating .env file..."
    cat > .env << 'EOL'
# OpenAI API Key (if using OpenAI)
# OPENAI_API_KEY=your-key-here

# Default LLM Provider (ollama or openai)
DEFAULT_LLM_PROVIDER=ollama

# Ollama Configuration
OLLAMA_HOST=http://localhost:11434
OLLAMA_MODEL=llama2
EOL
fi

# Add to existing setup.sh
pip install jsonschema rich pydantic anyio

echo "✅ Setup complete! Your development environment is ready."
echo "🔍 Run 'pytest tests/' to run tests"
echo "🚀 Run 'python chat.py' to start the MCP-CLI"
