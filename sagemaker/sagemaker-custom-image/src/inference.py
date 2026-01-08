import os
import json
import torch
import math
from typing import Tuple, List
from PIL import Image
import requests
from io import BytesIO
import base64
from qwen_vl_utils import process_vision_info

# --- PROMPTS (from chandra/prompts.py) ---
ALLOWED_TAGS = [
    "math", "br", "i", "b", "u", "del", "sup", "sub", "table", "tr", "td", "p",
    "th", "div", "pre", "h1", "h2", "h3", "h4", "h5", "ul", "ol", "li",
    "input", "a", "span", "img", "hr", "tbody", "small", "caption",
    "strong", "thead", "big", "code",
]
ALLOWED_ATTRIBUTES = [
    "class", "colspan", "rowspan", "display", "checked", "type", "border",
    "value", "style", "href", "alt", "align",
]

PROMPT_ENDING = f"""
Only use these tags {ALLOWED_TAGS}, and these attributes {ALLOWED_ATTRIBUTES}.

Guidelines:
* Inline math: Surround math with <math>...</math> tags. Math expressions should be rendered in KaTeX-compatible LaTeX. Use display for block math.
* Tables: Use colspan and rowspan attributes to match table structure.
* Formatting: Maintain consistent formatting with the image, including spacing, indentation, subscripts/superscripts, and special characters.
* Images: Include a description of any images in the alt attribute of an <img> tag. Do not fill out the src property.
* Forms: Mark checkboxes and radio buttons properly.
* Text: join lines together properly into paragraphs using <p>...</p> tags.  Use <br> tags for line breaks within paragraphs, but only when absolutely necessary to maintain meaning.
* Use the simplest possible HTML structure that accurately represents the content of the block.
* Make sure the text is accurate and easy for a human to read and interpret.  Reading order should be correct and natural.
""".strip()

OCR_LAYOUT_PROMPT = f"""
OCR this image to HTML, arranged as layout blocks.  Each layout block should be a div with the data-bbox attribute representing the bounding box of the block in [x0, y0, x1, y1] format.  Bboxes are normalized 0-{{bbox_scale}}. The data-label attribute is the label for the block.

Use the following labels:
- Caption
- Footnote
- Equation-Block
- List-Group
- Page-Header
- Page-Footer
- Image
- Section-Header
- Table
- Text
- Complex-Block
- Code-Block
- Form
- Table-Of-Contents
- Figure

{PROMPT_ENDING}
""".strip()

OCR_PROMPT = f"""
OCR this image to HTML.

{PROMPT_ENDING}
""".strip()

PROMPT_MAPPING = {
    "ocr_layout": OCR_LAYOUT_PROMPT,
    "ocr": OCR_PROMPT,
}

# --- UTILS (from chandra/model/util.py) ---
def scale_to_fit(
    img: Image.Image,
    max_size: Tuple[int, int] = (3072, 2048),
    min_size: Tuple[int, int] = (28, 28),
):
    resample_method = Image.Resampling.LANCZOS

    width, height = img.size

    # Check for empty or invalid image
    if width == 0 or height == 0:
        return img

    max_width, max_height = max_size
    min_width, min_height = min_size

    current_pixels = width * height
    max_pixels = max_width * max_height
    min_pixels = min_width * min_height

    if current_pixels > max_pixels:
        scale_factor = (max_pixels / current_pixels) ** 0.5
        new_width = math.floor(width * scale_factor)
        new_height = math.floor(height * scale_factor)
    elif current_pixels < min_pixels:
        scale_factor = (min_pixels / current_pixels) ** 0.5
        new_width = math.ceil(width * scale_factor)
        new_height = math.ceil(height * scale_factor)
    else:
        return img

    return img.resize((new_width, new_height), resample=resample_method)

# --- INFERENCE ---
model = None
processor = None

def model_fn(model_dir):
    """
    Load the model for inference
    """
    global model, processor
    print("Loading model...")
    
    # Use the model name directly from HuggingFace
    model_name = "datalab-to/chandra"
    
    try:
        # Try importing Qwen3VL first as seen in source, fallback to Qwen2VL
        try:
            from transformers import Qwen3VLForConditionalGeneration, Qwen3VLProcessor
            ModelClass = Qwen3VLForConditionalGeneration
            ProcessorClass = Qwen3VLProcessor
            print("Using Qwen3VL classes.")
        except ImportError:
            from transformers import Qwen2VLForConditionalGeneration, AutoProcessor
            ModelClass = Qwen2VLForConditionalGeneration
            ProcessorClass = AutoProcessor
            print("Using Qwen2VL classes (Qwen3VL not found).")

        model = ModelClass.from_pretrained(
            model_name,
            torch_dtype=torch.bfloat16,
            device_map="auto",
            trust_remote_code=True
        )
        
        processor = ProcessorClass.from_pretrained(
            model_name, 
            trust_remote_code=True
        )
        
        print("Model loaded successfully")
        return model, processor
    except Exception as e:
        print(f"Error loading model: {str(e)}")
        raise e

def predict_fn(input_data, model_and_processor):
    """
    Generate predictions
    """
    model, processor = model_and_processor
    
    if not isinstance(input_data, dict):
        raise ValueError("Input must be a dictionary")
        
    image_input = input_data.get("image")
    prompt_type = input_data.get("prompt_type", "ocr") # default to 'ocr'
    bbox_scale = input_data.get("bbox_scale", 1000)
    max_output_tokens = input_data.get("max_output_tokens", 4096)
    
    # Custom prompt override
    custom_prompt = input_data.get("prompt")

    if not image_input:
        raise ValueError("No image provided in input")
        
    # Load and scale image
    image = None
    if image_input.startswith("http"):
        response = requests.get(image_input, stream=True)
        image = Image.open(response.raw)
    else:
        try:
            image_bytes = base64.b64decode(image_input)
            image = Image.open(BytesIO(image_bytes))
        except:
             raise ValueError("Invalid image format. Provide URL or Base64 string.")
    
    # Scale image using official logic
    image = scale_to_fit(image)

    # Determine prompt
    if custom_prompt:
        prompt_text = custom_prompt
    else:
        prompt_template = PROMPT_MAPPING.get(prompt_type, OCR_PROMPT)
        prompt_text = prompt_template.replace("{bbox_scale}", str(bbox_scale))

    # Construct message
    messages = [
        {
            "role": "user",
            "content": [
                {
                    "type": "image",
                    "image": image,
                },
                {"type": "text", "text": prompt_text},
            ],
        }
    ]
    
    # Prepare inputs
    text = processor.apply_chat_template(
        messages, tokenize=False, add_generation_prompt=True
    )
    image_inputs, video_inputs = process_vision_info(messages)
    inputs = processor(
        text=[text],
        images=image_inputs,
        videos=video_inputs,
        padding=True,
        return_tensors="pt",
    )
    inputs = inputs.to(model.device)

    # Inference
    generated_ids = model.generate(**inputs, max_new_tokens=max_output_tokens)
    generated_ids_trimmed = [
        out_ids[len(in_ids) :] for in_ids, out_ids in zip(inputs.input_ids, generated_ids)
    ]
    output_text = processor.batch_decode(
        generated_ids_trimmed, skip_special_tokens=True, clean_up_tokenization_spaces=False
    )
    
    return output_text[0]
