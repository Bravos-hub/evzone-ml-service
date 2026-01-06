# ML Service Setup Guide

## Python Version Requirements

**IMPORTANT**: TensorFlow requires Python 3.11 or 3.12. Python 3.14 is not yet supported.

**Recommendation**: **Python 3.11 is recommended** as it has better compatibility with TensorFlow and avoids Python 3.12-specific issues (like distutils removal and protobuf conflicts).

**Note**: TensorFlow 2.15.0 is no longer available on PyPI. The project uses TensorFlow 2.16.1 (works well with Python 3.11) or TensorFlow 2.17.1 (for Python 3.12).

### Option 1: Install Python 3.11 or 3.12 (Recommended)

**Linux (Ubuntu/Debian):**
```bash
# Install Python 3.11
sudo apt update
sudo apt install python3.11 python3.11-venv python3.11-dev

# Verify installation
python3.11 --version
```

**macOS:**
```bash
# Using Homebrew
brew install python@3.11

# Verify installation
python3.11 --version
```

**Windows:**
1. Download Python 3.11 from [python.org](https://www.python.org/downloads/)
2. Run the installer and check "Add Python to PATH"
3. Verify: `py -3.11 --version`

**After installing Python 3.11, use it to create the virtual environment:**

**Windows:**
```powershell
# Using Python 3.11
py -3.11 -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
```

**Linux/macOS:**
```bash
# Using Python 3.11
python3.11 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### Option 2: Use Existing Python 3.11/3.12

If you already have Python 3.11 or 3.12 installed:

**Windows:**
```powershell
# Check available Python versions
py --list

# Use specific version
py -3.11 -m venv venv
# or
py -3.12 -m venv venv

venv\Scripts\activate
pip install -r requirements.txt
```

**Linux/macOS:**
```bash
# Check available Python versions
python3.11 --version
python3.12 --version

# Use specific version
python3.11 -m venv venv
# or
python3.12 -m venv venv

source venv/bin/activate
pip install -r requirements.txt
```

### Option 3: Skip TensorFlow for Now (Development Only)

If you want to set up the service structure without TensorFlow:

1. Comment out TensorFlow in `requirements.txt`
2. Install other dependencies
3. Add TensorFlow later when you have Python 3.11/3.12

## Quick Start

**Windows:**
```powershell
# Navigate to ML service directory
cd evzone-ml-service

# Create virtual environment (use Python 3.11 or 3.12)
py -3.11 -m venv venv

# Activate virtual environment
venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Copy environment file
copy .env.example .env
# Edit .env with your configuration

# Run the service
python -m uvicorn src.main:app --reload --port 8000
```

**Linux/macOS:**
```bash
# Navigate to ML service directory
cd evzone-ml-service

# Create virtual environment (use Python 3.11 or 3.12)
python3.11 -m venv venv
# or if you have 3.12: python3.12 -m venv venv

# Activate virtual environment
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Copy environment file
cp .env.example .env
# Edit .env with your configuration

# Run the service
python -m uvicorn src.main:app --reload --port 8000
```

## Verify Installation

**Windows:**
```powershell
python --version  # Should show 3.11 or 3.12
pip list | findstr tensorflow  # Should show tensorflow installed
```

**Linux/macOS:**
```bash
python --version  # Should show 3.11 or 3.12
pip list | grep tensorflow  # Should show tensorflow installed
```

## Troubleshooting

### "pip is not recognized"
- **Windows**: Use `python -m pip` or `py -m pip` instead of just `pip`
- **Linux/macOS**: Use `python3 -m pip` or `python3.11 -m pip` instead of just `pip`

### "TensorFlow not found"
- Ensure you're using Python 3.11 or 3.12
- Check: `python --version` or `python3 --version`
- Reinstall: `pip install --upgrade tensorflow`

### "No module named 'tensorflow'"
- **Windows**: Activate virtual environment: `venv\Scripts\activate`
- **Linux/macOS**: Activate virtual environment: `source venv/bin/activate`
- Verify installation: 
  - **Windows**: `pip list | findstr tensorflow`
  - **Linux/macOS**: `pip list | grep tensorflow`

