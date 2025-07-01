from flask import Flask, request, send_file
import io
import wave
import numpy as np
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# --- Integrate Kokoro Library ---
# Import the KPipeline class from the kokoro library
try:
    from kokoro import KPipeline
    logger.info("Successfully imported KPipeline.")
except ImportError:
    logger.error("Failed to import KPipeline. Make sure the 'kokoro' library is installed and accessible in your environment.")
    KPipeline = None # Set to None if import fails


# Initialize KPipeline once when the application starts
kokoro_pipeline = None # Initialize to None
try:
    if KPipeline:
        # Initialize KPipeline - adjust lang_code as needed.
        # The language code usually corresponds to the voice used,
        # or you might need to determine it based on the input 'language' parameter.
        # For simplicity, let's start by initializing with a default language,
        # but you might need to adjust or re-initialize based on request language.
        # A more robust approach might be to handle multiple pipelines or
        # ensure the voice matches the initialized pipeline's language.
        default_lang_code = "a" # Example: American English
        kokoro_pipeline = KPipeline(lang_code=default_lang_code)
        logger.info(f"Kokoro KPipeline initialized successfully with lang_code='{default_lang_code}'.")
    else:
         logger.error("KPipeline class not available, cannot initialize pipeline.")
except Exception as e:
    logger.error(f"Error initializing Kokoro KPipeline: {e}", exc_info=True)
    kokoro_pipeline = None # Ensure pipeline is None if initialization fails


app = Flask(__name__)

@app.route('/synthesize', methods=['POST'])
def synthesize_audio():
    """
    API endpoint to synthesize audio from text.
    Expects a JSON payload with a 'text' field.
    Optional fields: 'voice', 'language', 'speed'.
    """
    if not request.json or not 'text' in request.json:
        logger.warning("Bad request: 'text' field missing.")
        return "Error: Please provide 'text' in the request body.", 400

    text = request.json['text']
    # Get optional parameters, provide defaults
    # Note: Language might be inferred from the voice, or passed explicitly.
    # The KPipeline is initialized with a specific lang_code.
    # You might need logic here to ensure the requested voice/language
    # is compatible with the initialized pipeline, or handle multiple pipelines.
    voice = request.json.get('voice', 'af_heart')
    language = request.json.get('language', voice[0] if voice else 'a') # Attempt to infer language from voice, default to 'a'
    speed = request.json.get('speed', 1.0)

    logger.info(f"Received synthesis request: text='{text[:50]}...', voice='{voice}', language='{language}', speed={speed}")

    # --- Call Kokoro Synthesis ---
    # Use the initialized kokoro_pipeline to synthesize audio.
    try:
        if kokoro_pipeline is None:
            logger.error("Kokoro KPipeline not initialized.")
            return "Error: TTS pipeline not initialized.", 500

        # Call the pipeline with the provided parameters.
        # The pipeline likely returns a generator or an iterable of results.
        # We need to collect the audio data from the results.
        audio_segments = []
        # The split_pattern='\n+' is from __main__.py, adjust if needed
        logger.info(f"Calling kokoro pipeline with text length {len(text)}...")
        # Assuming pipeline returns results similar to __main__.py's generate_audio
        # The pipeline() call itself might be the generator.
        # You might need to confirm the exact method signature and return type.
        # Example based on the generate_audio structure in __main__.py:
        # for result in kokoro_pipeline(text, voice=voice, speed=speed, split_pattern='\n+'):
        for result in kokoro_pipeline(text, voice=voice, speed=speed, split_pattern='\n+'): # Corrected method call
            logger.debug(f"Received result: phonemes='{result.phonemes}'")
            if result.audio is not None:
                 # Assuming result.audio is a torch.Tensor or numpy array
                audio_segments.append(result.audio.numpy() if hasattr(result.audio, 'numpy') else result.audio) # Handle both torch and numpy

        if not audio_segments:
             logger.error("Kokoro pipeline did not return any audio segments.")
             return "Error: Failed to generate audio.", 500

        # Concatenate audio segments if multiple were returned
        audio_data = np.concatenate(audio_segments)

        # Convert audio data to 16-bit integers as in __main__.py
        audio_data = (audio_data * 32767).astype(np.int16)

        # Create a WAV file in memory
        byte_io = io.BytesIO()
        with wave.open(byte_io, 'wb') as wav_file:
            wav_file.setnchannels(1)  # Mono audio
            wav_file.setsampwidth(2)  # 2 bytes per sample (16-bit audio)
            wav_file.setframerate(24000) # Sample rate (based on __main__.py, verify kokoro's output rate)
            wav_file.writeframes(audio_data.tobytes())

        byte_io.seek(0)

        logger.info("Audio synthesized successfully.")
        return send_file(byte_io, mimetype='audio/wav')

    except Exception as e:
        logger.error(f"Error during synthesis: {e}", exc_info=True)
        # More specific error handling could be added based on potential kokoro exceptions
        return f"An error occurred during synthesis: {e}", 500

@app.route('/')
def index():
    """Basic route to confirm the API is running."""
    # Check if pipeline initialized to provide status
    status = "initialized" if kokoro_pipeline else "not initialized"
    return f"Kokoro TTS API - Pipeline status: {status}"

if __name__ == '__main__':
    # When running locally for development
    # In a production environment (like Render), use a production WSGI server (gunicorn)
    # Set host to '0.0.0.0' to be accessible externally in environments like Render
    logger.info("Starting Flask application.")
    # Remove debug=True for production
    # app.run(debug=True, host='0.0.0.0', port=5000)
    # For production using gunicorn, you would typically run 'gunicorn api:app'
    # The __main__ block is mainly for local testing.
    # If running locally for testing, keep debug=True.
    app.run(debug=True, host='0.0.0.0', port=5000) # Keep for local testing setup example