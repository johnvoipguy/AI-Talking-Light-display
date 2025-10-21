import os
import yaml
import logging

logger = logging.getLogger(__name__)

class ConfigLoader:
    _config = None
    
    @classmethod
    def load_config(cls):
        """Load configuration from config.yaml file"""
        if cls._config is None:
            config_path = os.path.join(os.path.dirname(__file__), '..', 'config', 'config.yaml')
            try:
                with open(config_path, 'r') as file:
                    cls._config = yaml.safe_load(file)
                logger.info("Configuration loaded from config.yaml")
            except FileNotFoundError:
                logger.warning(f"Config file not found at {config_path}, using environment variables only")
                cls._config = {}
            except Exception as e:
                logger.error(f"Error loading config: {str(e)}")
                cls._config = {}
        return cls._config
    
    @classmethod
    def get_aws_config(cls):
        """Get AWS configuration with fallback to environment variables"""
        config = cls.load_config()
        aws_config = config.get('aws', {})
        
        return {
            'access_key_id': aws_config.get('access_key_id') or os.getenv('AWS_ACCESS_KEY_ID'),
            'secret_access_key': aws_config.get('secret_access_key') or os.getenv('AWS_SECRET_ACCESS_KEY'),
            'region': aws_config.get('region') or os.getenv('AWS_REGION', 'us-east-1')
        }
    
    @classmethod
    def get_tts_config(cls):
        """Get TTS configuration with fallback to environment variables"""
        config = cls.load_config()
        tts_config = config.get('tts', {})
        
        return {
            'voice_id': tts_config.get('voice_id') or os.getenv('POLLY_VOICE_ID', 'Joanna'),
            'engine': tts_config.get('engine') or os.getenv('POLLY_ENGINE', 'neural'),
            'language_code': tts_config.get('language_code') or os.getenv('POLLY_LANGUAGE_CODE', 'en-US')
        }