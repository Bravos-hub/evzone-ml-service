#!/bin/bash
# Data pipeline script for processing training data

set -e

echo "Starting data pipeline..."

# Ensure we're running from the project root
cd "$(dirname "$0")/.."

# Load environment variables if .env exists
if [ -f .env ]; then
    export $(grep -v '^#' .env | xargs)
fi

# Use DATABASE_URL or default
DB_URL=${DATABASE_URL:-"postgresql://user:password@localhost:5432/evzone_ml"}

# Create datasets directory
DATA_DIR="src/ml/data/datasets"
mkdir -p "$DATA_DIR"

RAW_DATA_FILE="$DATA_DIR/raw_data.csv"
PROCESSED_DATA_FILE="$DATA_DIR/processed_data.csv"

# Extract data from database
echo "Extracting data from database..."
# Check if psql is available, if not, skip extraction with a warning
if command -v psql &> /dev/null; then
    # In a real scenario, this would select specific columns.
    # We use a dummy query if the table charger_metrics doesn't exist to avoid pipeline failure,
    # or just export a subset of chargers.
    psql "$DB_URL" -c "\copy (SELECT * FROM charger_metrics LIMIT 10000) TO '$RAW_DATA_FILE' WITH CSV HEADER;" || {
        echo "Warning: Failed to extract data using psql. Creating an empty dummy raw data file."
        echo "charger_id,connector_status,energy_delivered,power,temperature,error_codes,uptime_hours,total_sessions,last_maintenance,failure_within_30d_label" > "$RAW_DATA_FILE"
    }
else
    echo "Warning: psql not found. Creating a dummy raw data file."
    echo "charger_id,connector_status,energy_delivered,power,temperature,error_codes,uptime_hours,total_sessions,last_maintenance,failure_within_30d_label" > "$RAW_DATA_FILE"
fi

# Inline Python script for Preprocessing, Cleaning, and Feature Engineering
echo "Preprocessing, cleaning, and feature engineering..."
python3 -c "
import pandas as pd
import numpy as np
import ast
from datetime import datetime, timezone
import os

raw_file = '$RAW_DATA_FILE'
processed_file = '$PROCESSED_DATA_FILE'

if not os.path.exists(raw_file):
    print(f'Raw file {raw_file} not found.')
    exit(1)

df = pd.read_csv(raw_file)

if df.empty:
    print('Warning: Raw dataset is empty. Proceeding with an empty dataframe.')
    df.to_csv(processed_file, index=False)
    exit(0)

# Preprocessing and Cleaning
def parse_error_codes(val):
    if pd.isna(val) or val is None:
        return []
    if isinstance(val, list):
        return val
    s = str(val)
    if not s.strip():
        return []
    try:
        parsed = ast.literal_eval(s)
        return parsed if isinstance(parsed, list) else []
    except Exception:
        return []

# Feature Engineering
STATUS_TO_INT = {'AVAILABLE': 0, 'CHARGING': 1, 'FAULTED': 2, 'OFFLINE': 3, 'MAINTENANCE': 4}
status_series = df.get('connector_status', pd.Series('AVAILABLE', index=df.index))
df['status_int'] = status_series.fillna('AVAILABLE').astype(str).str.upper().map(STATUS_TO_INT).fillna(0).astype(int)

error_codes_col = df.get('error_codes', pd.Series('[]', index=df.index))
df['error_count'] = error_codes_col.apply(parse_error_codes).apply(len).astype(int)

now = datetime.now(timezone.utc)
lm_col = df.get('last_maintenance')
if lm_col is not None:
    lm_series = pd.to_datetime(lm_col, errors='coerce', utc=True)
    days_since_maint = (now - lm_series).dt.total_seconds() / 86400.0
    df['days_since_maintenance'] = days_since_maint.fillna(9999.0).clip(lower=0.0)
else:
    df['days_since_maintenance'] = 9999.0

numeric_cols = ['energy_delivered', 'power', 'temperature', 'uptime_hours', 'total_sessions']
for col in numeric_cols:
    if col in df.columns:
        df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0.0)
    else:
        df[col] = 0.0

# Store processed data
# We keep standard numeric features and any labels, dropping some raw columns
cols_to_keep = ['charger_id', 'status_int', 'energy_delivered', 'power', 'temperature',
                'error_count', 'uptime_hours', 'total_sessions', 'days_since_maintenance']
if 'failure_within_30d_label' in df.columns:
    cols_to_keep.append('failure_within_30d_label')

final_df = df[[c for c in cols_to_keep if c in df.columns]]
final_df.to_csv(processed_file, index=False)
print(f'Processed data saved to {processed_file}')
"

echo "Data pipeline completed!"
