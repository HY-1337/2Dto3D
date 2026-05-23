# 2Dto3D

Minimal local 2D-to-3D conversion module.

This repository starts with a runnable MVP skeleton:

- FastAPI backend
- Simple local job store
- Input normalization for images, SVG, and PDF where optional dependencies exist
- Placeholder local mesh generator
- OBJ, 3MF, and GLB preview exports
- Minimal test frontend
- Bambu Studio detection/open endpoint

The current `local` generator is intentionally a placeholder mesh backend. Replace
`backend/app/core/generator.py` with SF3D, TripoSR, or another image-to-3D backend
when model dependencies are ready.

## Run

```powershell
cd E:\2Dto3D
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r backend\requirements.txt
python backend\run.py
```

Then open:

```text
http://127.0.0.1:8000
```
