import os
import logging
from typing import Dict, List, Tuple, Optional

logger = logging.getLogger(__name__)

class PhonemeMapper:
    """Loads and manages xLights phoneme mappings from configuration files"""
    
    def __init__(self, config_dir: str = "config", dict_dir: str = "src"):
        self.config_dir = config_dir
        self.dict_dir = dict_dir
        self.phoneme_mapping = {}  # CMU -> Preston Blair mapping
        self.cmu_dictionary = {}   # Word -> CMU phonemes mapping
        self.extended_dictionary = {}  # Extended words
        self._load_dictionaries()
        self._load_phoneme_mapping()
        
    def _load_dictionaries(self):
        """Load CMU pronunciation dictionaries"""
        # Load standard dictionary
        standard_dict_path = os.path.join(self.dict_dir, "standard_dictionary")
        if os.path.exists(standard_dict_path):
            self._load_cmu_dict_file(standard_dict_path, self.cmu_dictionary)
            logger.info(f"Loaded {len(self.cmu_dictionary)} words from standard dictionary")
        else:
            logger.warning(f"Standard dictionary not found: {standard_dict_path}")
            
        # Load extended dictionary  
        extended_dict_path = os.path.join(self.dict_dir, "extended_dictionary")
        if os.path.exists(extended_dict_path):
            self._load_cmu_dict_file(extended_dict_path, self.extended_dictionary)
            logger.info(f"Loaded {len(self.extended_dictionary)} words from extended dictionary")
        else:
            logger.warning(f"Extended dictionary not found: {extended_dict_path}")
    
    def _load_cmu_dict_file(self, file_path: str, target_dict: dict):
        """Load a CMU dictionary file into the target dictionary"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    # Skip comments and empty lines
                    if not line or line.startswith(';;;'):
                        continue
                    
                    # Parse dictionary entries: "WORD  PHONEME1 PHONEME2 ..."
                    parts = line.split(None, 1)  # Split on first whitespace only
                    if len(parts) >= 2:
                        word = parts[0].upper()
                        phonemes = parts[1].split()
                        target_dict[word] = phonemes
                        
        except Exception as e:
            logger.error(f"Error loading dictionary {file_path}: {e}")
        
    def _load_phoneme_mapping(self):
        """Load CMU to Preston Blair phoneme mapping from phoneme_mapping file"""
        mapping_file = os.path.join(self.config_dir, "phoneme_mapping")
        
        if not os.path.exists(mapping_file):
            logger.warning(f"Phoneme mapping file not found: {mapping_file}")
            self._use_default_mapping()
            return
        
        try:
            with open(mapping_file, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    # Skip comments and empty lines
                    if not line or line.startswith('#') or line.startswith('.'):
                        continue
                    
                    # Parse mapping lines: "CMU BLAIR # comment"
                    parts = line.split()
                    if len(parts) >= 2:
                        cmu_phoneme = parts[0]
                        blair_phoneme = parts[1]
                        self.phoneme_mapping[cmu_phoneme] = blair_phoneme
                        
            logger.info(f"Loaded {len(self.phoneme_mapping)} phoneme mappings from {mapping_file}")
            
        except Exception as e:
            logger.error(f"Error loading phoneme mapping: {e}")
            self._use_default_mapping()
    
    def _use_default_mapping(self):
        """Fallback to basic phoneme mapping if file not found"""
        logger.info("Using default phoneme mapping")
        self.phoneme_mapping = {
            # Basic vowel mappings
            'AA0': 'AI', 'AA1': 'AI', 'AA2': 'AI',
            'AE0': 'AI', 'AE1': 'AI', 'AE2': 'AI',
            'AH0': 'AI', 'AH1': 'AI', 'AH2': 'AI',
            'AO0': 'O', 'AO1': 'O', 'AO2': 'O',
            'AW0': 'O', 'AW1': 'O', 'AW2': 'O',
            'AY0': 'AI', 'AY1': 'AI', 'AY2': 'AI',
            'EH0': 'E', 'EH1': 'E', 'EH2': 'E',
            'ER0': 'E', 'ER1': 'E', 'ER2': 'E',
            'EY0': 'E', 'EY1': 'E', 'EY2': 'E',
            'IH0': 'AI', 'IH1': 'AI', 'IH2': 'AI',
            'IY0': 'E', 'IY1': 'E', 'IY2': 'E',
            'OW0': 'O', 'OW1': 'O', 'OW2': 'O',
            'OY0': 'WQ', 'OY1': 'WQ', 'OY2': 'WQ',
            'UH0': 'U', 'UH1': 'U', 'UH2': 'U',
            'UW0': 'U', 'UW1': 'U', 'UW2': 'U',
            
            # Consonants
            'B': 'MBP', 'CH': 'etc', 'D': 'etc', 'DH': 'etc',
            'F': 'FV', 'G': 'etc', 'HH': 'etc', 'JH': 'etc',
            'K': 'etc', 'L': 'L', 'M': 'MBP', 'N': 'etc',
            'NG': 'etc', 'P': 'MBP', 'R': 'etc', 'S': 'etc',
            'SH': 'etc', 'T': 'etc', 'TH': 'etc', 'V': 'FV',
            'W': 'WQ', 'Y': 'etc', 'Z': 'etc', 'ZH': 'etc',
        }
    
    def _setup_channel_mapping(self):
        """Setup Preston Blair phoneme to LED channel mapping"""
        self.blair_channels = {
            'AI': [(0, 64, 1.0), (256, 320, 0.8)],     # Wide open mouth (A, I sounds)
            'O': [(64, 128, 1.0), (320, 384, 0.9)],    # Round mouth (O sounds)
            'E': [(128, 192, 1.0), (384, 448, 0.8)],   # Narrow mouth (E sounds)  
            'U': [(192, 256, 1.0), (448, 512, 0.7)],   # Small round mouth (U sounds)
            'etc': [(32, 96, 0.8), (160, 224, 0.6)],   # General consonants
            'L': [(96, 160, 1.0), (224, 288, 0.8)],    # Tongue tip up (L)
            'WQ': [(224, 288, 1.0), (96, 160, 0.7)],   # Lips together then apart (W, Q)
            'MBP': [(288, 352, 1.0), (32, 96, 0.9)],   # Lips together (M, B, P)
            'FV': [(352, 416, 1.0), (160, 224, 0.8)],  # Teeth on lip (F, V)
            'rest': [(0, 512, 0.1)],                   # Mouth at rest
        }
    
    def get_phoneme_channels(self, phoneme: str) -> List[Tuple[int, int, float]]:
        """Convert phoneme to LED channel ranges using xLights mapping"""
        phoneme_clean = phoneme.upper().strip()
        
        # First try direct CMU mapping
        blair_phoneme = self.phoneme_mapping.get(phoneme_clean)
        
        # If not found, try without stress markers (0,1,2)
        if not blair_phoneme and len(phoneme_clean) > 1:
            base_phoneme = ''.join(c for c in phoneme_clean if not c.isdigit())
            blair_phoneme = self.phoneme_mapping.get(base_phoneme)
        
        # Fallback logic
        if not blair_phoneme:
            if phoneme_clean in ['A', 'E', 'I', 'O', 'U']:
                blair_phoneme = 'AI'  # Default vowel
            else:
                blair_phoneme = 'etc'  # Default consonant
        
        # Return channel mapping for the Blair phoneme
        return self.blair_channels.get(blair_phoneme, self.blair_channels['rest'])
    
    def load_cmu_dictionary(self, dict_file: str = None) -> Dict[str, List[str]]:
        """Load CMU pronunciation dictionary (optional - for future expansion)"""
        if not dict_file:
            dict_file = os.path.join(self.config_dir, "standard_dictionary")
        
        if not os.path.exists(dict_file):
            logger.info(f"CMU dictionary not found: {dict_file}")
            return {}
        
        dictionary = {}
        try:
            with open(dict_file, 'r', encoding='utf-8', errors='ignore') as f:
                for line in f:
                    line = line.strip()
                    # Skip comments and empty lines
                    if not line or line.startswith(';;;'):
                        continue
                    
                    # Parse dictionary entries: "WORD  P HH OW N IY M Z"
                    parts = line.split()
                    if len(parts) >= 2:
                        word = parts[0].upper()
                        phonemes = parts[1:]
                        dictionary[word] = phonemes
                        
            logger.info(f"Loaded {len(dictionary)} words from CMU dictionary")
            return dictionary
            
        except Exception as e:
            logger.error(f"Error loading CMU dictionary: {e}")
            return {}
    
    def word_to_phonemes(self, word: str) -> List[str]:
        """Convert word to CMU phonemes using dictionary lookup"""
        word_clean = word.upper().strip('.,!?;:"\'')
        
        # Try dictionary lookup first
        if word_clean in self.cmu_dictionary:
            return self.cmu_dictionary[word_clean]
        
        # Fallback to simple letter-based phoneme generation
        return self._simple_phoneme_generation(word_clean)
    
    def _simple_phoneme_generation(self, word: str) -> List[str]:
        """Simple fallback phoneme generation for unknown words"""
        vowels = 'AEIOU'
        phonemes = []
        
        for i, char in enumerate(word):
            if char in vowels:
                if char == 'A':
                    phonemes.append('AE1')
                elif char == 'E':
                    phonemes.append('EH1')
                elif char == 'I':
                    phonemes.append('IH1')
                elif char == 'O':
                    phonemes.append('OW1')
                elif char == 'U':
                    phonemes.append('UW1')
            else:
                # Simple consonant mapping
                phonemes.append(char)
        
        return phonemes if phonemes else ['rest']
    
    def get_word_phonemes(self, word: str) -> List[str]:
        """Convert a word to CMU phonemes using the loaded dictionaries"""
        word_clean = word.upper().strip().rstrip('.,!?;:')
        
        # Try standard dictionary first
        if word_clean in self.cmu_dictionary:
            return self.cmu_dictionary[word_clean]
            
        # Try extended dictionary
        if word_clean in self.extended_dictionary:
            return self.extended_dictionary[word_clean]
            
        # If not found, try simple letter-to-phoneme mapping
        logger.debug(f"Word '{word}' not found in dictionaries, using fallback")
        return self.word_to_phonemes(word_clean)
    
    def convert_text_to_phonemes(self, text: str) -> List[Tuple[str, str]]:
        """Convert text to list of (word, blair_phoneme) pairs"""
        import re
        
        # Split text into words
        words = re.findall(r'\b\w+\b', text.upper())
        result = []
        
        for word in words:
            # Get CMU phonemes for the word
            cmu_phonemes = self.get_word_phonemes(word)
            
            # Convert each CMU phoneme to Preston Blair phoneme
            for cmu_phoneme in cmu_phonemes:
                blair_phoneme = self.phoneme_mapping.get(cmu_phoneme, 'etc')
                result.append((word, blair_phoneme))
        
        return result