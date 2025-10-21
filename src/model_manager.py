import os
import json
import logging
import xml.etree.ElementTree as ET
from typing import Dict, List, Tuple, Optional, Any

logger = logging.getLogger(__name__)

class ModelManager:
    """Manages xLights model files and provides channel mapping for sequence generation"""
    
    def __init__(self, models_dir: str = "models", config_dir: str = "config"):
        self.models_dir = models_dir
        self.active_models_dir = os.path.join(models_dir, "active_models")
        self.inactive_models_dir = os.path.join(models_dir, "inactive_models")
        self.config_dir = config_dir
        self.loaded_models = {}
        self.active_models = []
        self._ensure_directories()
        self._load_active_models()
        
    def _ensure_directories(self):
        """Ensure active and inactive model directories exist"""
        os.makedirs(self.active_models_dir, exist_ok=True)
        os.makedirs(self.inactive_models_dir, exist_ok=True)
        
    def _load_active_models(self):
        """Load all models from active_models directory"""
        self.active_models = []
        
        if not os.path.exists(self.active_models_dir):
            logger.warning(f"Active models directory not found: {self.active_models_dir}")
            return
            
        # Load all .xmodel and .model files from active directory
        for filename in os.listdir(self.active_models_dir):
            if filename.endswith(('.model', '.xmodel')):
                model_path = os.path.join(self.active_models_dir, filename)
                model_data = self.load_model_file(model_path)
                
                if model_data:
                    model_data['filename'] = filename
                    model_data['is_active'] = True
                    self.active_models.append(model_data)
                    logger.info(f"Loaded active model: {model_data['name']} ({filename})")
                    
        logger.info(f"Loaded {len(self.active_models)} active models")
        
        # Categorize models by likely function based on name/type
        self._categorize_models()
    
    def _categorize_models(self):
        """Automatically categorize models based on name patterns and properties"""
        self.face_models = []
        self.outline_models = []
        self.background_models = []
        self.prop_models = []
        
        for model in self.active_models:
            name_lower = model['name'].lower()
            display_as = model['display_as'].lower()
            
            # Face detection - look for face keywords, matrices, or models with face info
            has_face_info = model.get('face_info') is not None
            if (('face' in name_lower or 'head' in name_lower or 'mouth' in name_lower or 
                 'reindeer' in name_lower) or
                (display_as == 'matrix' and model.get('width', 0) <= 32 and model.get('height', 0) <= 32) or
                has_face_info):
                self.face_models.append(model)
                logger.info(f"Categorized as FACE: {model['name']}")
                
            # Outline detection - single lines, poly lines, or outline keywords
            elif (display_as in ['single line', 'poly line', 'icicles'] or 
                  'outline' in name_lower or 'border' in name_lower or 'perimeter' in name_lower):
                self.outline_models.append(model)
                logger.info(f"Categorized as OUTLINE: {model['name']}")
                
            # Background detection - large matrices or background keywords  
            elif (display_as == 'matrix' and (model.get('width', 0) > 32 or model.get('height', 0) > 32) or
                  'background' in name_lower or 'fill' in name_lower or 'wash' in name_lower):
                self.background_models.append(model)
                logger.info(f"Categorized as BACKGROUND: {model['name']}")
                
            # Everything else is a prop
            else:
                self.prop_models.append(model)
                logger.info(f"Categorized as PROP: {model['name']}")
    
    def load_model_file(self, model_path_or_filename: str) -> Optional[Dict[str, Any]]:
        """Load an xLights .model/.xmodel file and parse its structure"""
        # Handle both full paths and filenames
        if os.path.exists(model_path_or_filename):
            model_path = model_path_or_filename
            model_filename = os.path.basename(model_path)
        else:
            model_filename = model_path_or_filename
            # Try active models first, then inactive, then root models dir
            for directory in [self.active_models_dir, self.inactive_models_dir, self.models_dir]:
                potential_path = os.path.join(directory, model_filename)
                if os.path.exists(potential_path):
                    model_path = potential_path
                    break
            else:
                logger.error(f"Model file not found: {model_filename}")
                return None
            
        try:
            tree = ET.parse(model_path)
            root = tree.getroot()
            
            model_data = {
                "filename": model_filename,
                "name": root.get("name", model_filename),
                "display_as": root.get("DisplayAs", "Unknown"),
                "string_type": root.get("StringType", "RGB Nodes"),
                "start_channel": int(root.get("StartChannel", "1")),
                "nodes": [],
                "channel_count": 0,
                "width": 0,
                "height": 0,
                "is_matrix": False
            }
            
            # Parse specific model types
            display_as = model_data["display_as"].lower()
            
            if display_as == "matrix":
                model_data["is_matrix"] = True
                model_data["width"] = int(root.get("parm1", "10"))
                model_data["height"] = int(root.get("parm2", "10")) 
                model_data["channel_count"] = model_data["width"] * model_data["height"] * 3  # RGB
                
            elif display_as in ["single line", "poly line", "icicles", "tree", "star", "wreath"]:
                # String/outline models
                node_count = int(root.get("parm1", "50"))
                model_data["channel_count"] = node_count * 3  # RGB
                
                # Generate node positions for string models
                for i in range(node_count):
                    model_data["nodes"].append({
                        "index": i,
                        "start_channel": model_data["start_channel"] + (i * 3),
                        "channels": 3,
                        "x": i,  # Linear layout
                        "y": 0,
                        "z": 0
                    })
                    
            elif display_as == "custom":
                # Custom models - try to parse node layout
                self._parse_custom_model(root, model_data)
            elif root.tag == "custommodel":
                # xmodel files - parse based on face info and other definitions
                self._parse_xmodel_nodes(root, model_data)
                
            else:
                # Generic model - estimate based on parameters
                node_count = int(root.get("parm1", "20"))
                model_data["channel_count"] = node_count * 3
            
            logger.info(f"Loaded model '{model_data['name']}': {model_data['channel_count']} channels, {display_as}")
            
            # Look for face information in xmodel files
            face_info = root.find('faceInfo')
            if face_info is not None:
                model_data['face_info'] = {
                    'name': face_info.get('Name', ''),
                    'type': face_info.get('Type', ''),
                    'mouth_shapes': {}
                }
                
                # Extract mouth shape mappings
                for attr_name, attr_value in face_info.attrib.items():
                    if attr_name.startswith('Mouth-') and not attr_name.endswith('-Color'):
                        shape_name = attr_name[6:]  # Remove 'Mouth-' prefix
                        if attr_value:  # Only add if not empty
                            model_data['face_info']['mouth_shapes'][shape_name] = attr_value
                
                logger.info(f"Found face info with {len(model_data['face_info']['mouth_shapes'])} mouth shapes")
            
            # Cache the loaded model
            self.loaded_models[model_filename] = model_data
            return model_data
            
        except Exception as e:
            logger.error(f"Error parsing model file {model_filename}: {e}")
            return None
    
    def _parse_custom_model(self, root: ET.Element, model_data: Dict[str, Any]):
        """Parse custom model node layouts"""
        try:
            # Look for node data in custom models
            node_count = 0
            
            # Try different possible structures for custom models
            for elem in root.iter():
                if elem.tag.lower() in ['node', 'pixel', 'light']:
                    node_count += 1
                elif 'node' in elem.tag.lower() or 'pixel' in elem.tag.lower():
                    node_count += 1
            
            if node_count == 0:
                # Fallback - use parameters
                node_count = int(root.get("parm1", "30"))
            
            model_data["channel_count"] = node_count * 3
            logger.info(f"Custom model estimated: {node_count} nodes")
            
        except Exception as e:
            logger.warning(f"Error parsing custom model details: {e}")
            model_data["channel_count"] = 90  # Default fallback
    
    def _parse_xmodel_nodes(self, root: ET.Element, model_data: Dict[str, Any]):
        """Parse xmodel files to get actual node count from CustomModelCompressed data"""
        try:
            max_node = 0
            
            # First try to get actual node count from CustomModelCompressed (most reliable)
            compressed_data = root.get('CustomModelCompressed', '')
            if compressed_data:
                nodes_found = set()
                
                # CustomModelCompressed format: node,x,y;node,x,y;node,x,y...
                for entry in compressed_data.split(';'):
                    if entry.strip():
                        parts = entry.split(',')
                        if len(parts) >= 3:
                            try:
                                node_num = int(parts[0])
                                nodes_found.add(node_num)
                            except ValueError:
                                pass
                
                if nodes_found:
                    max_node = max(nodes_found)
                    model_data["channel_count"] = max_node * 3
                    logger.info(f"xmodel from CustomModelCompressed: {max_node} nodes = {max_node * 3} channels")
                    return
            
            # Fallback: Check face/state definitions for node ranges
            for elem in root.iter():
                for attr_name, attr_value in elem.attrib.items():
                    if (attr_name.startswith(('Mouth-', 'Eyes-', 'FaceOutline', 's00')) and 
                        not attr_name.endswith(('-Color', '-Name')) and attr_value):
                        
                        nodes = self._parse_node_ranges_for_count(attr_value)
                        if nodes:
                            max_node = max(max_node, max(nodes))
            
            if max_node > 0:
                model_data["channel_count"] = max_node * 3
                logger.info(f"xmodel from face definitions: {max_node} nodes = {max_node * 3} channels")
            else:
                # Final fallback to parm1
                node_count = int(root.get("parm1", "30"))
                model_data["channel_count"] = node_count * 3
                logger.info(f"xmodel fallback to parm1: {node_count} nodes = {node_count * 3} channels")
                
        except Exception as e:
            logger.warning(f"Error parsing xmodel nodes: {e}")
            # Final fallback
            node_count = int(root.get("parm1", "30"))
            model_data["channel_count"] = node_count * 3
    
    def _parse_node_ranges_for_count(self, range_string: str) -> List[int]:
        """Parse node range string and return list of all node numbers"""
        nodes = []
        try:
            for range_part in range_string.split(','):
                range_part = range_part.strip()
                if '-' in range_part:
                    start, end = map(int, range_part.split('-'))
                    nodes.extend(range(start, end + 1))
                elif range_part.isdigit():
                    nodes.append(int(range_part))
        except:
            pass  # Ignore parsing errors
        return nodes

    
    def get_active_models(self) -> Dict[str, Any]:
        """Get all active models as a dictionary"""
        active_models = {}
        
        # Add face models
        for model in self.face_models:
            if model.get('is_active', False):
                active_models[model['name']] = model
        
        # Add outline models  
        for model in self.outline_models:
            if model.get('is_active', False):
                active_models[model['name']] = model
                
        # Add background models
        for model in self.background_models:
            if model.get('is_active', False):
                active_models[model['name']] = model
                
        # Add prop models
        for model in self.prop_models:
            if model.get('is_active', False):
                active_models[model['name']] = model
        
        return active_models

    def get_models_by_type(self, model_type: str) -> List[Dict[str, Any]]:
        """Get all active models of a specific type"""
        if model_type == "face":
            return self.face_models
        elif model_type == "outline":  
            return self.outline_models
        elif model_type == "background":
            return self.background_models
        elif model_type == "prop" or model_type == "props":
            return self.prop_models
        else:
            return []
    
    def get_primary_model(self, model_type: str) -> Optional[Dict[str, Any]]:
        """Get the primary (first) model of a specific type"""
        models = self.get_models_by_type(model_type)
        return models[0] if models else None
    
    def get_model_channel_mapping(self, model_type: str) -> Dict[str, Any]:
        """Get channel mapping configuration for sequence generation"""
        model = self.get_primary_model(model_type)
        
        if not model:
            return self._get_fallback_mapping(model_type)
        
        return {
            "name": model["name"],
            "start_channel": model["start_channel"],
            "channel_count": model["channel_count"],
            "width": model.get("width", 0),
            "height": model.get("height", 0),
            "is_matrix": model.get("is_matrix", False),
            "display_as": model["display_as"],
            "nodes": model.get("nodes", [])
        }
    
    def get_all_active_models(self) -> List[Dict[str, Any]]:
        """Get all currently active models"""
        return self.active_models
    
    def _get_fallback_mapping(self, model_type: str) -> Dict[str, Any]:
        """Provide fallback channel mappings when no model is loaded"""
        fallbacks = {
            "face": {
                "name": "Generic Face Matrix",
                "start_channel": 1,
                "channel_count": 300,
                "width": 10,
                "height": 10,
                "is_matrix": True,
                "display_as": "Matrix",
                "nodes": []
            },
            "outline": {
                "name": "Generic Outline",
                "start_channel": 301,
                "channel_count": 300,
                "width": 0,
                "height": 0,
                "is_matrix": False,
                "display_as": "Single Line",
                "nodes": []
            },
            "background": {
                "name": "Generic Background",
                "start_channel": 601,
                "channel_count": 273,
                "width": 0,
                "height": 0,
                "is_matrix": False,
                "display_as": "Single Line", 
                "nodes": []
            }
        }
        
        return fallbacks.get(model_type, fallbacks["outline"])
    
    def list_available_models(self) -> Dict[str, List[str]]:
        """List all available model files in active and inactive directories"""
        result = {"active": [], "inactive": []}
        
        # List active models
        if os.path.exists(self.active_models_dir):
            for filename in os.listdir(self.active_models_dir):
                if filename.endswith(('.model', '.xmodel')):
                    result["active"].append(filename)
        
        # List inactive models  
        if os.path.exists(self.inactive_models_dir):
            for filename in os.listdir(self.inactive_models_dir):
                if filename.endswith(('.model', '.xmodel')):
                    result["inactive"].append(filename)
        
        result["active"] = sorted(result["active"])
        result["inactive"] = sorted(result["inactive"])
        
        return result
    
    def activate_model(self, model_filename: str) -> bool:
        """Move a model from inactive to active directory"""
        inactive_path = os.path.join(self.inactive_models_dir, model_filename)
        active_path = os.path.join(self.active_models_dir, model_filename)
        
        if not os.path.exists(inactive_path):
            logger.error(f"Model not found in inactive directory: {model_filename}")
            return False
            
        try:
            os.rename(inactive_path, active_path)
            self._load_active_models()  # Reload active models
            logger.info(f"Activated model: {model_filename}")
            return True
        except Exception as e:
            logger.error(f"Error activating model {model_filename}: {e}")
            return False
    
    def deactivate_model(self, model_filename: str) -> bool:
        """Move a model from active to inactive directory"""
        active_path = os.path.join(self.active_models_dir, model_filename)
        inactive_path = os.path.join(self.inactive_models_dir, model_filename)
        
        if not os.path.exists(active_path):
            logger.error(f"Model not found in active directory: {model_filename}")
            return False
            
        try:
            os.rename(active_path, inactive_path)
            self._load_active_models()  # Reload active models
            logger.info(f"Deactivated model: {model_filename}")
            return True
        except Exception as e:
            logger.error(f"Error deactivating model {model_filename}: {e}")
            return False
    
    def get_total_channel_count(self) -> int:
        """Calculate total channels needed for all active models"""
        max_channel = 0
        
        # Check all active models
        for model in self.active_models:
            model_end = model["start_channel"] + model["channel_count"] - 1
            max_channel = max(max_channel, model_end)
        
        # Return actual requirement (round up to nearest 64 for efficiency)
        if max_channel > 0:
            # Round up to nearest 64 channels for DMX universe alignment
            return ((max_channel + 63) // 64) * 64
        else:
            return 512  # Default if no models loaded