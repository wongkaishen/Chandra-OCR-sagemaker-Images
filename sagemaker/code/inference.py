
import json
import base64
import io
import subprocess
import sys
import time
import os
from PIL import Image
import importlib

# Force install transformers at the very beginning
try:
    subprocess.check_call([sys.executable, "-m", "pip", "install", "transformers>=4.46.0", "accelerate>=0.26.0", "--upgrade", "--no-cache-dir"])
except Exception as e:
    print(f"Error installing transformers: {e}")

# Aggressively reload pkg_resources and transformers
import pkg_resources
importlib.reload(pkg_resources)

import transformers
importlib.reload(transformers)

print(f"Transformers version: {transformers.__version__}")

from transformers import AutoProcessor, Qwen3VLForConditionalGeneration
import torch

def model_fn(model_dir):
    """Load the Chandra OCR model"""
    print("Loading Chandra OCR model...")
    model_id = "datalab-to/chandra"
    
    # REQUIRE GPU
    if not torch.cuda.is_available():
        raise RuntimeError("❌ GPU REQUIRED! Use ml.g4dn or ml.g5 instance.")
    
    print(f"✅ GPU detected: {torch.cuda.get_device_name(0)}")
    print(f"✅ CUDA version: {torch.version.cuda}")
    
    processor = AutoProcessor.from_pretrained(model_id, trust_remote_code=True)
    model = Qwen3VLForConditionalGeneration.from_pretrained(
        model_id,
        trust_remote_code=True,
        dtype=torch.bfloat16,  # Use bfloat16, not float16
        device_map="auto",
        low_cpu_mem_usage=True
    )
    model = model.eval()
    
    # Enable gradient checkpointing
    if hasattr(model, 'gradient_checkpointing_enable'):
        model.gradient_checkpointing_enable()
    
    return {"model": model, "processor": processor}

def input_fn(request_body, content_type):
    """Process input data"""
    if content_type == "application/json":
        data = json.loads(request_body)
        
        # Decode base64 image
        if "image" in data:
            image_b64 = data["image"]
            image_bytes = base64.b64decode(image_b64)
            image = Image.open(io.BytesIO(image_bytes))
            return {
                "image": image,
                "max_output_tokens": data.get("max_output_tokens", 4096)
            }
    
    raise ValueError(f"Unsupported content type: {content_type}")

def predict_fn(data, model_dict):
    """Run OCR inference"""
    start_time = time.time()
    model = model_dict["model"]
    processor = model_dict["processor"]
    image = data["image"]
    max_tokens = data["max_output_tokens"]
    
    print(f"Image size: {image.size}")
    
    # Resize large images to prevent timeout/OOM
    MAX_DIMENSION = 2048
    if max(image.size) > MAX_DIMENSION:
        ratio = MAX_DIMENSION / max(image.size)
        new_size = tuple(int(dim * ratio) for dim in image.size)
        print(f"Resizing from {image.size} to {new_size}")
        image = image.resize(new_size, Image.Resampling.LANCZOS)
    
    # Clear GPU cache
    torch.cuda.empty_cache()
    
    # Process image
    inputs = processor(images=image, return_tensors="pt").to(model.device)
    
    # Generate text
    print(f"Running inference (max {max_tokens} tokens)...")
    with torch.no_grad():
        outputs = model.generate(
            **inputs,
            max_new_tokens=max_tokens,
            do_sample=False
        )
    
    # Decode output
    text = processor.batch_decode(outputs, skip_special_tokens=True)[0]
    
    # Clear GPU cache
    torch.cuda.empty_cache()
    
    duration = time.time() - start_time
    print(f"✅ Inference completed in {duration:.2f} seconds")
    
    return {
        "text": text,
        "confidence": 0.9,
        "processing_time": duration
    }

def output_fn(prediction, accept):
    """Format output"""
    return json.dumps(prediction), accept
