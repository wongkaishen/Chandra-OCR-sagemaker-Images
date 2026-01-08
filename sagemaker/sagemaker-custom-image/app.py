import flask
from flask import request, jsonify
import json
import logging
from src import inference

app = flask.Flask(__name__)
model_and_processor = None

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@app.before_first_request
def load_model():
    """
    Load the model on startup
    """
    global model_and_processor
    # We load the model from the Hugging Face hub (cache)
    # The container usually has this volume mounted or downloads it
    try:
        model_and_processor = inference.model_fn("/opt/ml/model")
        logger.info("Model loaded successfully.")
    except Exception as e:
        logger.error(f"Failed to load model: {str(e)}")
        # In this case, we might want to crash the container so it restarts
        # but for now we just log it.

@app.route('/ping', methods=['GET'])
def ping():
    """
    Health check
    """
    global model_and_processor
    # If the model is loaded, we are healthy
    status = 200 if model_and_processor else 500
    return flask.Response(response='\n', status=status, mimetype='application/json')

@app.route('/invocations', methods=['POST'])
def transformation():
    """
    Inference endpoint
    """
    global model_and_processor
    
    if not model_and_processor:
        # Try loading if not loaded (fallback)
        try:
            load_model()
        except:
             return flask.Response(response='Model not loaded', status=500)

    if flask.request.content_type == 'application/json':
        data = flask.request.get_json()
    else:
        return flask.Response(response='This predictor only supports application/json data', status=415, mimetype='text/plain')

    # Do inference
    try:
        result = inference.predict_fn(data, model_and_processor)
        return flask.Response(response=json.dumps({"result": result}), status=200, mimetype='application/json')
    except Exception as e:
        logger.error(f"Inference processing failed: {str(e)}")
        return flask.Response(response=f"Error processing request: {str(e)}", status=500, mimetype='text/plain')

if __name__ == '__main__':
    # This is for local testing only
    app.run(host='0.0.0.0', port=8080)
