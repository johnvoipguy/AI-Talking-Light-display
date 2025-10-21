# Dynamic Sequence Generation System

## Overview
The sequence generation system is fully **model-agnostic** and **template-driven**. It automatically adapts to any model or XSQ template changes.

## How It Works

### 1. **Dynamic Model Loading**
- Loads active model from `models/active_models/`
- Extracts face structure and node definitions
- No hardcoded channel mappings

### 2. **Template XSQ Processing**
Reads `models/active_models/ReindeerChristmasGreeting.xsq` to extract:

#### Face Element Definitions (from `<faceInfo>`)
```xml
<Eyes-Open>51-54,56-71,73-76</Eyes-Open>
<FaceOutline>77-87,105-107,125-150</FaceOutline>
<Nose>43-50</Nose>
```

#### Effect Colors (from `<Effect>` tags)
```xml
<Effect type="On" color="#C8C8FF" intensity="80"/>        <!-- Eyes-Open -->
<Effect type="SingleStrand" color="#FF0000" intensity="100"/>  <!-- Nose -->
<Effect type="SingleStrand" color="#502814" intensity="60"/>   <!-- FaceOutline -->
```

### 3. **Polly Integration**
- Loads Polly viseme timing marks from `output/timings.json`
- Maps AWS visemes to xLights mouth shapes (e.g., 'a' → 'AI', 's' → 'etc')
- Applies mouth animation on top of static elements

### 4. **FSEQ Generation**
Generates binary FSEQ files with:
- **Frame header**: 32-byte FSEQ v2.0 header
- **Frame data**: Each frame contains all 450 RGB channels
- **Static elements**: Eyes, nose, outline (always lit)
- **Dynamic mouth**: Changes per frame based on viseme timing

## Adding New Model/Template

Just replace these files:
1. `models/active_models/NorRednoseReindeer.xmodel` - New character model
2. `models/active_models/ReindeerChristmasGreeting.xsq` - New template with face elements

The sequence generator will **automatically**:
- Load new face element definitions
- Extract new colors from effects
- Generate proper FSEQ with all elements

## File Structure

```
models/active_models/
├── NorRednoseReindeer.xmodel          # Model structure
└── ReindeerChristmasGreeting.xsq      # Template with elements + effects
```

## Key Classes

- `SequenceGenerator` - Main orchestrator
- `ModelManager` - Loads and caches model files
- `XLightsConverter` - Parses XSQ files
- `PhonemeMapper` - Maps visemes to mouth shapes

## Workflow

```
Query from Flask
    ↓
Grok AI generates response
    ↓
AWS Polly TTS generates audio + viseme marks
    ↓
SequenceGenerator:
  1. Load active model + template XSQ
  2. Extract face elements + colors
  3. Load Polly viseme timing marks
  4. Generate FSEQ:
     - Apply static elements every frame
     - Apply mouth shape per viseme
  5. Return FSEQ + XSQ files
    ↓
FPP client uploads to display device
    ↓
Character plays with lip-sync animation!
```

## Performance

- Typical generation: ~50-200ms for audio duration
- Fully integrated pipeline: <7 seconds total (Grok + Polly + FSEQ + FPP)
