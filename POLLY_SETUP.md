# Amazon Polly Setup Guide

## Configuration Options

To use Amazon Polly for text-to-speech, you can configure it in two ways:

### Option 1: Configuration File (Recommended)
Edit `/app/config/config.yaml` - the AWS credentials and TTS settings are already configured there.

### Option 2: Environment Variables
Alternatively, you can set up the following environment variables:

### AWS Credentials
```bash
export AWS_ACCESS_KEY_ID="your-aws-access-key-id"
export AWS_SECRET_ACCESS_KEY="your-aws-secret-access-key"
export AWS_REGION="us-east-1"
```

### Polly Configuration (Optional - defaults provided)
```bash
export POLLY_VOICE_ID="Ruth"           # Available voices: Joanna, Matthew, Amy, etc.
export POLLY_ENGINE="generative"             # neural (higher quality) or standard
export POLLY_LANGUAGE_CODE="en-US"       # Language code
```

## AWS Setup

1. **Create AWS Account**: If you don't have one, create an AWS account
2. **Create IAM User**: Create an IAM user with Polly permissions
3. **Attach Policy**: Attach the `AmazonPollyFullAccess` policy or create a custom policy with `polly:SynthesizeSpeech` and `polly:DescribeVoices` permissions
4. **Get Credentials**: Generate access key and secret key for the IAM user

## Installation

Install the required dependencies:
```bash
pip install boto3>=1.26.0
```

## Available Neural Voices

Popular English neural voices:
- **Joanna** (Female, US English)
- **Matthew** (Male, US English) 
- **Amy** (Female, British English)
- **Brian** (Male, British English)
- **Emma** (Female, British English)
- **Olivia** (Female, Australian English)

## Testing

You can test the setup by running:
```python
from src.tts_handler import TTSHandler

tts = TTSHandler()

# Get simple list of voice IDs
voices = tts.get_available_voices()
print(f"Available voices: {voices}")

# Get detailed voice information
voice_details = tts.get_voice_details()
for voice in voice_details:
    print(f"Voice: {voice['Id']} ({voice['Gender']}) - Engines: {voice['SupportedEngines']}")

# Generate speech
audio_file = tts.text_to_speech("Hello, this is a test of Amazon Polly!")
print(f"Audio saved to: {audio_file}")
```

## Cost Considerations

Amazon Polly pricing (as of 2024):
- Neural voices: ~$16 per 1 million characters
- Standard voices: ~$4 per 1 million characters
- First 5 million characters per month are free for 12 months (new accounts)

## Troubleshooting

1. **NoCredentialsError**: Check that AWS credentials are properly set
2. **AccessDenied**: Verify IAM permissions include Polly access
3. **Invalid Voice**: Use `get_available_voices()` to see supported voices for your region
4. **Region Issues**: Some voices may not be available in all regions