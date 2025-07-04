#!/usr/bin/env bash

###############################################################################
# install.sh - Setup script for backend_fastapi (TestAssist GeminiBot)
# This script installs Docker, Docker Compose, Python 3.8+, pip, venv,
# and Python dependencies to run the FastAPI backend and local Postgres DB.
#
# Usage:
#   $ bash install.sh
#
# For non-Linux OS (macOS, Windows), see the instructions at the end of this file.
###############################################################################

set -e

echo "========== [TestAssist GeminiBot: FastAPI Backend Setup] =========="

# ---- 1. OS Detection ----
if [[ "$OSTYPE" == "linux-gnu"* ]]; then
    OS="Linux"
elif [[ "$OSTYPE" == "darwin"* ]]; then
    OS="macOS"
elif [[ "$OSTYPE" == "msys" || "$OSTYPE" == "win32" ]]; then
    OS="Windows"
else
    OS="Unknown"
fi

echo "Detected OS: $OS"
if [[ "$OS" != "Linux" ]]; then
    echo "NOTE: This script is intended for Ubuntu/Debian Linux."
    echo "      For macOS or Windows/WSL, see instructions at the end of this file."
fi

# ---- 2. Install Docker ----
echo "---- [1/5] Installing Docker ... ----"
if ! command -v docker &>/dev/null; then
    echo "Docker not found. Installing Docker ..."
    # For Ubuntu/Debian
    sudo apt-get update -y
    sudo apt-get install -y \
        ca-certificates \
        curl \
        gnupg \
        lsb-release
    # Add Docker's official GPG key
    sudo install -m 0755 -d /etc/apt/keyrings
    curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg
    sudo chmod a+r /etc/apt/keyrings/docker.gpg
    # Add Docker repo
    echo \
      "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu \
      $(lsb_release -cs) stable" | \
      sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
    sudo apt-get update -y
    sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
    sudo systemctl enable docker
    sudo systemctl start docker
    echo "Docker installed!"
else
    echo "Docker already installed. Skipping."
fi

# ---- 3. Install Docker Compose (if not present) ----
echo "---- [2/5] Checking Docker Compose ... ----"
if ! command -v docker-compose &>/dev/null; then
    # Prefer using the plugin (since docker-ce > 20.10)
    if docker compose version &>/dev/null; then
        echo "Docker Compose plugin found!"
    else
        echo "docker-compose not found. Installing legacy docker-compose ..."
        sudo curl -L "https://github.com/docker/compose/releases/download/v2.29.2/docker-compose-$(uname -s)-$(uname -m)" \
          -o /usr/local/bin/docker-compose
        sudo chmod +x /usr/local/bin/docker-compose
    fi
else
    echo "docker-compose is available."
fi

# ---- 4. Python 3.8+ and pip ----
echo "---- [3/5] Checking Python installation ... ----"
PYTHON=''
if command -v python3 &>/dev/null; then
    pyv=$(python3 -c "import sys; print('.'.join(map(str, sys.version_info[:3])))")
    if [[ $pyv > "3.7" ]]; then
        PYTHON=python3
    fi
fi
if [[ -z "$PYTHON" ]]; then
    echo "Python 3.8+ not found. Installing python3, python3-venv, and python3-pip ..."
    sudo apt-get update -y
    sudo apt-get install -y python3 python3-venv python3-pip
    PYTHON=python3
else
    echo "Python version $pyv found"
fi

# ---- 5. Create Python Virtual Environment ----
echo "---- [4/5] Setting up Python virtual environment ... ----"
cd "$(dirname "$0")"
if [[ ! -d ".venv" ]]; then
    $PYTHON -m venv .venv
    echo "Virtual environment created at .venv/"
fi
source .venv/bin/activate

# ---- 6. Install Python Packages ----
echo "---- [5/5] Installing Python packages from requirements.txt ... ----"
$PYTHON -m pip install --upgrade pip
$PYTHON -m pip install -r requirements.txt
echo "All Python dependencies installed!"

echo "==================================================================="
echo "SETUP COMPLETE! Next Steps:"
echo ""
echo "  1. To start the local PostgreSQL DB: "
echo "      (from this backend_fastapi folder)"
echo "      $ docker compose up -d"
echo ""
echo "  2. To run the FastAPI server (use Python venv):"
echo "      $ source .venv/bin/activate"
echo "      $ uvicorn src.api.main:app --host 0.0.0.0 --port 3001 --reload"
echo ""
echo "  3. Backend API will be live at: http://localhost:3001"
echo ""
echo "  4. Use Swagger API docs at: http://localhost:3001/docs"
echo ""
echo "  5. To shut down the DB: $ docker compose down"
echo ""
echo "For any issues, refer to README or the documentation."
echo "==================================================================="

###############################################################################
cat << 'MACOS_NOTE' >/dev/null
For macOS users:
- Install Docker Desktop from https://www.docker.com/products/docker-desktop/
- Install Homebrew: https://brew.sh/
- brew install python
- python3 -m venv .venv && source .venv/bin/activate
- pip install -r requirements.txt

For Windows users:
- Install Docker Desktop for Windows
- Use "WSL2" for best compatibility, install Python from https://www.python.org/downloads/ (ensure 3.8+)
- Setup venv & pip as per Python docs
- Run Docker and backend server as on Linux/Mac
MACOS_NOTE
###############################################################################

