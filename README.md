# 🎄 AI-Driven xLights Integration - Talking Reindeer

Transform text prompts into dynamic, animated Christmas light displays! This project combines **AI text generation**, **text-to-speech synthesis**, **xLights sequencing**, and **real-time light control** to create an intelligent lighting system that responds to natural language.

## ✨ Features

- **🤖 AI-Powered Response**: Uses Grok AI to generate creative responses to user queries
- **🔊 Natural Speech Synthesis**: Amazon Polly text-to-speech with multiple voice options
- **🎨 Dynamic Light Animation**: Generates xLights sequences (FSEQ binary format) synchronized with speech
- **🎭 Face Element Mapping**: Intelligent mapping of 150-node reindeer model with state-based color system
- **📡 FPP Hardware Integration**: Direct control of Falcon Player (FPP) hardware at 192.168.50.200
- **⚡ Real-Time Processing**: Complete query-to-display pipeline in seconds
- **🎯 State-Based Colors**: Loads xmodel and XSQ files dynamically for accurate color rendering

## 🏗️ Architecture

```
User Query
    ↓
Grok AI (text generation)
    ↓
Amazon Polly (TTS + audio file)
    ↓
FSEQ Generator (binary sequence with face animations)
    ├─ Loads latest xmodel (150-node reindeer)
    ├─ Loads latest XSQ (sequence template with state)
    ├─ Extracts face elements (Eyes, Nose, Outline, Antlers)
    ├─ Applies state-based colors
    └─ Generates timed FSEQ binary with mouth animations
    ↓
FPP Hardware Upload & Playback
```

## 🚀 Quick Start

### Prerequisites

- Python 3.8+
- AWS Account with Polly access (or credentials in `.env`)
- xLights models in `models/active_models/`
- FPP hardware at `192.168.50.200` (optional, for playback)

### 1. Clone & Setup

```bash
# Clone the repository
git clone https://github.com/johnvoipguy/AI-Talking-Light-display.git
cd AI-Talking-Light-display

# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Configure Environment Variables

Create a `.env` file in the project root with your AWS credentials:

```bash
# Copy the example
cp POLLY_SETUP.md .env.example

# Edit with your actual credentials
nano .env
```

Add these variables:

```bash
# AWS Polly (Required for TTS)
AWS_ACCESS_KEY_ID="your-aws-access-key-id"
AWS_SECRET_ACCESS_KEY="your-aws-secret-access-key"
AWS_REGION="us-east-1"

# Grok AI (Required for text generation)
GROK_API_KEY="your-grok-api-key"

# FPP Hardware (Optional, for playback)
FPP_HOST="192.168.50.200"
FPP_PORT="80"
```

### 3. Configure Application Settings

Edit `config/config.yaml` to customize:

```yaml
# Text-to-Speech Options
tts:
  voice_id: "Ruth"                    # Polly voice (Ruth, Joanna, Matthew, Amy)
  engine: "neural"                    # "neural" (better) or "standard"
  language_code: "en-US"

# AI Model
grok:
  model: "grok-3"
  temperature: 0.7                    # 0.0 = deterministic, 1.0 = creative

# FPP Hardware
fpp:
  enabled: true
  auto_upload: false                  # Auto-send sequences to FPP
  auto_start: false                   # Auto-play on FPP after upload
```

### 4. Prepare xLights Models

Place your xLights model files in:

```
models/active_models/
  ├── NorRednoseReindeer.xmodel       # Model definition (150 nodes)
  └── norfreindeer_seq_antlers.xsq    # Sequence template
```

**What these files contain:**
- **xmodel**: Physical node definitions + face elements (Eyes, Nose, Outline, Mouth) + state definitions (colors, node ranges)
- **xsq**: Sequence template specifying which state to use and frame timing

### 5. Run the Application

```bash
# Start the Flask server
python3 app.py

# Server runs on http://localhost:5001
```

## 📡 API Usage

### Health Check

```bash
curl http://localhost:5001/health
```

Response:
```json
{
  "status": "healthy",
  "service": "Grok AI Middleware",
  "version": "1.0.0",
  "timestamp": "2025-10-21T15:30:45.123456"
}
```

### Generate Sequence from Query

```bash
curl -X POST http://localhost:5001/query \
  -H "Content-Type: application/json" \
  -d '{"query": "make the reindeer dance with purple antlers!"}'
```

Response:
```json
{
  "status": "success",
  "query": "make the reindeer dance with purple antlers!",
  "response": "🦌 Let me make those antlers glow brilliantly purple while the reindeer dances with joy! ...",
  "audio_file": "output/audio_20251021_150000.mp3",
  "fseq_file": "output/sequence_20251021_150000.fseq",
  "xsq_file": "output/sequence_20251021_150000.xsq",
  "total_time_ms": 3847
}
```

### File Endpoints

```bash
# Get the latest generated FSEQ file
curl http://localhost:5001/latest-fseq --output sequence.fseq

# Get the latest generated XSQ file
curl http://localhost:5001/latest-xsq --output sequence.xsq

# Get the latest audio file
curl http://localhost:5001/latest-audio --output audio.mp3
```

## 🎨 How It Works

### 1. Text Generation (Grok AI)
User sends a query → Grok AI generates a creative, engaging response → Returns text

### 2. Text-to-Speech (Amazon Polly)
Response text → Polly converts to audio MP3 → Returns audio file + timing marks

### 3. Sequence Generation (FSEQ)
- **Load Models**: Reads latest xmodel and XSQ from `models/active_models/`
- **Extract Face Elements**: Parses faceInfo and stateInfo from xmodel
- **State Mapping**: XSQ specifies which state to use (e.g., "Reindeer_rednose_purple_antlers")
- **Color Application**: Merges base colors with state overrides
- **Frame Generation**: For each audio frame:
  - Apply static colors (Eyes, Nose, Outline, Antlers)
  - Overlay mouth animation based on phoneme/viseme timing
  - Write to FSEQ at correct channel offsets

### 4. Hardware Playback (FPP)
FSEQ file → FPP hardware reads and controls LED strips → Lights animate in sync with audio

## 🔧 Technical Details

### FSEQ Binary Format

```
Header (32 bytes):
  - "FSEQ" magic (4 bytes)
  - Version 2.0 (4 bytes)
  - Compression type: 0 (uncompressed)
  - Channel count: 450 (3 bytes per node × 150 nodes)
  - Frame count: based on audio duration
  - Step time: 50ms (0.05s per frame)

Frame Data:
  - 450 bytes per frame (RGB for each of 150 nodes)
  - Written sequentially for each frame
```

### Node-to-Channel Mapping

```
Node N → RGB Channels: (N-1)×3, (N-1)×3+1, (N-1)×3+2

Example (Node 43 = Red Nose):
  - R channel: (43-1)×3 = 126
  - G channel: 127
  - B channel: 128
```

### Face Element Colors

From xmodel state definitions:

| Element | Nodes | Default Color | State Override |
|---------|-------|---------------|-----------------|
| Eyes-Open | 51-76 | RGB(200,200,200) | (varies) |
| Eyes-Closed | 55-72 | RGB(0,0,0) | (varies) |
| FaceOutline | 77-150 | RGB(128,64,0) BROWN | (varies) |
| FaceOutline2 (Nose) | 43-50 | RGB(255,0,0) RED | State-specific |
| Mouth | 88-108 | Animated | (varies) |
| Antlers | 88-124 | (varies) | State-specific |

## 📁 Project Structure

```
├── app.py                              # Flask server entry point
├── requirements.txt                    # Python dependencies
├── config/
│   └── config.yaml                     # Application configuration
├── .env                                # Environment variables (git-ignored)
├── .env.example                        # Example env file
├── src/
│   ├── grok_client.py                  # Grok AI integration
│   ├── tts_handler.py                  # Amazon Polly TTS
│   ├── sequence_generator.py           # FSEQ binary generation (576 lines)
│   ├── fpp_client.py                   # Falcon Player control
│   ├── config_loader.py                # Configuration management
│   └── model_manager.py                # xLights model parsing
├── models/
│   └── active_models/                  # xLights model files (xmodel, xsq)
└── output/                             # Generated sequences & audio files
```

## 🎯 Example Workflows

### Scenario 1: Simple Animation

```bash
curl -X POST http://localhost:5001/query \
  -H "Content-Type: application/json" \
  -d '{"query": "make the reindeer glow"}'
```

**Result**: 
- Grok generates: "I'll make the reindeer shine with a warm, festive glow..."
- Polly creates audio + timing
- Generator creates FSEQ with glowing colors
- Sequence ready to play on FPP

### Scenario 2: State-Based Colors

```bash
curl -X POST http://localhost:5001/query \
  -H "Content-Type: application/json" \
  -d '{"query": "purple antlers now!"}'
```

**Result**:
- XSQ references state: "Reindeer_rednose_purple_antlers"
- xmodel loads this state definition
- Antlers render in purple (RGB 128, 0, 255)
- Sequence synced with speech

## ⚠️ Troubleshooting

### Issue: "No xmodel file found"
**Solution**: Place `NorRednoseReindeer.xmodel` in `models/active_models/`

### Issue: "AWS credentials not found"
**Solution**: Ensure `.env` file exists in project root with AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY

### Issue: "FPP connection failed"
**Solution**: Verify FPP hardware is at 192.168.50.200:80, or update FPP_HOST in `.env`

### Issue: "Colors look wrong on display"
**Solution**: Verify state name in XSQ matches xmodel stateInfo definitions

### Issue: "Audio/video out of sync"
**Solution**: Use `neural` engine in config.yaml (provides better timing than `standard`)

## 🔐 Security

- **No hardcoded credentials**: All secrets in `.env` (git-ignored)
- **GitHub Push Protection**: Prevents accidental credential commits
- **`.gitignore`**: Excludes `.env`, `__pycache__/`, `*.mp3`, large sequences

## 📝 Configuration Reference

### TTS Voices (Amazon Polly)

Popular options:
- **Ruth**: Warm, friendly (default)
- **Joanna**: Clear, professional
- **Matthew**: Deep, male voice
- **Amy**: Warm female
- **Ivy**: Child-like voice

Full list: [AWS Polly Voices](https://docs.aws.amazon.com/polly/latest/dg/voicelist.html)

### TTS Engines

- **neural**: High-quality, natural-sounding (15% more expensive)
- **standard**: Good quality, lower cost (default)
- **generative**: Experimental, may have limitations

### xLights States

States are defined in xmodel `stateInfo` section. Common patterns:

```xml
<state Name="Reindeer_rednose_purple_antlers">
  <s001 Name="nose" ... >43-50</s001>        <!-- Red nose -->
  <s002 Name="antlers" ... >88-124</s002>    <!-- Purple antlers -->
</state>
```

## 🚀 Deployment

### Local Development
```bash
python3 app.py
```

### Production with Gunicorn
```bash
pip install gunicorn
gunicorn -w 4 -b 0.0.0.0:5001 app:app
```

### Docker (optional)
```bash
docker build -t reindeer-lights .
docker run -p 5001:5001 --env-file .env reindeer-lights
```

## 📊 Performance Notes

- **Query Response**: 2-4 seconds (includes AI generation + TTS)
- **Sequence Generation**: 1-2 seconds (FSEQ binary writing)
- **Total Time**: 3-6 seconds end-to-end
- **File Sizes**:
  - FSEQ (30 seconds @ 20fps): ~1.5 MB
  - Audio (MP3): 100-200 KB
  - XSQ template: <100 KB

## 📚 Resources

- [xLights Documentation](https://www.xlights.org/)
- [AWS Polly Documentation](https://docs.aws.amazon.com/polly/)
- [Falcon Player (FPP)](https://falconchristmas.com/)
- [FSEQ Format Specification](https://github.com/FalconChristmas/fpp/tree/master/docs)

## 👨‍💻 Development

### Adding New Features

1. **New TTS Voice**: Update `config.yaml` → `tts.voice_id`
2. **New Face Element**: Add to xmodel `faceInfo` section
3. **New State Colors**: Add to xmodel `stateInfo` section
4. **New Hardware Integration**: Create new client in `src/` following FPPClient pattern

### Testing

```bash
# Health check
curl http://localhost:5001/health

# Test query
python3 test_query.py
```

## 📄 License

[Add your license here]

## 🤝 Contributing

Contributions welcome! Please:
1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push to the branch
5. Open a Pull Request

## 📧 Contact

For questions or issues, please open a GitHub issue or contact the project maintainer.

---

**Made with ❤️ for Christmas lights** 🎄✨🦌
