import os
import requests
import logging
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)

class FPPClient:
    def __init__(self):
        self.fpp_host = os.getenv("FPP_HOST")
        self.fpp_port = int(os.getenv("FPP_PORT", "80"))
        self.base_url = f"http://{self.fpp_host}:{self.fpp_port}" if self.fpp_host else None
        
        if not self.fpp_host:
            logger.warning("FPP_HOST not configured - FPP features will be disabled")

    def upload_sequence(self, sequence_file: str, audio_file: str) -> Optional[Dict[str, Any]]:
        """Upload sequence and audio to FPP"""
        if not self.base_url:
            logger.warning("FPP not configured - skipping upload")
            return None
        
        try:
            result = {}
            
            # Upload audio file
            audio_result = self._upload_file(audio_file, "music")
            result["audio_upload"] = audio_result
            
            # Upload sequence file
            sequence_result = self._upload_file(sequence_file, "sequences")
            result["sequence_upload"] = sequence_result
            
            # Give FPP a moment to index the new files
            import time
            time.sleep(2)
            
            # Verify files are accessible in FPP
            audio_filename = os.path.basename(audio_file)
            sequence_filename = os.path.basename(sequence_file)
            
            # Check if files are now available
            files_verified = self._verify_files_uploaded(audio_filename, sequence_filename)
            result["files_verified"] = files_verified
            
            return result
            
        except Exception as e:
            logger.error(f"Error uploading to FPP: {str(e)}")
            return {"error": str(e)}

    def upload_sequences(self, xsq_file: str, fseq_file: str, audio_file: str) -> Optional[Dict[str, Any]]:
        """Upload XSQ, FSEQ, and audio files to FPP"""
        if not self.base_url:
            logger.warning("FPP not configured - skipping upload")
            return None
        
        try:
            result = {}
            
            # Upload audio file
            audio_result = self._upload_file(audio_file, "music")
            result["audio_upload"] = audio_result
            
            # Upload XSQ sequence file (for xLights compatibility)
            xsq_result = self._upload_file(xsq_file, "sequences")
            result["xsq_upload"] = xsq_result
            
            # Upload FSEQ sequence file (for FPP playback)
            fseq_result = self._upload_file(fseq_file, "sequences")
            result["fseq_upload"] = fseq_result
            
            # Give FPP a moment to index the new files
            import time
            time.sleep(2)
            
            # Verify files are accessible in FPP (check FSEQ since that's what FPP plays)
            audio_filename = os.path.basename(audio_file)
            fseq_filename = os.path.basename(fseq_file)
            xsq_filename = os.path.basename(xsq_file)
            
            # Check if files are now available
            files_verified = self._verify_files_uploaded(audio_filename, fseq_filename)
            result["files_verified"] = files_verified
            
            # Also check XSQ availability
            xsq_verified = self._verify_files_uploaded(audio_filename, xsq_filename)
            result["xsq_verified"] = xsq_verified.get("sequence_found", False)
            
            logger.info(f"📄 Uploaded to FPP: {xsq_filename} + {fseq_filename} + {audio_filename}")
            
            return result
            
        except Exception as e:
            logger.error(f"Error uploading sequences to FPP: {str(e)}")
            return {"error": str(e)}

    def upload_fseq_and_audio(self, fseq_file: str, audio_file: str) -> Dict[str, Any]:
        """
        Upload FSEQ sequence and audio file to FPP for themed character interaction
        
        Args:
            fseq_file: Path to FSEQ sequence file
            audio_file: Path to audio file
            
        Returns:
            Dictionary with upload results and verification status
        """
        try:
            from concurrent.futures import ThreadPoolExecutor
            import threading
            
            result = {
                "success": True,
                "method": "fseq_audio_upload",
                "files": []
            }
            
            # Upload both files in parallel for speed
            audio_result = None
            fseq_result = None
            
            def upload_audio():
                nonlocal audio_result
                audio_result = self._upload_file(audio_file, "music")
            
            def upload_fseq():
                nonlocal fseq_result
                fseq_result = self._upload_file(fseq_file, "sequences")
            
            # Start both uploads concurrently
            with ThreadPoolExecutor(max_workers=2) as executor:
                executor.submit(upload_audio)
                executor.submit(upload_fseq)
            
            result["audio_upload"] = audio_result
            result["fseq_upload"] = fseq_result
            
            # Minimal sleep - FPP indexes files very quickly
            import time
            time.sleep(0.1)
            
            # Verify files are accessible in FPP
            audio_filename = os.path.basename(audio_file)
            fseq_filename = os.path.basename(fseq_file)
            
            # Check if files are now available
            files_verified = self._verify_files_uploaded(audio_filename, fseq_filename)
            result["files_verified"] = files_verified
            
            logger.info(f"📄 Uploaded to FPP: {fseq_filename} + {audio_filename}")
            
            return result
            
        except Exception as e:
            logger.error(f"Error uploading FSEQ and audio to FPP: {str(e)}")
            return {"error": str(e)}

    def _verify_files_uploaded(self, audio_filename: str, sequence_filename: str) -> Dict[str, Any]:
        """Verify that uploaded files are available in FPP"""
        try:
            result = {"audio_found": False, "sequence_found": False}
            
            # Check music files
            try:
                response = requests.get(f"{self.base_url}/api/files/music", timeout=10)
                if response.status_code == 200:
                    music_files = response.json()
                    result["audio_found"] = audio_filename in music_files
            except:
                pass
            
            # Check sequence files  
            try:
                response = requests.get(f"{self.base_url}/api/files/sequences", timeout=10)
                if response.status_code == 200:
                    sequence_files = response.json()
                    result["sequence_found"] = sequence_filename in sequence_files
            except:
                pass
                
            return result
        except Exception as e:
            return {"error": str(e)}

    def _upload_file(self, file_path: str, upload_type: str) -> Dict[str, Any]:
        """Upload a file to FPP using the correct API endpoint"""
        try:
            filename = os.path.basename(file_path)
            
            # Use correct FPP API endpoint from documentation
            if upload_type == "music":
                endpoint = f"{self.base_url}/api/file/music/{filename}"
            elif upload_type == "sequences": 
                endpoint = f"{self.base_url}/api/file/sequences/{filename}"
            else:
                raise ValueError(f"Unknown upload type: {upload_type}")
            
            # Upload file using POST with file data as body
            with open(file_path, 'rb') as f:
                response = requests.post(endpoint, data=f, timeout=30)
            
            if response.status_code == 200:
                try:
                    result = response.json()
                    return {
                        "success": True,
                        "filename": filename,
                        "type": upload_type,
                        "response": result
                    }
                except:
                    return {
                        "success": True,
                        "filename": filename,
                        "type": upload_type,
                        "response": f"HTTP 200 - {response.text[:100]}"
                    }
            else:
                return {
                    "success": False,
                    "filename": filename,
                    "type": upload_type,
                    "error": f"HTTP {response.status_code}: {response.text[:200]}"
                }
                
        except Exception as e:
            return {
                "success": False,
                "filename": os.path.basename(file_path),
                "type": upload_type,
                "error": str(e)
            }

    def start_playlist(self, playlist_name: str) -> Optional[Dict[str, Any]]:
        """Start a playlist on FPP"""
        if not self.base_url:
            return None
        
        try:
            logger.info(f"🎬 Attempting to start playlist: {playlist_name}")
            
            # Use the correct FPP API methods that work
            methods_to_try = [
                # Method 1: Command API with JSON args (WORKS!)
                ("command_json", f"{self.base_url}/api/command", "POST", {"command": "Start Playlist", "args": [playlist_name]}),
                # Method 2: Direct GET command (WORKS!)
                ("command_get", f"{self.base_url}/api/command/Start%20Playlist/{playlist_name}", "GET", None),
                # Method 3: Fallback to standard playlist API
                ("playlist_api", f"{self.base_url}/api/playlists/{playlist_name}/start", "POST", None),
            ]
            
            for method_name, endpoint, http_method, data in methods_to_try:
                logger.info(f"🔄 Trying {method_name}: {endpoint}")
                
                try:
                    if http_method == "GET":
                        response = requests.get(endpoint, timeout=10)
                    elif data:
                        response = requests.post(endpoint, json=data, timeout=10)
                    else:
                        response = requests.post(endpoint, timeout=10)
                    
                    logger.info(f"📡 Response: {response.status_code} - {response.text[:100]}")
                    
                    # Check for success indicators
                    response_text = response.text.lower()
                    is_success = (
                        response.status_code == 200 and (
                            "playlist starting" in response_text or
                            "started" in response_text or
                            (response_text == "" and method_name == "playlist_api")  # Empty response often means success
                        )
                    )
                    
                    response_data = {}
                    if response.content:
                        try:
                            response_data = response.json()
                        except:
                            response_data = {"raw_response": response.text}
                    
                    result = {
                        "success": is_success,
                        "playlist": playlist_name,
                        "method": method_name,
                        "endpoint_used": endpoint,
                        "response": response_data,
                        "status_code": response.status_code
                    }
                    
                    if is_success:
                        logger.info(f"✅ Successfully started playlist using {method_name}: {playlist_name}")
                        return result
                    elif response.status_code == 200:
                        logger.warning(f"⚠️ Got 200 but unexpected response: {response.text}")
                    
                except requests.exceptions.RequestException as e:
                    logger.warning(f"⚠️ {method_name} failed: {e}")
                    continue
            
            # If no method worked
            logger.error(f"❌ All methods failed to start playlist: {playlist_name}")
            return {
                "success": False,
                "playlist": playlist_name,
                "error": "All playlist start methods failed"
            }
            
        except Exception as e:
            logger.error(f"Error starting playlist: {str(e)}")
            return {"error": str(e)}

    def stop_playback(self) -> Optional[Dict[str, Any]]:
        """Stop current playback on FPP"""
        if not self.base_url:
            return None
        
        try:
            # Try different FPP API endpoints for stopping playback
            endpoints_to_try = [
                f"{self.base_url}/api/playlists/stop",
                f"{self.base_url}/api/playlist/stop",
                f"{self.base_url}/api/command/Stop",
                f"{self.base_url}/api/commands/Stop"
            ]
            
            for endpoint in endpoints_to_try:
                response = requests.post(endpoint, timeout=10)
                
                # If we get a non-404 response, use this endpoint
                if response.status_code != 404:
                    response_data = {}
                    if response.content:
                        try:
                            response_data = response.json()
                        except:
                            response_data = {"raw_response": response.text}
                    
                    return {
                        "success": response.status_code == 200,
                        "endpoint_used": endpoint,
                        "response": response_data
                    }
            
            # If all endpoints failed with 404
            return {
                "success": False,
                "error": "All stop endpoints returned 404 - FPP API may have changed"
            }
            
        except Exception as e:
            logger.error(f"Error stopping playback: {str(e)}")
            return {"error": str(e)}

    def get_playlists(self) -> Optional[Dict[str, Any]]:
        """Get list of available playlists from FPP"""
        if not self.base_url:
            return None
        
        try:
            endpoint = f"{self.base_url}/api/playlists"
            response = requests.get(endpoint, timeout=10)
            
            if response.status_code == 200:
                return {
                    "success": True,
                    "playlists": response.json()
                }
            else:
                return {
                    "success": False,
                    "error": f"HTTP {response.status_code}: {response.text[:200]}"
                }
                
        except Exception as e:
            logger.error(f"Error getting playlists: {str(e)}")
            return {"error": str(e)}

    def get_sequences(self) -> Optional[Dict[str, Any]]:
        """Get list of available sequences from FPP"""
        if not self.base_url:
            return None
        
        try:
            endpoint = f"{self.base_url}/api/files/sequences"
            response = requests.get(endpoint, timeout=10)
            
            if response.status_code == 200:
                return {
                    "success": True,
                    "sequences": response.json()
                }
            else:
                return {
                    "success": False,
                    "error": f"HTTP {response.status_code}: {response.text[:200]}"
                }
                
        except Exception as e:
            logger.error(f"Error getting sequences: {str(e)}")
            return {"error": str(e)}

    def get_status(self) -> Optional[Dict[str, Any]]:
        """Get FPP status"""
        if not self.base_url:
            return None
        
        try:
            endpoint = f"{self.base_url}/api/fppd/status"
            response = requests.get(endpoint, timeout=10)
            
            if response.status_code == 200:
                return response.json()
            else:
                return {"error": f"HTTP {response.status_code}"}
                
        except Exception as e:
            logger.error(f"Error getting FPP status: {str(e)}")
            return {"error": str(e)}

    def create_simple_playlist(self, sequence_name: str, audio_name: str) -> Optional[Dict[str, Any]]:
        """Create a simple playlist with one sequence using correct FPP format"""
        if not self.base_url:
            return None
        
        try:
            # Remove file extensions for internal references
            sequence_base = sequence_name.replace('.xsq', '').replace('.fseq', '')
            audio_base = audio_name.replace('.mp3', '')
            
            playlist_name = f"AI_Generated_{sequence_base}"
            logger.info(f"🎵 Creating playlist: {playlist_name}")
            logger.info(f"🎼 Sequence: {sequence_name}, Audio: {audio_name}")
            
            # Use correct FPP playlist format (version 3) based on Halloween playlist
            playlist_data = {
                "name": playlist_name,
                "version": 3,
                "repeat": 0,
                "loopCount": 0,
                "empty": False,
                "desc": "Auto-generated playlist from AI response",
                "random": 0,
                "leadIn": [],
                "mainPlaylist": [
                    {
                        "type": "both",
                        "enabled": 1,
                        "playOnce": 0,
                        "sequenceName": sequence_name,  # Keep full filename with extension
                        "mediaName": audio_name,        # Keep full filename with extension
                        "videoOut": "--Default--",
                        "timecode": "Default"
                    }
                ],
                "leadOut": [],
                "playlistInfo": {
                    "total_duration": 0,
                    "total_items": 1
                }
            }
            
            endpoint = f"{self.base_url}/api/playlist/{playlist_data['name']}"
            logger.info(f"📡 POST {endpoint}")
            response = requests.post(endpoint, json=playlist_data, timeout=10)
            logger.info(f"📡 Response: {response.status_code} - {response.text[:200]}")
            
            result = {
                "success": response.status_code == 200,
                "playlist": playlist_data["name"],
                "response": response.json() if response.content else {},
                "playlist_data": playlist_data,  # Include for debugging
                "status_code": response.status_code
            }
            
            if result["success"]:
                logger.info(f"✅ Playlist created successfully: {playlist_name}")
            else:
                logger.error(f"❌ Playlist creation failed: {response.status_code} - {response.text}")
            
            return result
            
        except Exception as e:
            logger.error(f"Error creating playlist: {str(e)}")
            return {"error": str(e)}
