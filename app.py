from flask import Flask, request, jsonify, send_file
import os
import logging
from datetime import datetime
from dotenv import load_dotenv

# Import our modules
from src.grok_client import GrokClient
from src.tts_handler import TTSHandler  
from src.sequence_generator import SequenceGenerator
from src.fpp_client import FPPClient
from src.model_manager import ModelManager# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# Initialize clients
grok_client = GrokClient()
tts_handler = TTSHandler()
sequence_generator = SequenceGenerator()
fpp_client = FPPClient()
model_manager = ModelManager()

@app.route("/health", methods=["GET"])
def health_check():
    return jsonify({
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "service": "Grok AI Middleware",
        "version": "1.0.0"
    })

@app.route("/query", methods=["POST"])
def process_query():
    import time
    start_time = time.time()
    
    try:
        data = request.get_json()
        if not data or ("query" not in data and "text" not in data):
            return jsonify({"error": "Query or text parameter required"}), 400
        
        query = data.get("query") or data.get("text")
        logger.info(f"🚀 QUERY START: {query[:50]}... at {datetime.now().strftime('%H:%M:%S.%f')[:-3]}")
        
        # Step 1: Get AI response
        grok_start = time.time()
        logger.info(f"📤 SENT to GROK at {datetime.now().strftime('%H:%M:%S.%f')[:-3]}")
        ai_response = grok_client.get_response(query)
        grok_end = time.time()
        logger.info(f"📥 RECEIVED from GROK at {datetime.now().strftime('%H:%M:%S.%f')[:-3]} ({grok_end - grok_start:.3f}s, {len(ai_response)} chars)")
        
        # Step 2: Generate TTS audio
        polly_start = time.time()
        logger.info(f"🔊 SENT to POLLY at {datetime.now().strftime('%H:%M:%S.%f')[:-3]}")
        audio_file = tts_handler.text_to_speech(ai_response)
        polly_end = time.time()
        logger.info(f"🎵 RECEIVED from POLLY at {datetime.now().strftime('%H:%M:%S.%f')[:-3]} ({polly_end - polly_start:.3f}s)")
        
        # Step 3: Generate working FSEQ sequence with XSQ model loading
        sequence_start = time.time()
        logger.info(f"🎬 SEQUENCE GENERATION START at {datetime.now().strftime('%H:%M:%S.%f')[:-3]}")
        
        # Use the working sequence generation method that preserves all phoneme/face/lighting logic
        # This method loads XSQ files for model configurations but uses proven FSEQ generation
        sequence_files = sequence_generator.create_sequence(ai_response, audio_file)
        fseq_file = sequence_files['fseq']
        xsq_file = sequence_files.get('xsq', 'none')
        
        sequence_end = time.time()
        logger.info(f"✅ SEQUENCE GENERATION END at {datetime.now().strftime('%H:%M:%S.%f')[:-3]} ({sequence_end - sequence_start:.3f}s)")
        
        # Extract file paths
        source_type = 'proven_fseq_generation'
        original_xsq = 'preserved_phoneme_logic'
        
        logger.info(f"🎭 Created: {os.path.basename(fseq_file)} (from {source_type})")
        if original_xsq != 'none':
            logger.info(f"📄 Source XSQ: {os.path.basename(original_xsq)}")
        
        # Step 4: Upload to FPP and create playlist (optional)
        fpp_result = None
        if os.getenv("FPP_HOST"):
            logger.info(f"🎪 FPP UPLOAD START at {datetime.now().strftime('%H:%M:%S.%f')[:-3]}")
            fpp_start = time.time()
            
            # Upload FSEQ and audio to FPP for themed character playback
            fpp_result = fpp_client.upload_fseq_and_audio(fseq_file, audio_file)
            
            if fpp_result and not fpp_result.get("error"):
                # Check if files were verified as uploaded
                files_verified = fpp_result.get("files_verified", {})
                
                # Note: FPP uploads are successful even if immediate verification fails
                # (FPP may take a moment to index), so we skip the verification wait
                # and go straight to playlist creation
                if files_verified.get("audio_found") and files_verified.get("sequence_found"):
                    logger.info("✅ FPP files verified immediately")
                else:
                    # Files are uploaded successfully - FPP will find them when needed
                    logger.info("📁 Files uploaded to FPP (indexing in background...)")
                
                # Create playlist for immediate playback (use FSEQ for FPP)
                fseq_name = os.path.basename(fseq_file)  # Use FSEQ for FPP playback
                audio_name = os.path.basename(audio_file)
                
                logger.info(f"🎭 Creating playlist with: {fseq_name} + {audio_name}")
                playlist_result = fpp_client.create_simple_playlist(fseq_name, audio_name)
                fpp_result["playlist_creation"] = playlist_result
                
                # Auto-start the playlist if creation was successful
                if playlist_result and playlist_result.get("success"):
                    playlist_name = playlist_result["playlist"]
                    logger.info(f"🚀 Starting playlist: {playlist_name}")
                    start_result = fpp_client.start_playlist(playlist_name)
                    fpp_result["playlist_start"] = start_result
                    
                    if start_result and start_result.get("success"):
                        logger.info(f"✅ FPP PLAYLIST STARTED: {playlist_name}")
                    else:
                        logger.error(f"❌ FPP PLAYLIST START FAILED: {start_result}")
                else:
                    logger.error(f"❌ FPP PLAYLIST CREATION FAILED: {playlist_result}")
            else:
                logger.error(f"❌ FPP UPLOAD FAILED: {fpp_result}")
            
            fpp_end = time.time()
            logger.info(f"🎪 FPP COMPLETE at {datetime.now().strftime('%H:%M:%S.%f')[:-3]} ({fpp_end - fpp_start:.3f}s)")
        else:
            logger.info("🎪 FPP not configured - skipping upload and playlist creation")
        
        total_time = time.time() - start_time
        fpp_time = fpp_end - fpp_start if os.getenv("FPP_HOST") else 0
        logger.info(f"🏁 TOTAL COMPLETION at {datetime.now().strftime('%H:%M:%S.%f')[:-3]} ({total_time:.3f}s total)")
        logger.info(f"📊 TIMING BREAKDOWN:")
        logger.info(f"   - Grok AI: {grok_end - grok_start:.3f}s")
        logger.info(f"   - AWS Polly TTS: {polly_end - polly_start:.3f}s")
        logger.info(f"   - FSEQ Generation: {sequence_end - sequence_start:.3f}s")
        logger.info(f"   - FPP Upload/Playlist: {fpp_time:.3f}s")
        logger.info(f"   - Total: {total_time:.3f}s")
        
        return jsonify({
            "query": query,
            "ai_response": ai_response,
            "audio_file": os.path.basename(audio_file),
            "xsq_file": os.path.basename(xsq_file),
            "fseq_file": os.path.basename(fseq_file),
            "fpp_result": fpp_result,
            "timestamp": datetime.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Error processing query: {str(e)}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        return jsonify({"error": str(e)}), 500

@app.route("/files", methods=["GET"])
def list_files():
    """List generated files"""
    try:
        output_dir = "output"
        if not os.path.exists(output_dir):
            return jsonify({"files": []})
        
        files = []
        for file in os.listdir(output_dir):
            file_path = os.path.join(output_dir, file)
            if os.path.isfile(file_path):
                files.append({
                    "name": file,
                    "size": os.path.getsize(file_path),
                    "modified": datetime.fromtimestamp(os.path.getmtime(file_path)).isoformat()
                })
        
        return jsonify({"files": files})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/files/<filename>", methods=["GET"])
def download_file(filename):
    """Download a generated file"""
    try:
        file_path = os.path.join("output", filename)
        if not os.path.exists(file_path):
            return jsonify({"error": "File not found"}), 404
        
        return send_file(file_path, as_attachment=True)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/config", methods=["GET"])
def get_config():
    """Get current configuration"""
    return jsonify({
        "grok_api_configured": bool(os.getenv("GROK_API_KEY")),
        "fpp_host": os.getenv("FPP_HOST", "Not configured"),
        "output_directory": os.path.abspath("output"),
        "tts_language": os.getenv("TTS_LANGUAGE", "en"),
        "tts_slow": os.getenv("TTS_SLOW", "false").lower() == "true"
    })

@app.route("/fpp/status", methods=["GET"])
def fpp_status():
    """Get FPP status"""
    try:
        status = fpp_client.get_status()
        if status:
            return jsonify(status)
        else:
            return jsonify({"error": "FPP not configured"}), 400
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/fpp/playlist/<playlist_name>/start", methods=["POST"])
def start_fpp_playlist(playlist_name):
    """Start a specific playlist on FPP"""
    try:
        result = fpp_client.start_playlist(playlist_name)
        if result:
            return jsonify(result)
        else:
            return jsonify({"error": "FPP not configured"}), 400
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/fpp/upload", methods=["POST"])
def manual_fpp_upload():
    """Manually upload the latest generated files to FPP"""
    try:
        # Find the latest sequence and audio files
        output_dir = "output"
        xsq_files = [f for f in os.listdir(output_dir) if f.endswith('.xsq')]
        fseq_files = [f for f in os.listdir(output_dir) if f.endswith('.fseq')]
        audio_files = [f for f in os.listdir(output_dir) if f.endswith('.mp3')]
        
        if not xsq_files or not fseq_files or not audio_files:
            return jsonify({"error": "Missing sequence or audio files"}), 400
        
        # Get the latest files (by modification time)
        latest_xsq = max(xsq_files, key=lambda f: os.path.getmtime(os.path.join(output_dir, f)))
        latest_fseq = max(fseq_files, key=lambda f: os.path.getmtime(os.path.join(output_dir, f)))
        latest_audio = max(audio_files, key=lambda f: os.path.getmtime(os.path.join(output_dir, f)))
        
        xsq_path = os.path.join(output_dir, latest_xsq)
        fseq_path = os.path.join(output_dir, latest_fseq)
        audio_path = os.path.join(output_dir, latest_audio)
        
        # Upload both sequence types to FPP
        result = fpp_client.upload_sequences(xsq_path, fseq_path, audio_path)
        
        if result:
            return jsonify(result)
        else:
            return jsonify({"error": "FPP not configured"}), 400
            
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/fpp/upload-and-play", methods=["POST"])
def upload_and_play():
    """Upload the latest files to FPP and immediately play them"""
    try:
        # Find the latest sequence and audio files
        output_dir = "output"
        xsq_files = [f for f in os.listdir(output_dir) if f.endswith('.xsq')]
        fseq_files = [f for f in os.listdir(output_dir) if f.endswith('.fseq')]
        audio_files = [f for f in os.listdir(output_dir) if f.endswith('.mp3')]
        
        if not xsq_files or not fseq_files or not audio_files:
            return jsonify({"error": "Missing sequence or audio files"}), 400
        
        # Get the latest files (by modification time)
        latest_xsq = max(xsq_files, key=lambda f: os.path.getmtime(os.path.join(output_dir, f)))
        latest_fseq = max(fseq_files, key=lambda f: os.path.getmtime(os.path.join(output_dir, f)))
        latest_audio = max(audio_files, key=lambda f: os.path.getmtime(os.path.join(output_dir, f)))
        
        xsq_path = os.path.join(output_dir, latest_xsq)
        fseq_path = os.path.join(output_dir, latest_fseq)
        audio_path = os.path.join(output_dir, latest_audio)
        
        logger.info(f"🎪 Manual upload and play: {latest_xsq} + {latest_fseq} + {latest_audio}")
        
        # Upload both sequence types to FPP
        upload_result = fpp_client.upload_sequences(xsq_path, fseq_path, audio_path)
        
        if not upload_result:
            return jsonify({"error": "FPP not configured"}), 400
        
        result = {"upload": upload_result}
        
        # If upload was successful, create and start playlist
        if upload_result and not upload_result.get("error"):
            import time
            time.sleep(2)  # Give FPP time to index files
            
            # Create playlist (use FSEQ for FPP playback)
            playlist_result = fpp_client.create_simple_playlist(latest_fseq, latest_audio)
            result["playlist_creation"] = playlist_result
            
            # Start playlist if creation was successful
            if playlist_result and playlist_result.get("success"):
                playlist_name = playlist_result["playlist"]
                start_result = fpp_client.start_playlist(playlist_name)
                result["playlist_start"] = start_result
                
                if start_result and start_result.get("success"):
                    logger.info(f"🚀 Manual playlist started: {playlist_name}")
                    result["message"] = f"Successfully uploaded and started playlist: {playlist_name}"
                else:
                    logger.warning(f"⚠️ Manual playlist start failed: {start_result}")
                    result["message"] = "Uploaded successfully but failed to start playlist"
            else:
                result["message"] = "Uploaded successfully but failed to create playlist"
        else:
            result["message"] = "Upload failed"
        
        return jsonify(result)
            
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/fpp/play/<path:sequence_name>", methods=["POST"])
def play_specific_sequence(sequence_name):
    """Play a specific sequence that's already uploaded to FPP"""
    try:
        # Find matching audio file (assumes sequence and audio have same base name)
        output_dir = "output"
        
        # Look for the sequence file
        sequence_file = None
        if not sequence_name.endswith('.xsq'):
            sequence_file = f"{sequence_name}.xsq"
        else:
            sequence_file = sequence_name
            
        sequence_path = os.path.join(output_dir, sequence_file)
        if not os.path.exists(sequence_path):
            return jsonify({"error": f"Sequence file not found: {sequence_file}"}), 404
        
        # Look for matching audio file
        audio_file = None
        base_name = sequence_name.replace('.xsq', '').replace('.fseq', '')
        for ext in ['.mp3', '.wav']:
            potential_audio = f"{base_name}{ext}"
            if os.path.exists(os.path.join(output_dir, potential_audio)):
                audio_file = potential_audio
                break
                
        if not audio_file:
            return jsonify({"error": f"No matching audio file found for {sequence_name}"}), 404
        
        logger.info(f"🎪 Playing specific sequence: {sequence_file} + {audio_file}")
        
        # Create and start playlist
        playlist_result = fpp_client.create_simple_playlist(sequence_file, audio_file)
        result = {"playlist_creation": playlist_result}
        
        if playlist_result and playlist_result.get("success"):
            playlist_name = playlist_result["playlist"]
            start_result = fpp_client.start_playlist(playlist_name)
            result["playlist_start"] = start_result
            
            if start_result and start_result.get("success"):
                logger.info(f"🚀 Specific sequence started: {playlist_name}")
                result["message"] = f"Successfully started playlist: {playlist_name}"
            else:
                logger.warning(f"⚠️ Failed to start playlist: {start_result}")
                result["message"] = "Created playlist but failed to start it"
        else:
            result["message"] = "Failed to create playlist"
        
        return jsonify(result)
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/fpp/stop", methods=["POST"])
def stop_fpp_playback():
    """Stop current FPP playback"""
    try:
        result = fpp_client.stop_playback()
        if result:
            return jsonify(result)
        else:
            return jsonify({"error": "FPP not configured"}), 400
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/fpp/playlists", methods=["GET"])
def get_fpp_playlists():
    """Get list of available playlists from FPP"""
    try:
        result = fpp_client.get_playlists()
        if result:
            return jsonify(result)
        else:
            return jsonify({"error": "FPP not configured"}), 400
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/fpp/sequences", methods=["GET"])
def get_fpp_sequences():
    """Get list of available sequences from FPP"""
    try:
        result = fpp_client.get_sequences()
        if result:
            return jsonify(result)
        else:
            return jsonify({"error": "FPP not configured"}), 400
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# Model Management Endpoints

@app.route("/models/available", methods=["GET"])
def list_available_models():
    """List all available .model files"""
    try:
        models = model_manager.list_available_models()
        return jsonify({"models": models})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/models/active", methods=["GET"])
def get_active_models():
    """Get currently active model configuration"""
    try:
        return jsonify({
            "active_models": model_manager.active_models,
            "face": model_manager.get_model_channel_mapping("face"),
            "outline": model_manager.get_model_channel_mapping("outline"),
            "background": model_manager.get_model_channel_mapping("background"),
            "total_channels": model_manager.get_total_channel_count()
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/models/active/<model_type>", methods=["POST"])
def set_active_model(model_type):
    """Set active model for a specific type"""
    try:
        data = request.get_json()
        model_filename = data.get('model_filename')
        
        if model_type not in ["face", "outline", "background", "props"]:
            return jsonify({"error": "Invalid model type"}), 400
        
        success = model_manager.set_active_model(model_type, model_filename)
        
        if success:
            # Reload sequence generator to pick up new model config
            global sequence_generator
            sequence_generator = SequenceGenerator()
            
            return jsonify({
                "success": True,
                "model_type": model_type,
                "model_filename": model_filename,
                "mapping": model_manager.get_model_channel_mapping(model_type)
            })
        else:
            return jsonify({"error": "Failed to set active model"}), 400
            
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/models/upload", methods=["POST"])
def upload_model_file():
    """Upload a new .model file"""
    try:
        if 'file' not in request.files:
            return jsonify({"error": "No file provided"}), 400
        
        file = request.files['file']
        if file.filename == '' or not file.filename.endswith('.model'):
            return jsonify({"error": "Invalid file type. Must be .model file"}), 400
        
        os.makedirs(model_manager.models_dir, exist_ok=True)
        file_path = os.path.join(model_manager.models_dir, file.filename)
        file.save(file_path)
        
        # Try to load the model to validate it
        model_data = model_manager.load_model_file(file.filename)
        
        if model_data:
            return jsonify({
                "success": True,
                "filename": file.filename,
                "model_data": {
                    "name": model_data["name"],
                    "display_as": model_data["display_as"],
                    "channel_count": model_data["channel_count"],
                    "start_channel": model_data["start_channel"]
                }
            })
        else:
            return jsonify({"error": "Failed to parse uploaded model file"}), 400
            
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    port = int(os.getenv("PORT", 5001))
    debug = os.getenv("DEBUG", "false").lower() == "true"
    
    logger.info(f"Starting Grok AI Middleware on port {port}")
    app.run(host="0.0.0.0", port=port, debug=debug)
