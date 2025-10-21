import os
import json
import struct
import logging
from datetime import datetime
from typing import Dict, List, Any, Optional
from .model_manager import ModelManager
from .xlights_converter import XLightsConverter

logger = logging.getLogger(__name__)

class SequenceGenerator:
    """Generate FSEQ sequences for FPP from phoneme timing data"""
    
    def __init__(self):
        self.output_dir = "output"
        self.model_manager = ModelManager()
        self.xlights_converter = XLightsConverter()
        self.template_xsq = self._find_latest_xsq()  # Find most recent XSQ
        self.xmodel_file = self._find_latest_xmodel()  # Find most recent xmodel
        self.face_elements = {}  # Will store extracted face elements from template
        self._load_face_elements()
        os.makedirs(self.output_dir, exist_ok=True)
    
    def _find_latest_xsq(self) -> str:
        """Find the most recently modified XSQ file in active_models"""
        xsq_dir = "models/active_models"
        if not os.path.exists(xsq_dir):
            logger.warning(f"XSQ directory not found: {xsq_dir}")
            return None
        
        xsq_files = [f for f in os.listdir(xsq_dir) if f.endswith('.xsq')]
        if not xsq_files:
            logger.warning(f"No XSQ files found in {xsq_dir}")
            return None
        
        # Get the MOST RECENTLY MODIFIED XSQ (newest timestamp)
        latest = max(xsq_files, key=lambda f: os.path.getmtime(os.path.join(xsq_dir, f)))
        full_path = os.path.join(xsq_dir, latest)
        mtime = os.path.getmtime(full_path)
        logger.info(f"✅ Found latest XSQ: {latest} (modified: {datetime.fromtimestamp(mtime)})")
        return full_path
    
    def _find_latest_xmodel(self) -> str:
        """Find the most recently modified xmodel file in active_models"""
        xmodel_dir = "models/active_models"
        if not os.path.exists(xmodel_dir):
            logger.warning(f"xmodel directory not found: {xmodel_dir}")
            return None
        
        xmodel_files = [f for f in os.listdir(xmodel_dir) if f.endswith('.xmodel')]
        if not xmodel_files:
            logger.warning(f"No xmodel files found in {xmodel_dir}")
            return None
        
        # Get the MOST RECENTLY MODIFIED xmodel (newest timestamp)
        latest = max(xmodel_files, key=lambda f: os.path.getmtime(os.path.join(xmodel_dir, f)))
        full_path = os.path.join(xmodel_dir, latest)
        mtime = os.path.getmtime(full_path)
        logger.info(f"✅ Found latest xmodel: {latest} (modified: {datetime.fromtimestamp(mtime)})")
        return full_path
    
    def _load_face_elements(self):
        """Load ALL face elements dynamically from model - both definitions and colors"""
        try:
            import xml.etree.ElementTree as ET
            
            # STEP 1: Load base definitions from xmodel (use the latest found)
            xmodel_file = self.xmodel_file
            if not xmodel_file or not os.path.exists(xmodel_file):
                logger.warning(f"xmodel file not found: {xmodel_file}")
                return
            
            tree = ET.parse(xmodel_file)
            root = tree.getroot()
            
            face_definitions = {}
            face_order = []
            face_colors = {}
            
            # Load face element definitions from xmodel
            for face_info in root.findall('.//faceInfo'):
                for attr_name in face_info.attrib:
                    if attr_name.endswith('-Color') or attr_name.endswith('2-Color') or attr_name.endswith('3-Color'):
                        continue
                    if attr_name in ['Name', 'CustomColors', 'Type']:
                        continue
                    
                    nodes_str = face_info.get(attr_name, '')
                    color_attr = attr_name + '-Color'
                    color_hex = face_info.get(color_attr, '#FFFFFF')
                    
                    if nodes_str:
                        tag = attr_name
                        face_definitions[tag] = nodes_str
                        face_order.append(tag)
                        rgb = self._hex_to_rgb(color_hex, 1.0)
                        face_colors[tag] = rgb
            
            # STEP 2: Check XSQ for a state override
            state_name = None
            if os.path.exists(self.template_xsq):
                try:
                    xsq_tree = ET.parse(self.template_xsq)
                    xsq_root = xsq_tree.getroot()
                    
                    # Look for E_CHOICE_Faces_UseState in EffectDB
                    for effect in xsq_root.findall('.//Effect'):
                        effect_str = effect.text or ""
                        if 'E_CHOICE_Faces_UseState=' in effect_str:
                            # Extract state name
                            for param in effect_str.split(','):
                                if 'E_CHOICE_Faces_UseState=' in param:
                                    state_name = param.split('=')[1]
                                    logger.info(f"✅ Found state in XSQ: {state_name}")
                                    break
                            if state_name:
                                break
                except Exception as e:
                    logger.debug(f"Could not extract state from XSQ: {e}")
            
            # STEP 3: If state found, load colors from state in xmodel
            if state_name:
                for state_info in root.findall('.//stateInfo'):
                    if state_info.get('Name') == state_name:
                        logger.info(f"Loading colors from state: {state_name}")
                        # Load s001, s002, s003, etc. from state
                        for i in range(1, 10):  # Try s001 to s009
                            node_key = f's{i:03d}'
                            color_key = f'{node_key}-Color'
                            name_key = f'{node_key}-Name'
                            
                            nodes_str = state_info.get(node_key, '')
                            color_hex = state_info.get(color_key, '')
                            elem_name = state_info.get(name_key, '')
                            
                            if nodes_str and color_hex:
                                # First priority: use elem_name from state if it matches base faceInfo
                                tag = None
                                for face_tag in face_order:
                                    if face_tag.lower().replace('_', '').replace('-', '') == elem_name.lower().replace('_', '').replace('-', ''):
                                        tag = face_tag
                                        break
                                
                                # Second priority: use elem_name as tag
                                if not tag:
                                    tag = elem_name if elem_name else node_key
                                
                                # Update or add the face element
                                face_definitions[tag] = nodes_str
                                if tag not in face_order:
                                    face_order.append(tag)
                                rgb = self._hex_to_rgb(color_hex, 1.0)
                                face_colors[tag] = rgb
                                logger.info(f"  {tag} ({node_key}): {nodes_str} → {color_hex} = {rgb}")
                        break
            
            # STEP 4: Assign all colors to face elements
            for face_tag in face_order:
                if face_tag in face_definitions:
                    color = face_colors.get(face_tag, (255, 255, 255))
                    self.face_elements[face_tag] = {
                        'nodes': face_definitions[face_tag],
                        'color': color
                    }
                    if 'Mouth' not in face_tag:
                        logger.info(f"Final: {face_tag} {face_definitions[face_tag]} → {color}")
            
            logger.info(f"✅ Loaded {len(self.face_elements)} face elements (xmodel + state colors)")
            logger.info(f"Face elements: {[(k, v['color']) for k, v in sorted(self.face_elements.items()) if 'Mouth' not in k]}")
            
        except Exception as e:
            logger.error(f"Error loading face elements from xmodel: {e}")
            import traceback
            logger.error(traceback.format_exc())
    
    def _apply_hardware_corrections(self):
        """Apply corrections for actual hardware node mappings"""
        # This method handles cases where the xmodel node ranges don't match
        # the physical model configuration. Update as needed based on your hardware.
        logger.debug("Hardware corrections applied (if any)")
    
    def _hex_to_rgb(self, hex_color: str, intensity: float = 1.0) -> tuple:
        """Convert hex color to RGB tuple with intensity"""
        hex_color = hex_color.lstrip('#')
        try:
            r = int(hex_color[0:2], 16)
            g = int(hex_color[2:4], 16)
            b = int(hex_color[4:6], 16)
            
            # Apply intensity
            r = int(r * intensity)
            g = int(g * intensity)
            b = int(b * intensity)
            
            return (r, g, b)
        except:
            return (200, 200, 200)  # Default gray
        
    def create_sequence(self, text: str, audio_file: str, filename: str = None) -> Dict[str, str]:
        """Create FSEQ sequence file from text and audio"""
        try:
            # ALWAYS reload the latest model and XSQ when creating a new sequence
            self.template_xsq = self._find_latest_xsq()
            self.xmodel_file = self._find_latest_xmodel()
            self.face_elements = {}  # Clear and reload
            self._load_face_elements()
            
            # Extract timestamp from audio file to match naming
            if not filename and audio_file:
                audio_basename = os.path.basename(audio_file)
                if audio_basename.startswith('tts_') and '_' in audio_basename:
                    timestamp_part = audio_basename.replace('tts_', '').replace('.mp3', '')
                    filename = f"sequence_{timestamp_part}"
                else:
                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                    filename = f"sequence_{timestamp}"
            elif not filename:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = f"sequence_{timestamp}"
            
            # Load actual timing data if available
            word_timings = self._load_or_generate_timings(text, audio_file)
            
            # Create FSEQ file (FPP native format)
            fseq_filename = filename + '.fseq'
            fseq_filepath = os.path.join(self.output_dir, fseq_filename)
            
            # Generate FSEQ binary file
            self._create_fseq_file(fseq_filepath, word_timings, audio_file)
            
            logger.info(f"FSEQ sequence saved to: {fseq_filepath}")
            
            # Also create XSQ file (needed for xLights import)
            xsq_filename = filename + '.xsq'
            xsq_filepath = os.path.join(self.output_dir, xsq_filename)
            sequence_data = self._create_xlights_sequence(word_timings, audio_file)
            with open(xsq_filepath, 'w', encoding='utf-8') as f:
                f.write(sequence_data)
            logger.info(f"xLights sequence saved to: {xsq_filepath}")
            
            # Return both files for upload
            return {'fseq': fseq_filepath, 'xsq': xsq_filepath}
            
        except Exception as e:
            logger.error(f"Error creating sequence: {str(e)}")
            raise

    def _create_fseq_file(self, fseq_filepath: str, word_timings: List[Dict], audio_file: str):
        """Create FSEQ v2.0 binary file with phoneme-based frame data"""
        try:
            frame_rate = 20
            frame_duration_ms = 1000 // frame_rate
            
            # Get model channel configuration from ModelManager
            active_models = self.model_manager.get_active_models()
            if not active_models:
                logger.error("No active models found!")
                raise ValueError("No active models configured")
            
            model_name = list(active_models.keys())[0]
            model_info = active_models[model_name]
            fpp_start_channel = model_info.get('start_channel', 1)
            channel_count = model_info.get('channel_count', 450)
            
            # FSEQ must include all channels up to the last used channel
            # If model uses channels 1-450, FSEQ has 450 channels
            # If model uses channels 860-1309, FSEQ has 1309 channels
            total_channels = fpp_start_channel + channel_count - 1
            model_start_offset = fpp_start_channel - 1  # Convert to 0-based index
            
            logger.info(f"📋 Using model: {model_name}")
            logger.info(f"   Channel range: {fpp_start_channel}-{total_channels} (total: {total_channels} channels, offset: {model_start_offset})")
            
            # Calculate number of frames based on timing data
            if word_timings and len(word_timings) > 0:
                last_timing = word_timings[-1]
                duration_ms = last_timing.get('end_time', last_timing.get('end_ms', 0))
            else:
                duration_ms = 5000
            
            num_frames = max(1, (duration_ms + frame_duration_ms - 1) // frame_duration_ms)
            
            # Generate frame data
            frame_data = []
            for frame_idx in range(num_frames):
                frame = self._generate_phoneme_frame(frame_idx, frame_duration_ms, word_timings, total_channels, model_start_offset)
                frame_data.append(bytes(frame))
            
            # Write FSEQ v2.0 file with proper header
            with open(fseq_filepath, 'wb') as f:
                # FSEQ v2.0 header format (32 bytes):
                # Bytes 0-3:     "FSEQ" magic
                # Byte 4:        Data block offset (32 = no sparse ranges)
                # Byte 5:        Compression type (0 = uncompressed)
                # Byte 6:        Version minor
                # Byte 7:        Version major (2 for v2.0)
                # Bytes 8-9:     Header length (0x20 = 32)
                # Bytes 10-13:   Channel count (little-endian)
                # Bytes 14-17:   Frame count (little-endian)
                # Bytes 18-19:   Step time in ms (little-endian)
                # Bytes 20-31:   Reserved
                
                header = bytearray(32)
                header[0:4] = b'FSEQ'                                    # Magic
                header[4] = 32                                           # Data block offset
                header[5] = 0                                            # Compression type (0 = uncompressed)
                header[6] = 0                                            # Version minor
                header[7] = 2                                            # Version major (v2.0)
                struct.pack_into('<H', header, 8, 32)                   # Header length (0x20)
                struct.pack_into('<I', header, 10, total_channels)      # Channel count (450)
                struct.pack_into('<I', header, 14, num_frames)          # Frame count
                struct.pack_into('<H', header, 18, frame_duration_ms)   # Step time ms (50)
                
                f.write(bytes(header))
                
                for frame in frame_data:
                    f.write(frame)
                
            logger.info(f"Created FSEQ v2.0 file: {fseq_filepath} ({len(frame_data)} frames, {total_channels} channels)")
            
            
        except Exception as e:
            logger.error(f"Error creating FSEQ file: {str(e)}")
            raise

    def _generate_phoneme_frame(self, frame_idx: int, frame_duration_ms: int, word_timings: List[Dict], num_channels: int, model_start_offset: int = 0) -> bytearray:
        """Generate animation frame with ALL face elements + phoneme-based mouth animation"""
        current_time_ms = frame_idx * frame_duration_ms
        frame = bytearray(num_channels)
        
        # Get active model and its face info
        active_models = self.model_manager.get_active_models()
        if not active_models:
            return frame
        
        # Use the first active model
        model_name = list(active_models.keys())[0]
        model_info = active_models[model_name]
        face_info = model_info.get('face_info', {})
        
        if not face_info:
            logger.warning(f"No face_info found for model {model_name}")
            return frame
        
        # FIRST: Light up all the STATIC face elements (eyes, nose, outline, antlers, etc)
        # These are extracted from the template XSQ and should be on in every frame
        self._apply_all_static_face_elements(frame, model_start_offset)
        
        # SECOND: Apply mouth shape based on current viseme (Polly timing marks)
        current_viseme = self._get_phoneme_at_time(current_time_ms, word_timings)
        mouth_shapes = face_info.get('mouth_shapes', {})
        mouth_shape_name = self._map_viseme_to_mouth_shape(current_viseme)
        
        if mouth_shape_name in mouth_shapes and current_viseme != 'sil':
            nodes_str = mouth_shapes[mouth_shape_name]
            nodes = self._parse_node_ranges(nodes_str)
            
            # Get the mouth color from the loaded face elements
            if mouth_shape_name in self.face_elements:
                color = self.face_elements[mouth_shape_name]['color']
            else:
                # Default to white if not found
                color = (255, 255, 255)
            
            for node_num in nodes:
                rgb_start = (node_num - 1) * 3 + model_start_offset
                if rgb_start + 2 < num_channels:
                    frame[rgb_start] = color[0]      # R
                    frame[rgb_start + 1] = color[1]  # G
                    frame[rgb_start + 2] = color[2]  # B
        
        return frame
    
    def _apply_all_static_face_elements(self, frame: bytearray, model_start_offset: int = 0):
        """Light up all static face elements from template with colors from XSQ"""
        if not self.face_elements:
            logger.warning("⚠️  face_elements is EMPTY!")
            return
        
        logger.info(f"Applying {len(self.face_elements)} face elements to frame (offset: {model_start_offset})")
        for face_element_name, element_data in self.face_elements.items():
            # Skip mouth elements - those are handled separately by phonemes
            if 'Mouth' in face_element_name:
                continue
            
            nodes_str = element_data['nodes']
            color = element_data['color']
            
            logger.info(f"  Applying {face_element_name}: nodes={nodes_str}, color={color}")
            nodes = self._parse_node_ranges(nodes_str)
            logger.info(f"    Parsed {len(nodes)} nodes: {nodes[:10]}... (total: {len(nodes)})")
            for idx, node_num in enumerate(nodes):
                # CRITICAL: node_num is the ACTUAL node ID (1-150)
                # FSEQ channels are sequential: offset to (offset+449) for 150 nodes * 3 RGB
                # Node N → channels (N-1)*3 + offset, (N-1)*3+1 + offset, (N-1)*3+2 + offset
                rgb_start = (node_num - 1) * 3 + model_start_offset
                if rgb_start + 2 < len(frame):
                    frame[rgb_start] = color[0]      # R
                    frame[rgb_start + 1] = color[1]  # G
                    frame[rgb_start + 2] = color[2]  # B
                    if idx < 3:
                        logger.debug(f"      Node {node_num} → channels {rgb_start}-{rgb_start+2} = {color}")
                else:
                    logger.warning(f"      Node {node_num} out of bounds: rgb_start={rgb_start} frame_len={len(frame)}")
    
    def _parse_node_ranges(self, node_string: str) -> List[int]:
        """Parse node range string like '1-5,10,15-20' into list of node numbers"""
        nodes = []
        if not node_string:
            return nodes
        
        parts = node_string.split(',')
        for part in parts:
            part = part.strip()
            if '-' in part:
                # Range like '1-5'
                start, end = part.split('-')
                try:
                    nodes.extend(range(int(start), int(end) + 1))
                except ValueError:
                    continue
            else:
                # Single node
                try:
                    nodes.append(int(part))
                except ValueError:
                    continue
        
        return sorted(list(set(nodes)))  # Remove duplicates and sort

    def _get_phoneme_at_time(self, time_ms: int, word_timings: List[Dict]) -> str:
        """Get the active phoneme/viseme at a specific time"""
        for timing_data in word_timings:
            start = timing_data.get('start_time') or timing_data.get('start_ms', 0)
            end = timing_data.get('end_time') or timing_data.get('end_ms', 0)
            
            if start <= time_ms < end:
                # Return viseme if available (from Polly), otherwise phoneme
                return timing_data.get('viseme') or timing_data.get('phoneme') or timing_data.get('viseme', 'sil')
        
        return "sil"
    
    def _map_viseme_to_mouth_shape(self, viseme: str) -> str:
        """Map Polly AWS viseme to xLights mouth shape"""
        # AWS Polly visemes map to mouth shapes
        viseme_to_shape = {
            # Vowels
            'a': 'AI',      # open front vowel
            'i': 'E',       # close front vowel  
            'u': 'U',       # close back vowel
            'o': 'O',       # close back rounded vowel
            # Consonants - fricatives/sibilants
            's': 'etc',     # sibilant
            'S': 'etc',     # sibilant (voiceless)
            'z': 'etc',     # sibilant (voiced)
            'f': 'FV',      # labiodental
            'v': 'FV',      # labiodental voiced
            't': 'etc',     # alveolar stop
            'd': 'etc',     # alveolar voiced stop
            # Consonants - bilabial
            'p': 'MBP',     # bilabial stop
            'b': 'MBP',     # bilabial voiced stop
            'm': 'MBP',     # bilabial nasal
            # Other
            'r': 'L',       # approximant (treated as lateral for mouth)
            'l': 'L',       # lateral approximant
            'w': 'WQ',      # labial approximant
            'sil': 'rest',  # silence
        }
        
        return viseme_to_shape.get(viseme.lower(), 'rest')

    def _load_or_generate_timings(self, text: str, audio_file: str = None) -> List[Dict[str, Any]]:
        """Load timing data from timings.json (Polly viseme marks) or generate if not available"""
        try:
            timings_file = os.path.join(self.output_dir, "timings.json")
            if os.path.exists(timings_file):
                with open(timings_file, 'r') as f:
                    timings_data = json.load(f)
                    
                # Check if it's a list of timing marks (from Polly) - this is what we need!
                if isinstance(timings_data, list) and len(timings_data) > 0:
                    first_item = timings_data[0]
                    if 'viseme' in first_item and 'start_ms' in first_item:
                        logger.info(f"✅ Loaded {len(timings_data)} Polly viseme timing marks")
                        return self._normalize_timings(timings_data)
                
                # Fallback: check for old dict-based format
                current_words = text.lower().split()[:3]
                if isinstance(timings_data, dict):
                    audio_basename = os.path.basename(audio_file) if audio_file else None
                    if audio_basename and audio_basename in timings_data:
                        cached_timings = timings_data[audio_basename]
                        if isinstance(cached_timings, list):
                            if self._timings_match_text(cached_timings, current_words):
                                logger.info(f"Loaded matching timings from timings.json")
                                return self._normalize_timings(cached_timings)
                elif isinstance(timings_data, list) and timings_data:
                    if self._timings_match_text(timings_data, current_words):
                        logger.info(f"Loaded {len(timings_data)} timing marks from timings.json")
                        return self._normalize_timings(timings_data)
            
            logger.info("Generating estimated word timings")
            return self._generate_word_timings(text)
            
        except Exception as e:
            logger.warning(f"Error loading timings: {str(e)}")
            return self._generate_word_timings(text)

    def _timings_match_text(self, timings: List[Dict], current_words: List[str]) -> bool:
        """Check if cached timings match the current text"""
        if not timings or not current_words:
            return False
        
        timing_words = [t.get('word', '').lower() for t in timings if 'word' in t]
        return any(w in timing_words for w in current_words[:2])

    def _normalize_timings(self, timings: List[Dict]) -> List[Dict]:
        """Normalize timing format from various sources (Polly visemes, word timings, etc)"""
        normalized = []
        for timing in timings:
            if isinstance(timing, dict):
                start_ms = timing.get("start_time") or timing.get("start_ms", 0)
                end_ms = timing.get("end_time") or timing.get("end_ms", 0)
                
                # Handle Polly viseme format (viseme + start_ms/end_ms)
                if "viseme" in timing:
                    normalized.append({
                        "viseme": timing.get("viseme", "sil"),
                        "start_ms": start_ms,
                        "end_ms": end_ms
                    })
                # Handle word format
                elif "word" in timing:
                    normalized.append({
                        "word": timing.get("word", ""),
                        "start_time": start_ms,
                        "end_time": end_ms,
                        "phoneme": "sil"
                    })
                # Handle phoneme format
                elif "phoneme" in timing or "viseme" in timing:
                    normalized.append({
                        "phoneme": timing.get("phoneme") or timing.get("viseme", "sil"),
                        "start_time": start_ms,
                        "end_time": end_ms
                    })
        
        return normalized

    def _generate_word_timings(self, text: str) -> List[Dict[str, Any]]:
        """Generate estimated word timings based on text"""
        words = text.split()
        total_duration = 5000
        word_duration = total_duration // max(1, len(words))
        
        timings = []
        current_time = 0
        
        for word in words:
            timings.append({
                "word": word,
                "start_time": current_time,
                "end_time": current_time + word_duration,
                "phoneme": "sil"
            })
            current_time += word_duration
        
        return timings

    def _create_xlights_sequence(self, word_timings: List[Dict], audio_file: str) -> str:
        """Create xLights XML sequence string"""
        xml_parts = [
            '<?xml version="1.0"?>',
            '<sequence>',
            f'  <song>{os.path.basename(audio_file) if audio_file else ""}</song>',
            '  <effects></effects>',
            '</sequence>'
        ]
        return '\n'.join(xml_parts)
