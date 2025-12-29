"""
Custom inference code for Chandra OCR model
Using official chandra-ocr package from Hugging Face
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

# Global variables for model
_model = None

def model_fn(model_dir):
    """
    Load the Chandra OCR model using official package
    Called once when the container starts
    """
    global _model
    
    print("="*70)
    print("Loading Chandra OCR model using official chandra-ocr package")
    print("="*70)
    
    # Import and print versions
    import transformers
    print(f"Transformers version: {transformers.__version__}")
    print(f"Torch version: {torch.__version__}")
    
    model_id = "datalab-to/chandra"
    
    # REQUIRE GPU - Fail if not available
    if not torch.cuda.is_available():
        error_msg = (
            "❌ FATAL ERROR: GPU/CUDA is NOT available!\n"
            "This model REQUIRES a GPU instance.\n"
            "Please use ml.g4dn.xlarge or ml.g4dn.2xlarge instance type.\n"
            "Current instance appears to be CPU-only."
        )
        print("="*70)
        print(error_msg)
        print("="*70)
        raise RuntimeError(error_msg)
    
    # GPU is available - proceed
    print(f"✅ CUDA available: True")
    print(f"✅ GPU detected: {torch.cuda.get_device_name(0)}")
    print(f"✅ CUDA version: {torch.version.cuda}")
    print(f"Loading model from {model_id} to GPU...")
    
    # Load model with memory optimization
    # Use bfloat16 for lower memory footprint (half of float32)
    print("Loading model with bfloat16 precision for memory efficiency...")
    _model = Qwen3VLForConditionalGeneration.from_pretrained(
        model_id,
        trust_remote_code=True,
        dtype=torch.bfloat16,  # Use bfloat16 to reduce memory usage
        device_map="auto",  # Automatically distribute model across devices
        low_cpu_mem_usage=True  # Optimize CPU memory during loading
    )
    _model = _model.eval()  # Set to evaluation mode
    
    # Enable gradient checkpointing to reduce memory during inference
    if hasattr(_model, 'gradient_checkpointing_enable'):
        _model.gradient_checkpointing_enable()
        print("✅ Gradient checkpointing enabled")
    
    print("Loading processor...")
    _model.processor = AutoProcessor.from_pretrained(
        model_id,
        trust_remote_code=True
    )
    
    # Print memory stats
    if torch.cuda.is_available():
        allocated = torch.cuda.memory_allocated(0) / 1024**3
        reserved = torch.cuda.memory_reserved(0) / 1024**3
        print(f"📊 GPU Memory - Allocated: {allocated:.2f}GB, Reserved: {reserved:.2f}GB")
    
    print("✅ Model loaded successfully on GPU!")
    print("="*70)
    
    return _model

def input_fn(request_body, content_type):
    """
    Process input data
    """
    if content_type == "application/json":
        data = json.loads(request_body)
        
        # Decode base64 image
        if "image" in data:
            image_b64 = data["image"]
            image_bytes = base64.b64decode(image_b64)
            image = Image.open(io.BytesIO(image_bytes))
            return {
                "image": image,
                "prompt_type": data.get("prompt_type", "ocr_layout")
            }
    
    raise ValueError(f"Unsupported content type: {content_type}")

def predict_fn(data, model):
    """
    Run OCR inference using official Chandra method
    """
    start_time = time.time()
    image = data["image"]
    prompt_type = data["prompt_type"]
    
    print(f"Starting inference with prompt_type: {prompt_type}")
    print(f"Image size: {image.size}")
    
    # Resize very large images to prevent timeout
    MAX_DIMENSION = 2048
    if max(image.size) > MAX_DIMENSION:
        ratio = MAX_DIMENSION / max(image.size)
        new_size = tuple(int(dim * ratio) for dim in image.size)
        print(f"Resizing image from {image.size} to {new_size}")
        image = image.resize(new_size, Image.Resampling.LANCZOS)
    
    # Clear GPU cache before inference
    torch.cuda.empty_cache()
    
    # Create batch input using official schema
    batch = [
        BatchInputItem(
            image=image,
            prompt_type=prompt_type
        )
    ]
    
    print(f"Running inference (max 4096 tokens)...")
    
    # Run inference using official generate_hf method with limits
    # Reduce max_output_tokens to prevent timeout on long documents
    with torch.no_grad():
        result = generate_hf(batch, model, max_output_tokens=4096)[0]
    
    # Parse markdown output using official parser
    markdown = parse_markdown(result.raw)
    
    # Clear GPU cache after inference
    torch.cuda.empty_cache()
    
    duration = time.time() - start_time
    print(f"✅ Inference completed in {duration:.2f} seconds")
    
    return {
        "text": markdown,
        "raw": result.raw,
        "processing_time": duration
    }

def output_fn(prediction, accept):
    """
    Format output
    """
    return json.dumps(prediction), accept
