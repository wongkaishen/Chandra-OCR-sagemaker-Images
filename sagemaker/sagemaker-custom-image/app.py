"""
Flask app for SageMaker custom inference endpoint
Handles /ping and /invocations endpoints
FIXED: Loads model ONCE at startup, not on every ping request
"""
from flask import Flask, request, jsonify
import sys
import os

# Add src to path
sys.path.insert(0, '/opt/ml/code/src')

from inference import model_fn, input_fn, predict_fn, output_fn

app = Flask(__name__)

# Load model ONCE at module import time (not on every request!)
print("="*70)
print("INITIALIZING MODEL AT STARTUP")
print("This should only happen ONCE during container startup")
print("="*70)
model_dir = os.environ.get('MODEL_PATH', '/opt/ml/model')
MODEL = model_fn(model_dir)
print("="*70)
print("✅ MODEL READY - Server starting...")
print("="*70)

@app.route('/ping', methods=['GET'])
def ping():
    """
    Health check endpoint required by SageMaker
    Returns 200 immediately since model is already loaded at startup
    """
    return '', 200

@app.route('/invocations', methods=['POST'])
def invocations():
    """
    Inference endpoint required by SageMaker
    Uses pre-loaded MODEL (no loading delay)
    """
    try:
        # Get content type
        content_type = request.content_type or 'application/json'
        
        # Process input
        data = input_fn(request.data, content_type)
        
        # Make prediction using pre-loaded MODEL
        prediction = predict_fn(data, MODEL)
        
        # Format output
        result, accept = output_fn(prediction, request.accept_mimetypes.best or 'application/json')
        
        return result, 200, {'Content-Type': accept}
        
    except Exception as e:
        print(f"Error in /invocations: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080)
