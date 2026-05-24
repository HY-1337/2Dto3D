# 2Dto3D Nexus AI Studio

A local three-stage AI creation workflow:

1. Generate a 2D character concept image from text.
2. Convert the 2D image into downloadable 3D assets.
3. Load the 3D model into the Nexus motion workspace and control it with AI chat or voice.

The main frontend is the Nexus React app. The root FastAPI backend provides the text-to-image and 2D-to-3D APIs.

## Project Layout

```text
E:\2Dto3D
├── backend/                         # FastAPI backend for text-to-image and 2D-to-3D
│   ├── app/api/images.py             # Text-to-image and speech transcription endpoints
│   ├── app/api/jobs.py               # 2D-to-3D job endpoints
│   └── app/core/                     # Input processing, mesh generation, export, Bambu launch
├── Nexus-3D-AI-Agent-master/
│   └── Nexus-3D-AI-Agent-master/
│       ├── frontend2/                # Main React frontend
│       └── backend2/                 # Nexus motion/chat/Unity helper services
└── models/                           # Local model folders, ignored by git
```

## Main Workflow

Open the Nexus frontend and use the tabs in order:

```text
Text to Image -> 2D to 3D -> 3D Motion
```

- `Text to Image`: creates a character concept image.
- `2D to 3D`: accepts PNG, JPG, WEBP, SVG, or PDF and exports OBJ ZIP, 3MF, and GLB preview.
- `3D Motion`: loads GLB/OBJ/3MF/FBX-style assets into the Nexus Three.js scene and connects to the Nexus WebSocket motion service.

## Requirements

- Python 3.10+
- Node.js 20+
- Optional: Bambu Studio, if you want to open exported 3MF files directly.
- Optional: Blender and Unity, if you want the full Nexus/Unity automation path.
- Optional: DashScope, OpenAI, or a custom image generation API key for text-to-image.

## Backend Setup

From the repository root:

```powershell
cd E:\2Dto3D
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r backend\requirements.txt
Copy-Item backend\.env.example backend\.env
```

Edit `backend\.env` and set the provider you want:

```env
IMAGE_PROVIDER=dashscope
DASHSCOPE_API_KEY=your-key
```

You can also use:

```env
IMAGE_PROVIDER=openai
OPENAI_API_KEY=your-key
```

Start the backend:

```powershell
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --app-dir backend
```

Backend URL:

```text
http://127.0.0.1:8000
```

## Main Frontend Setup

Open a second terminal:

```powershell
cd E:\2Dto3D\Nexus-3D-AI-Agent-master\Nexus-3D-AI-Agent-master\frontend2
npm install
npm run dev -- --host 127.0.0.1 --port 5173
```

Open:

```text
http://127.0.0.1:5173
```

The Vite dev server proxies `/api` and `/image-outputs` to the FastAPI backend on port `8000`.

## Nexus Motion Service

To enable live AI motion/chat commands in the third page, start the Nexus WebSocket service in another terminal:

```powershell
cd E:\2Dto3D\Nexus-3D-AI-Agent-master\Nexus-3D-AI-Agent-master\backend2
python interactive_server.py
```

Default WebSocket:

```text
ws://127.0.0.1:8765
```

## 2D-to-3D Notes

The 2D-to-3D backend stores jobs under `data/jobs/`, which is ignored by git.

Supported input types:

- `.png`
- `.jpg`
- `.jpeg`
- `.webp`
- `.svg`
- `.pdf`

Outputs:

- `preview.glb`
- `output.3mf`
- OBJ ZIP package

For local Bambu Studio handoff, set:

```powershell
$env:BAMBU_STUDIO_EXE = "E:\BambuStudio\Bambu Studio\bambu-studio.exe"
```

## Development Checks

Build the frontend:

```powershell
cd E:\2Dto3D\Nexus-3D-AI-Agent-master\Nexus-3D-AI-Agent-master\frontend2
npm run build
```

Check backend import:

```powershell
cd E:\2Dto3D
python -c "import sys; sys.path.insert(0, 'backend'); from app.main import app; print(app.title)"
```

## Git Hygiene

The repository ignores generated and machine-local files:

- `.env`
- virtual environments
- `node_modules`
- Vite `dist`
- generated OBJ/3MF/GLB/ZIP files
- `data/jobs`
- local model weights
- output image folders

Do not commit API keys, model weights, generated jobs, or downloaded dependency folders.
