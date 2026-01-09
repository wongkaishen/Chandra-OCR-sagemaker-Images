FROM python:3.10-slim

# Install system dependencies including curl for health checks
RUN apt-get update && apt-get install -y \
    libgomp1 \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /opt/ml/code

# Copy requirements and install Python dependencies
COPY requirements.txt .

# CRITICAL: Install PyTorch with CUDA 11.8 FIRST, explicitly from cu118 index
# Default pip will install cu121/cu124 which is incompatible with ml.g4dn (CUDA 11.0.4)
RUN pip install --no-cache-dir \
    --index-url https://download.pytorch.org/whl/cu118 \
    torch torchvision

# Install remaining dependencies from requirements.txt (excluding torch/torchvision)
RUN pip install --no-cache-dir \
    flask \
    gunicorn \
    "numpy>=1.24.0,<2.0.0" \
    "transformers>=4.46.0" \
    "pillow>=9.0.0" \
    "accelerate>=0.26.0" \
    qwen-vl-utils \
    huggingface-hub \
    six \
    beautifulsoup4 \
    markdownify \
    pydantic-settings \
    python-dotenv \
    filetype \
    pypdfium2 \
    openai

# Install chandra-ocr LAST with --no-deps to prevent it from reinstalling PyTorch
# This ensures we keep the CUDA 11.8 version compatible with ml.g4dn instances
RUN pip install --no-deps chandra-ocr

# Copy inference code
COPY src/ /opt/ml/code/src/
COPY app.py /opt/ml/code/
COPY serve /opt/ml/code/serve

# Make serve script executable
RUN chmod +x /opt/ml/code/serve

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV MODEL_PATH=/opt/ml/model
ENV PYTHONPATH=/opt/ml/code:$PYTHONPATH

# Expose port for SageMaker
EXPOSE 8080

# Set PATH to include our serve script
ENV PATH="/opt/ml/code:${PATH}"

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=300s --retries=3 \
    CMD curl -f http://localhost:8080/ping || exit 1

# SageMaker will execute 'serve' when the container starts
# No need for CMD or ENTRYPOINT - SageMaker calls /opt/ml/code/serve automatically
