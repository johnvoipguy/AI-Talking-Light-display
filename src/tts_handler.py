import os
import json
import logging
import boto3
from datetime import datetime
from botocore.exceptions import NoCredentialsError, BotoCoreError
from mutagen.mp3 import MP3
from .config_loader import ConfigLoader

logger = logging.getLogger(__name__)

class TTSHandler:
    def __init__(self):
        # Load configuration from config.yaml with environment variable fallbacks
        aws_config = ConfigLoader.get_aws_config()
        tts_config = ConfigLoader.get_tts_config()
        
        self.voice_id = tts_config['voice_id']
        self.engine = tts_config['engine']
        self.language_code = tts_config['language_code']
        self.output_dir = "output"
        
        # Ensure output directory exists
        os.makedirs(self.output_dir, exist_ok=True)
        
        # Initialize Polly client
        try:
            self.polly = boto3.client(
                'polly',
                region_name=aws_config['region'],
                aws_access_key_id=aws_config['access_key_id'],
                aws_secret_access_key=aws_config['secret_access_key']
            )
            logger.info(f"Amazon Polly client initialized successfully - Voice: {self.voice_id}, Engine: {self.engine}")
        except (NoCredentialsError, Exception) as e:
            logger.error(f"Failed to initialize Polly client: {str(e)}")
            raise

    def text_to_speech(self, text: str, filename: str = None) -> str:
        """Convert text to speech and save as MP3 with word timing data"""
        import time
        
        try:
            if not filename:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = f"tts_{timestamp}.mp3"
            
            if not filename.endswith('.mp3'):
                filename += '.mp3'
            
            filepath = os.path.join(self.output_dir, filename)
            
            polly_synthesis_start = time.time()
            
            logger.info(f"Generating TTS with Polly for {len(text)} characters")
            
            # Generate speech marks for timing data (only supported by neural/standard engines)
            timing_data = []
            if self.engine in ['neural', 'standard']:
                try:
                    timing_response = self.polly.synthesize_speech(
                        Text=text,
                        OutputFormat='json',
                        VoiceId=self.voice_id,
                        Engine=self.engine,
                        LanguageCode=self.language_code,
                        SpeechMarkTypes=['viseme', 'word']  # Get viseme AND word timing (viseme covers full audio)
                    )
                    timing_data = self._process_speech_marks(timing_response['AudioStream'].read())
                    logger.info(f"Retrieved {len(timing_data)} timing marks from Polly")
                except Exception as e:
                    logger.warning(f"Could not get speech marks from Polly: {e}")
                    timing_data = []
            else:
                logger.info(f"Speech marks not supported for engine '{self.engine}', will use estimated timing")
            
            # Convert to speech with Polly
            logger.info(f"🔊 POLLY SYNTHESIS START at {datetime.now().strftime('%H:%M:%S.%f')[:-3]}")
            audio_response = self.polly.synthesize_speech(
                Text=text,
                OutputFormat='mp3',
                VoiceId=self.voice_id,
                Engine=self.engine,
                LanguageCode=self.language_code
            )
            polly_synthesis_end = time.time()
            logger.info(f"🔊 POLLY SYNTHESIS END at {datetime.now().strftime('%H:%M:%S.%f')[:-3]} ({polly_synthesis_end - polly_synthesis_start:.3f}s)")
            
            # Save audio stream to file with detailed timing
            download_start = time.time()
            logger.info(f"⬇️ POLLY DOWNLOAD START at {datetime.now().strftime('%H:%M:%S.%f')[:-3]}")
            
            # Read in chunks to detect when bytes actually start flowing
            audio_stream = audio_response['AudioStream']
            audio_content = b''
            first_byte_time = None
            chunk_size = 8192  # 8KB chunks
            
            while True:
                try:
                    chunk = audio_stream.read(chunk_size)
                    if not chunk:
                        break
                    
                    if first_byte_time is None:
                        first_byte_time = time.time()
                        logger.info(f"🟢 FIRST BYTES RECEIVED at {datetime.now().strftime('%H:%M:%S.%f')[:-3]} ({first_byte_time - download_start:.3f}s delay)")
                    
                    audio_content += chunk
                    
                except Exception as e:
                    logger.error(f"Error reading audio stream chunk: {e}")
                    break
            
            download_end = time.time()
            logger.info(f"⬇️ POLLY DOWNLOAD END at {datetime.now().strftime('%H:%M:%S.%f')[:-3]} ({download_end - download_start:.3f}s total, {len(audio_content)} bytes)")
            
            if first_byte_time:
                actual_transfer_time = download_end - first_byte_time
                bytes_per_sec = len(audio_content) / actual_transfer_time if actual_transfer_time > 0 else 0
                logger.info(f"📊 TRANSFER STATS: {actual_transfer_time:.3f}s transfer, {bytes_per_sec/1024:.1f} KB/s, {first_byte_time - download_start:.3f}s wait time")
            
            file_write_start = time.time()
            with open(filepath, 'wb') as file:
                file.write(audio_content)
            file_write_end = time.time()
            logger.info(f"💾 FILE WRITE at {datetime.now().strftime('%H:%M:%S.%f')[:-3]} ({file_write_end - file_write_start:.3f}s)")
            
            # Get actual MP3 duration using mutagen (most accurate)
            mutagen_start = time.time()
            logger.info(f"🎧 MUTAGEN START at {datetime.now().strftime('%H:%M:%S.%f')[:-3]}")
            actual_duration = None
            try:
                audio_file = MP3(filepath)
                actual_duration = audio_file.info.length
                mutagen_end = time.time()
                logger.info(f"🎧 MUTAGEN END at {datetime.now().strftime('%H:%M:%S.%f')[:-3]} ({mutagen_end - mutagen_start:.3f}s) - Duration: {actual_duration:.2f}s")
            except Exception as e:
                mutagen_end = time.time()
                logger.warning(f"🎧 MUTAGEN FAILED at {datetime.now().strftime('%H:%M:%S.%f')[:-3]} ({mutagen_end - mutagen_start:.3f}s): {e}")
                
                # Fallback 1: Use speech marks if available and complete
                if timing_data and len(timing_data) > 0:
                    speech_mark_duration = timing_data[-1]['end_ms'] / 1000.0
                    words_in_text = len(text.split())
                    words_in_timing = len(timing_data)
                    coverage_ratio = words_in_timing / words_in_text if words_in_text > 0 else 0
                    
                    if coverage_ratio > 0.8:
                        actual_duration = speech_mark_duration
                        logger.info(f"Fallback: Using speech marks duration: {actual_duration:.2f}s")
                    else:
                        logger.warning(f"Speech marks incomplete ({coverage_ratio:.1%}), using estimation")
                
                # Fallback 2: Character-based estimation
                if not actual_duration:
                    if 'RequestCharacters' in audio_response:
                        char_count = audio_response['RequestCharacters'] 
                        actual_duration = char_count / 16.4
                    else:
                        actual_duration = len(text) / 16.4
                    logger.info(f"Fallback: Estimated duration: {actual_duration:.2f}s")
            
            actual_duration = max(1.0, actual_duration)
            
            # Save timing data if we got it from Polly, otherwise create estimated timing with correct duration
            if timing_data:
                # Adjust last viseme timing to match actual audio duration
                actual_duration_ms = int(actual_duration * 1000)
                if len(timing_data) > 0:
                    last_timing = timing_data[-1] 
                    if last_timing.get('end_ms', 0) > actual_duration_ms:
                        logger.info(f"Adjusting last viseme from {last_timing['end_ms']}ms to {actual_duration_ms}ms to match audio duration")
                        last_timing['end_ms'] = actual_duration_ms
                
                timings_filepath = os.path.join(self.output_dir, "timings.json")
                with open(timings_filepath, 'w') as f:
                    json.dump(timing_data, f, indent=2)
                logger.info(f"Polly timing data saved to: {timings_filepath}")
            else:
                # Create estimated timing data with correct duration
                words = text.split()
                if words:
                    estimated_timing = self._create_estimated_timing(words, actual_duration)
                    timings_filepath = os.path.join(self.output_dir, "timings.json")
                    with open(timings_filepath, 'w') as f:
                        json.dump(estimated_timing, f, indent=2)
                    logger.info(f"Created estimated timing data with duration {actual_duration:.2f}s: {timings_filepath}")
                else:
                    logger.warning("No words found in text for timing generation")
            
            logger.info(f"TTS audio saved to: {filepath}")
            logger.info(f"Timing data saved to: {timings_filepath}")
            return filepath
            
        except (BotoCoreError, Exception) as e:
            logger.error(f"Error generating TTS with Polly: {str(e)}")
            raise

    def get_audio_duration(self, filepath: str) -> float:
        """Get audio duration in seconds (corrected estimation for Polly MP3s)"""
        try:
            with open(filepath, 'rb') as f:
                file_size = len(f.read())
            
            # Corrected estimation for Polly generative engine MP3s
            # Based on your feedback: 228KB file = 38 seconds
            # That's approximately 6KB per second, much lower than previous estimate
            estimated_duration = max(1.0, file_size / 6000)  # ~6KB per second for generative voice
            
            logger.info(f"Estimated audio duration: {estimated_duration:.2f} seconds (file size: {file_size} bytes)")
            return estimated_duration
            
        except Exception as e:
            logger.error(f"Error getting audio duration: {str(e)}")
            return 5.0  # Default fallback
    
    def _process_speech_marks(self, speech_marks_data: bytes) -> list:
        """Process AWS Polly speech marks into timing data
        
        Returns viseme marks if available (for lip-sync), otherwise word marks.
        This ensures we have timing data that covers the entire audio duration.
        """
        try:
            # Speech marks come as newline-separated JSON objects
            speech_marks_str = speech_marks_data.decode('utf-8')
            logger.info(f"Raw speech marks data: {speech_marks_str[:500]}...")
            lines = speech_marks_str.strip().split('\n')
            
            word_data = []
            viseme_data = []
            
            for line in lines:
                if line.strip():
                    mark = json.loads(line)
                    mark_type = mark.get('type')
                    
                    if mark_type == 'word':
                        word_data.append({
                            "word": mark['value'],
                            "start_ms": mark['start'],
                            "end_ms": mark['end']
                        })
                    elif mark_type == 'viseme':
                        viseme_data.append({
                            "viseme": mark['value'],
                            "start_ms": mark['time'],
                            "end_ms": mark.get('end', mark['time'] + 150)  # Longer 150ms duration to reduce gaps
                        })
            
            # Prefer viseme data for full coverage, but fall back to words
            if viseme_data:
                # Extend viseme durations to fill gaps between visemes
                for i, viseme in enumerate(viseme_data):
                    if i < len(viseme_data) - 1:
                        # Extend this viseme until the next one starts
                        next_start = viseme_data[i + 1]['start_ms']
                        viseme['end_ms'] = next_start
                    # Last viseme keeps its current end_ms for now
                
                logger.info(f"Processed {len(viseme_data)} viseme timing marks from Polly (covers full audio)")
                return viseme_data
            else:
                logger.info(f"Processed {len(word_data)} word timing marks from Polly")
                return word_data
            
        except Exception as e:
            logger.error(f"Error processing speech marks: {str(e)}")
            return []
    
    def _create_estimated_timing(self, words: list, total_duration: float) -> list:
        """Create estimated word timing that matches actual audio duration"""
        if not words or total_duration <= 0:
            return []
        
        timing_data = []
        
        # Calculate timing based on word length and characteristics
        word_weights = []
        for word in words:
            # Base weight on word length
            weight = len(word) + 1
            
            # Adjust for punctuation (longer pauses)
            if word.endswith(('.', '!', '?')):
                weight *= 1.5
            elif word.endswith((',', ';', ':')):
                weight *= 1.2
            
            word_weights.append(weight)
        
        total_weight = sum(word_weights)
        
        # Distribute timing proportionally
        current_time_ms = 0
        padding_ms = 100  # Small padding at start and end
        usable_duration_ms = (total_duration * 1000) - (2 * padding_ms)
        
        for i, word in enumerate(words):
            # Calculate duration based on weight proportion
            duration_ms = (word_weights[i] / total_weight) * usable_duration_ms
            duration_ms = max(100, duration_ms)  # Minimum 100ms per word
            
            start_ms = current_time_ms + padding_ms
            end_ms = start_ms + duration_ms
            
            timing_data.append({
                "word": word,
                "start_ms": int(start_ms),
                "end_ms": int(end_ms)
            })
            
            current_time_ms += duration_ms
        
        logger.info(f"Generated {len(timing_data)} word timings for {total_duration:.2f}s audio")
        return timing_data
    
    def get_available_voices(self) -> list:
        """Get list of available Polly voice IDs"""
        try:
            response = self.polly.describe_voices(
                Engine=self.engine,
                LanguageCode=self.language_code
            )
            voices = [voice['Id'] for voice in response['Voices']]
            logger.info(f"Available voices: {voices}")
            return voices
        except Exception as e:
            logger.error(f"Error getting available voices: {str(e)}")
            return []
    
    def get_voice_details(self) -> list:
        """Get detailed information about available Polly voices"""
        try:
            response = self.polly.describe_voices(
                Engine=self.engine,
                LanguageCode=self.language_code
            )
            voices = []
            for voice in response['Voices']:
                voices.append({
                    'Id': voice['Id'],
                    'Name': voice.get('Name', voice['Id']),
                    'Gender': voice.get('Gender', 'Unknown'),
                    'LanguageCode': voice.get('LanguageCode', 'Unknown'),
                    'SupportedEngines': voice.get('SupportedEngines', [])
                })
            logger.info(f"Found {len(voices)} voices for engine '{self.engine}'")
            return voices
        except Exception as e:
            logger.error(f"Error getting voice details: {str(e)}")
            return []
