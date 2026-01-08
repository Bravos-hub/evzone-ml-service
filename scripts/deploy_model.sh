#!/bin/bash
# Deploy model script

set -e

MODEL_NAME=$1
RAW_VERSION=$2

if [ -z "$MODEL_NAME" ] || [ -z "$RAW_VERSION" ]; then
    echo "Usage: ./deploy_model.sh <model_name> <version>"
    exit 1
fi

if [[ "$RAW_VERSION" =~ ^[vV] ]]; then
    VERSION="V${RAW_VERSION:1}"
else
    VERSION="V${RAW_VERSION}"
fi

MODEL_REGISTRY_PATH="${MODEL_REGISTRY_PATH:-./models}"
MODEL_REGISTRY_PATH="${MODEL_REGISTRY_PATH%/}"
MODEL_DIR="${MODEL_REGISTRY_PATH}/${MODEL_NAME}/${RAW_VERSION}"

if [ ! -d "$MODEL_DIR" ] && [ "$RAW_VERSION" != "$VERSION" ]; then
    MODEL_DIR="${MODEL_REGISTRY_PATH}/${MODEL_NAME}/${VERSION}"
fi

if [ ! -d "$MODEL_DIR" ]; then
    echo "Error: Model directory not found: $MODEL_DIR"
    exit 1
fi

echo "Deploying model: $MODEL_NAME $VERSION"
echo "Model directory: $MODEL_DIR"

PROD_BASE="${MODEL_BASE_PATH:-./models}"
PROD_BASE="${PROD_BASE%/}"

if [ ! -d "$PROD_BASE" ]; then
    mkdir -p "$PROD_BASE"
fi

ARTIFACTS=()
case "$MODEL_NAME" in
    failure_predictor|failure)
        ARTIFACTS=("failure_model.joblib")
        ;;
    anomaly_detector|anomaly)
        ARTIFACTS=("anomaly_model.joblib")
        ;;
    maintenance_optimizer|maintenance_scheduler|maintenance)
        ARTIFACTS=("maintenance_model.joblib")
        ;;
esac

if [ ${#ARTIFACTS[@]} -gt 0 ]; then
    echo "Copying model artifacts to: $PROD_BASE"
    for artifact in "${ARTIFACTS[@]}"; do
        SRC_FILE="${MODEL_DIR}/${artifact}"
        if [ ! -f "$SRC_FILE" ]; then
            echo "Error: Missing artifact: $SRC_FILE" >&2
            exit 1
        fi
        cp -a "$SRC_FILE" "$PROD_BASE"/
    done
else
    echo "Copying all artifacts to: $PROD_BASE"
    cp -a "$MODEL_DIR"/. "$PROD_BASE"/
fi

METADATA_DIR="${PROD_BASE}/metadata"
METADATA_FILE="${METADATA_DIR}/${MODEL_NAME}.json"
DEPLOYED_AT="$(date -u +"%Y-%m-%dT%H:%M:%SZ")"

mkdir -p "$METADATA_DIR"
cat > "$METADATA_FILE" <<EOF
{
  "name": "$MODEL_NAME",
  "version": "$VERSION",
  "deployed_at": "$DEPLOYED_AT",
  "source_dir": "$MODEL_DIR",
  "path": "$PROD_BASE"
}
EOF

ML_SERVICE_URL="${ML_SERVICE_URL:-http://localhost:8000}"
RELOAD_URL="${ML_SERVICE_URL%/}/api/v1/models/reload"
API_KEY_VALUE="${ML_SERVICE_API_KEY:-${API_KEY:-}}"

if [ -n "$API_KEY_VALUE" ]; then
    echo "Triggering model reload via: $RELOAD_URL"
    if ! curl -sS -X POST -H "X-API-Key: $API_KEY_VALUE" "${RELOAD_URL}?model_name=${MODEL_NAME}" > /dev/null; then
        echo "Warning: Failed to trigger model reload." >&2
    fi
else
    echo "Warning: API key not set; skipping model reload request." >&2
fi

echo "Model deployed successfully!"
