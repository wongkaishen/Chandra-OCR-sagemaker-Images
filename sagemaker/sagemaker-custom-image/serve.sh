#!/bin/bash
# SageMaker startup script for Chandra OCR
# This script starts the Flask app with gunicorn
# SageMaker will call this with 'serve' as an argument - we ignore it

set -e

echo "======================================================================="
echo "Starting Chandra OCR SageMaker Endpoint"
echo "Arguments passed: $@"
echo "======================================================================="
echo "Working directory: $(pwd)"
echo "Python version: $(python --version)"
echo "Gunicorn version: $(gunicorn --version)"
echo "Transformers version: $(python -c 'import transformers; print(transformers.__version__)')"
echo "Torch version: $(python -c 'import torch; print(torch.__version__)')"
echo "CUDA available: $(python -c 'import torch; print(torch.cuda.is_available())')"
echo "======================================================================="

# Set PYTHONPATH
export PYTHONPATH=/opt/ml/code:$PYTHONPATH

# Start gunicorn (ignore any arguments like 'serve' that SageMaker passes)
echo "Starting gunicorn server on 0.0.0.0:8080..."
exec gunicorn \
    --bind=0.0.0.0:8080 \
    --workers=1 \
    --worker-class=sync \
    --timeout=3600 \
    --graceful-timeout=3600 \
    --keep-alive=60 \
    --log-level=info \
    --access-logfile=- \
    --error-logfile=- \
    app:app
