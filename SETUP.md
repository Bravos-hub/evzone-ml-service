# ML Service Setup Guide

## Python Version Requirements

**IMPORTANT**: TensorFlow 2.15.0 requires Python 3.11 or 3.12. Python 3.14 is not yet supported.

### Option 1: Install Python 3.11 or 3.12 (Recommended)

1. Download Python 3.11 or 3.12 from [python.org](https://www.python.org/downloads/)
2. Install it (you can have multiple Python versions installed)
3. Use the specific version when creating virtual environment:

```powershell
# Using Python 3.11
py -3.11 -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
```

### Option 2: Use Existing Python 3.11/3.12

If you already have Python 3.11 or 3.12 installed:

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

### Option 3: Skip TensorFlow for Now (Development Only)

If you want to set up the service structure without TensorFlow:

1. Comment out TensorFlow in `requirements.txt`
2. Install other dependencies
3. Add TensorFlow later when you have Python 3.11/3.12

## Quick Start

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

## Verify Installation

```powershell
python --version  # Should show 3.11 or 3.12
pip list | findstr tensorflow  # Should show tensorflow installed
```

## Troubleshooting

### "pip is not recognized"
Use: `python -m pip` or `py -m pip` instead of just `pip`

### "TensorFlow not found"
- Ensure you're using Python 3.11 or 3.12
- Check: `python --version`
- Reinstall: `pip install --upgrade tensorflow`

### "No module named 'tensorflow'"
- Activate virtual environment: `venv\Scripts\activate`
- Verify installation: `pip list | findstr tensorflow`

