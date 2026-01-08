"""
Inference code for Chandra OCR model on SageMaker
"""
import json
import base64
import io
import time
from PIL import Image
import torch
from transformers import Qwen3VLForConditionalGeneration, AutoProcessor
from chandra.model.hf import generate_hf
from chandra.model.schema import BatchInputItem
from chandra.output import parse_markdown

_model = None

def model_fn(model_dir):
    """Load the Chandra OCR model - called once when container starts"""
    global _model
    
    print("=" * 70)
    print("Loading Chandra OCR model")
    print("=" * 70)
    
    model_id = "datalab-to/chandra"
    
    if not torch.cuda.is_available():
        raise RuntimeError("GPU REQUIRED! Use ml.g4dn or ml.g5 instance.")
    
    print(f"GPU detected: {torch.cuda.get_device_name(0)}")
    
    _model = Qwen3VLForConditionalGeneration.from_pretrained(
        model_id,
        trust_remote_code=True,
        dtype=torch.bfloat16,
        device_map="auto",
        low_cpu_mem_usage=True
    ).eval()
    
    _model.processor = AutoProcessor.from_pretrained(model_id, trust_remote_code=True)
    
    print("Model loaded successfully!")
    return _model


def input_fn(request_body, content_type):
    """Process input - accepts base64 encoded image in JSON"""
    if content_type != "application/json":
        raise ValueError(f"Unsupported content type: {content_type}")
    
    data = json.loads(request_body)
    
    if "image" not in data:
        raise ValueError("Missing 'image' field in request body")
    
    image_bytes = base64.b64decode(data["image"])
    image = Image.open(io.BytesIO(image_bytes))
    
    return {
        "image": image,
        "prompt_type": data.get("prompt_type", "ocr_layout")
    }


def predict_fn(data, model):
    """Run OCR inference"""
    start_time = time.time()
    image = data["image"]
    prompt_type = data["prompt_type"]
    
    # Resize large images to prevent OOM
    MAX_DIMENSION = 2048
    if max(image.size) > MAX_DIMENSION:
        ratio = MAX_DIMENSION / max(image.size)
        new_size = tuple(int(dim * ratio) for dim in image.size)
        image = image.resize(new_size, Image.Resampling.LANCZOS)
    
    torch.cuda.empty_cache()
    
    batch = [BatchInputItem(image=image, prompt_type=prompt_type)]
    
    with torch.no_grad():
        result = generate_hf(batch, model, max_output_tokens=4096)[0]
    
    markdown = parse_markdown(result.raw)
    
    torch.cuda.empty_cache()
    
    duration = time.time() - start_time
    print(f"Inference completed in {duration:.2f}s")
    
    return {
        "text": markdown,
        "raw": result.raw,
        "processing_time": duration
    }


def output_fn(prediction, accept):
    """Format output as JSON"""
    return json.dumps(prediction), accept
