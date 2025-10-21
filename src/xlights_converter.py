"""
xLights to FPP Converter
Converts xLights XSQ sequences to FPP FSEQ format for themed character interactions
"""

import os
import xml.etree.ElementTree as ET
import struct
import logging
from typing import Dict, List, Tuple, Any
from mutagen import File as MutagenFile
from .model_manager import ModelManager

logger = logging.getLogger(__name__)

class XLightsConverter:
    """Convert xLights XSQ sequences to FPP FSEQ binary format"""
    
    def __init__(self):
        self.model_manager = ModelManager()
        self.output_dir = "output"
        os.makedirs(self.output_dir, exist_ok=True)
    
    def convert_sequence_to_fseq(self, xsq_file: str, audio_file: str, output_name: str = None) -> str:
        """
        Convert an xLights XSQ sequence file to FPP FSEQ format
        
        Args:
            xsq_file: Path to xLights .xsq sequence file
            audio_file: Path to matching audio file for timing
            output_name: Optional output filename (auto-generated if None)
            
        Returns:
            Path to generated FSEQ file
        """
        try:
            logger.info(f"🎬 Converting xLights sequence: {xsq_file}")
            
            # Parse the XSQ file
            xsq_data = self._parse_xsq_file(xsq_file)
            
            # Get audio duration
            duration_ms = self._get_audio_duration(audio_file)
            
            # Generate output filename
            if not output_name:
                base_name = os.path.splitext(os.path.basename(xsq_file))[0]
                output_name = f"{base_name}_converted"
            
            logger.info(f"🔧 XLights converter using output_name: {output_name}")
            fseq_path = os.path.join(self.output_dir, f"{output_name}.fseq")
            
            # Convert XSQ timing and effects to FSEQ binary
            self._create_fseq_from_xsq(xsq_data, duration_ms, fseq_path)
            
            logger.info(f"✅ Converted to FSEQ: {fseq_path}")
            return fseq_path
            
        except Exception as e:
            logger.error(f"❌ Error converting XSQ to FSEQ: {e}")
            raise
    
    def _parse_xsq_file(self, xsq_file: str) -> Dict[str, Any]:
        """Parse xLights XSQ sequence file and extract timing/effect data"""
        try:
            tree = ET.parse(xsq_file)
            root = tree.getroot()
            
            # Extract sequence metadata
            sequence_data = {
                'name': root.get('name', 'Unknown'),
                'version': root.get('version', '4'),
                'timing': [],
                'effects': [],
                'models': {},
                'frame_rate': 20,  # Default xLights frame rate
                'duration_ms': 0
            }
            
            # Parse timing tracks (for lip-sync and cues)
            timing_tracks = root.findall('.//TimingTrack')
            for track in timing_tracks:
                track_name = track.get('name', '')
                track_data = {
                    'name': track_name,
                    'type': track.get('type', 'timing'),
                    'intervals': []
                }
                
                # Parse timing intervals
                for interval in track.findall('.//Interval'):
                    start = float(interval.get('start', 0))
                    end = float(interval.get('end', 0))
                    label = interval.get('label', '')
                    
                    track_data['intervals'].append({
                        'start_ms': int(start * 1000),
                        'end_ms': int(end * 1000),
                        'label': label,
                        'duration_ms': int((end - start) * 1000)
                    })
                
                sequence_data['timing'].append(track_data)
            
            # Parse model effects
            models = root.findall('.//Model')
            for model in models:
                model_name = model.get('name', '')
                model_data = {
                    'name': model_name,
                    'type': model.get('ModelType', 'unknown'),
                    'effects': []
                }
                
                # Parse effects for this model
                effects = model.findall('.//Effect')
                for effect in effects:
                    start_time = float(effect.get('startTime', 0))
                    end_time = float(effect.get('endTime', 0))
                    effect_type = effect.get('type', 'unknown')
                    
                    effect_data = {
                        'start_ms': int(start_time * 1000),
                        'end_ms': int(end_time * 1000),
                        'type': effect_type,
                        'settings': {}
                    }
                    
                    # Parse effect settings/parameters
                    for attr in effect.attrib:
                        if attr not in ['startTime', 'endTime', 'type']:
                            effect_data['settings'][attr] = effect.get(attr)
                    
                    model_data['effects'].append(effect_data)
                
                sequence_data['models'][model_name] = model_data
            
            return sequence_data
            
        except Exception as e:
            logger.error(f"Error parsing XSQ file: {e}")
            raise
    
    def _get_audio_duration(self, audio_file: str) -> int:
        """Get audio file duration in milliseconds"""
        try:
            logger.info(f"🔧 Getting audio duration for: {audio_file}")
            audio_info = MutagenFile(audio_file)
            if audio_info and hasattr(audio_info, 'info'):
                duration_ms = int(audio_info.info.length * 1000)
                logger.info(f"🔧 Audio duration: {duration_ms}ms ({duration_ms/1000:.2f}s)")
                return duration_ms
            logger.warning(f"No audio info found, using default 30s")
            return 30000  # Default 30 seconds
        except Exception as e:
            logger.warning(f"Could not get audio duration: {e}, using default 30s")
            return 30000
    
    def _create_fseq_from_xsq(self, xsq_data: Dict[str, Any], duration_ms: int, output_path: str):
        """Create FSEQ binary file from parsed XSQ data"""
        try:
            logger.info(f"🔧 _create_fseq_from_xsq called with duration_ms={duration_ms}")
            
            # Get total channel count from active models
            active_models = self.model_manager.get_active_models()
            total_channels = 0
            
            for model_name, model_info in active_models.items():
                channels = model_info.get('channel_count', 450)
                if channels > total_channels:
                    total_channels = channels
            
            if total_channels == 0:
                total_channels = 450  # Default for reindeer
            
            # Frame timing
            frame_rate = xsq_data.get('frame_rate', 20)
            frame_duration_ms = 1000 // frame_rate
            num_frames = max(1, duration_ms // frame_duration_ms)
            
            logger.info(f"🔧 Calculated: num_frames={num_frames}, total_channels={total_channels}, frame_rate={frame_rate}, frame_duration_ms={frame_duration_ms}")
            
            # Generate frame data using XSQ effects AND phoneme data
            frame_data = []
            for frame_idx in range(num_frames):
                current_time_ms = frame_idx * frame_duration_ms
                
                # Create frame with XSQ effects (this was the original logic)
                frame = bytearray(total_channels)
                
                # Apply XSQ effects to the frame
                for effect in xsq_data.get('effects', []):
                    self._apply_effect_to_frame(frame, effect, current_time_ms, total_channels)
                
                frame_data.append(bytes(frame))
                frame = self._generate_frame_from_xsq(xsq_data, current_time_ms, total_channels)
                frame_data.append(bytes(frame))
            
            # Write FSEQ v2.0 file
            self._write_fseq_file(output_path, frame_data, total_channels, frame_rate)
            
        except Exception as e:
            logger.error(f"Error creating FSEQ from XSQ: {e}")
            raise
    
    def _generate_frame_from_xsq(self, xsq_data: Dict[str, Any], time_ms: int, total_channels: int) -> List[int]:
        """Generate a single frame based on XSQ effects active at given time"""
        # Initialize all channels to 0
        channels = [0] * total_channels
        
        # Apply effects from each model that are active at this time
        for model_name, model_data in xsq_data['models'].items():
            # Find corresponding active model
            active_models = self.model_manager.get_active_models()
            
            if model_name in active_models:
                model_info = active_models[model_name]
                start_channel = model_info.get('start_channel', 1) - 1  # Convert to 0-based
                
                # Apply all effects active at this time
                for effect in model_data['effects']:
                    if effect['start_ms'] <= time_ms <= effect['end_ms']:
                        self._apply_xsq_effect(channels, effect, model_info, start_channel, time_ms)
        
        return channels
    
    def _apply_xsq_effect(self, channels: List[int], effect: Dict, model_info: Dict, start_channel: int, time_ms: int):
        """Apply a specific XSQ effect to the channel data"""
        effect_type = effect['type']
        settings = effect['settings']
        
        # Handle different effect types from xLights
        if effect_type == 'On':
            # Simple "On" effect - light up the model
            self._apply_on_effect(channels, model_info, start_channel, settings)
        
        elif effect_type == 'SingleStrand':
            # Single color effect
            self._apply_color_effect(channels, model_info, start_channel, settings)
        
        elif effect_type == 'Faces':
            # Face/phoneme effect for lip-sync
            self._apply_face_effect(channels, model_info, start_channel, settings, time_ms, effect)
        
        elif effect_type in ['Morph', 'ColorWash', 'Chase']:
            # Dynamic effects
            self._apply_dynamic_effect(channels, model_info, start_channel, settings, effect_type, time_ms, effect)
        
        # Add more effect types as needed
    
    def _apply_on_effect(self, channels: List[int], model_info: Dict, start_channel: int, settings: Dict):
        """Apply simple 'On' effect"""
        channel_count = model_info.get('channel_count', 450)
        
        # Parse color from settings
        color = self._parse_color_setting(settings.get('color', '#FFFFFF'))
        
        # Apply to all channels of the model
        for i in range(0, channel_count, 3):  # RGB groups
            if start_channel + i + 2 < len(channels):
                channels[start_channel + i] = color[0]      # R
                channels[start_channel + i + 1] = color[1]  # G
                channels[start_channel + i + 2] = color[2]  # B
    
    def _apply_color_effect(self, channels: List[int], model_info: Dict, start_channel: int, settings: Dict):
        """Apply color effect"""
        # Similar to On effect but may have additional color logic
        self._apply_on_effect(channels, model_info, start_channel, settings)
    
    def _apply_face_effect(self, channels: List[int], model_info: Dict, start_channel: int, settings: Dict, time_ms: int, effect: Dict):
        """Apply face/lip-sync effect"""
        if model_info.get('type') == 'face':
            # Use face definitions from the model
            face_info = model_info.get('face_info', {})
            
            # Parse phoneme from effect settings or timing
            phoneme = settings.get('Phoneme', 'rest')
            
            # Apply face effect using model's face definitions
            self._apply_model_face_effect(channels, face_info, start_channel, phoneme, settings)
    
    def _apply_model_face_effect(self, channels: List[int], face_info: Dict, start_channel: int, phoneme: str, settings: Dict):
        """Apply face effect using model face definitions"""
        mouth_shapes = face_info.get('mouth_shapes', {})
        
        if phoneme in mouth_shapes:
            nodes_str = mouth_shapes[phoneme]
            nodes = self._parse_node_ranges(nodes_str)
            
            # Parse color and brightness
            color = self._parse_color_setting(settings.get('color', '#FFFFFF'))
            
            for node_num in nodes:
                rgb_start = start_channel + ((node_num - 1) * 3)
                if rgb_start + 2 < len(channels):
                    channels[rgb_start] = color[0]      # R
                    channels[rgb_start + 1] = color[1]  # G
                    channels[rgb_start + 2] = color[2]  # B
    
    def _apply_dynamic_effect(self, channels: List[int], model_info: Dict, start_channel: int, settings: Dict, effect_type: str, time_ms: int, effect: Dict):
        """Apply dynamic effects like morph, chase, etc."""
        # Calculate effect progress (0.0 to 1.0)
        effect_duration = effect['end_ms'] - effect['start_ms']
        if effect_duration > 0:
            progress = (time_ms - effect['start_ms']) / effect_duration
        else:
            progress = 0.0
        
        # Apply effect based on type and progress
        if effect_type == 'Morph':
            # Morphing between colors
            self._apply_morph_effect(channels, model_info, start_channel, settings, progress)
        elif effect_type == 'Chase':
            # Chasing effect
            self._apply_chase_effect(channels, model_info, start_channel, settings, progress)
        # Add more dynamic effects as needed
    
    def _apply_morph_effect(self, channels: List[int], model_info: Dict, start_channel: int, settings: Dict, progress: float):
        """Apply color morphing effect"""
        # Simple morph between two colors based on progress
        color1 = self._parse_color_setting(settings.get('color1', '#FF0000'))
        color2 = self._parse_color_setting(settings.get('color2', '#0000FF'))
        
        # Interpolate colors
        r = int(color1[0] + (color2[0] - color1[0]) * progress)
        g = int(color1[1] + (color2[1] - color1[1]) * progress)
        b = int(color1[2] + (color2[2] - color1[2]) * progress)
        
        channel_count = model_info.get('channel_count', 450)
        for i in range(0, channel_count, 3):
            if start_channel + i + 2 < len(channels):
                channels[start_channel + i] = r
                channels[start_channel + i + 1] = g
                channels[start_channel + i + 2] = b
    
    def _apply_chase_effect(self, channels: List[int], model_info: Dict, start_channel: int, settings: Dict, progress: float):
        """Apply chase effect"""
        # Simple chase effect - light moves across nodes
        channel_count = model_info.get('channel_count', 450)
        node_count = channel_count // 3
        
        color = self._parse_color_setting(settings.get('color', '#FFFFFF'))
        
        # Calculate which node should be lit based on progress
        active_node = int(progress * node_count) % node_count
        
        # Light up the active node
        rgb_start = start_channel + (active_node * 3)
        if rgb_start + 2 < len(channels):
            channels[rgb_start] = color[0]
            channels[rgb_start + 1] = color[1]
            channels[rgb_start + 2] = color[2]
    
    def _parse_color_setting(self, color_str: str) -> Tuple[int, int, int]:
        """Parse color string to RGB tuple"""
        if color_str.startswith('#'):
            # Hex color
            hex_color = color_str[1:]
            if len(hex_color) == 6:
                return (
                    int(hex_color[0:2], 16),
                    int(hex_color[2:4], 16),
                    int(hex_color[4:6], 16)
                )
        
        # Default to white if parsing fails
        return (255, 255, 255)
    
    def _parse_node_ranges(self, range_string: str) -> List[int]:
        """Parse node range string like '14-27,33-34,40-41' into list of node numbers"""
        nodes = []
        
        for range_part in range_string.split(','):
            range_part = range_part.strip()
            if '-' in range_part:
                start, end = map(int, range_part.split('-'))
                nodes.extend(range(start, end + 1))
            elif range_part.isdigit():
                nodes.append(int(range_part))
        
        return nodes
    
    def _write_fseq_file(self, output_path: str, frame_data: List[bytes], total_channels: int, frame_rate: int):
        """Write FSEQ v2.0 binary file"""
        try:
            # Get audio filename for embedding in FSEQ
            audio_filename = os.path.basename(audio_file) if audio_file else ""
            
            with open(output_path, 'wb') as f:
                # Use the WORKING FSEQ header format from create_sequence()
                logger.info(f"🔧 Writing FSEQ header: frames={len(frame_data)}, channels={total_channels}, rate={frame_rate}, audio={audio_filename}")
                
                # FSEQ Header (Version 2.0 - working format)
                f.write(b'FSEQ')                # Magic number (4 bytes) - offset 0-3
                f.write(struct.pack('<H', 32))  # Channel data offset (2 bytes) - offset 4-5
                f.write(struct.pack('<B', 0))   # Version minor (1 byte) - offset 6
                f.write(struct.pack('<B', 2))   # Version major (1 byte) - offset 7
                f.write(struct.pack('<H', 32))  # Header length (2 bytes) - offset 8-9
                f.write(struct.pack('<I', total_channels))  # Channel count (4 bytes)
                f.write(struct.pack('<I', len(frame_data))) # Frame count (4 bytes)
                f.write(struct.pack('<B', frame_rate))      # Step time ms (1 byte)
                f.write(struct.pack('<B', 0))  # Flags = 0 (1 byte) 
                f.write(struct.pack('<B', 0))  # Compression = 0 (1 byte)
                f.write(struct.pack('<B', 0))  # Compression level = 0 (1 byte)
                f.write(struct.pack('<I', 0))  # Sparse ranges = 0 (4 bytes)
                f.write(struct.pack('<Q', 0))  # Unique ID (8 bytes)
                
                # Write frame data
                for frame in frame_data:
                    f.write(frame)
                
                logger.info(f"Written FSEQ: {len(frame_data)} frames, {total_channels} channels")
                
        except Exception as e:
            logger.error(f"Error writing FSEQ file: {e}")
            raise