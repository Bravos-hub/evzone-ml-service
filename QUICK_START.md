# Quick Start Guide

## Current Situation

You have **Python 3.14.2** installed, but the ML service dependencies (especially TensorFlow and some packages like pydantic-core) require **Python 3.11 or 3.12**.

## Recommended Solution: Install Python 3.11 or 3.12

### Step 1: Download Python 3.11 or 3.12

1. Go to [python.org/downloads](https://www.python.org/downloads/)
2. Download Python 3.11.9 or Python 3.12.7 (latest stable versions)
3. **Important**: During installation, check "Add Python to PATH"

### Step 2: Verify Installation

```powershell
# Check available Python versions
py --list

# You should see something like:
# -V:3.11 *   Python 3.11.9
# -V:3.14     Python 3.14.2
```

### Step 3: Create Virtual Environment with Python 3.11

```powershell
cd C:\Users\user\Desktop\evzone-portal\evzone-ml-service

# Create venv with Python 3.11
py -3.11 -m venv venv

# Activate virtual environment
venv\Scripts\activate

# Verify Python version
python --version  # Should show 3.11.x

# Install dependencies
pip install -r requirements.txt
```

## Alternative: Use Docker (Easier)

If you prefer not to install Python 3.11/3.12, use Docker:

```powershell
cd C:\Users\user\Desktop\evzone-portal\evzone-ml-service

# Build and run with Docker
docker-compose up -d
```

This uses a Python 3.11 base image and handles all dependencies automatically.

## What's Working Now

The ML service structure is complete and ready. You just need:
1. Python 3.11 or 3.12 installed
2. Dependencies installed
3. Environment configured

## Next Steps After Setup

1. Copy `.env.example` to `.env` and configure
2. Run the service: `python -m uvicorn src.main:app --reload`
3. Test: Visit `http://localhost:8000/docs`

## Need Help?

- See `SETUP.md` for detailed setup instructions
- See `README.md` for service overview
- See `INTEGRATION.md` for backend integration

