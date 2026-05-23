from __future__ import annotations

from pathlib import Path
import os
import subprocess
import sys

import numpy as np
import trimesh
from PIL import Image

from app.config import PROJECT_ROOT
from app.core.errors import AppError

DEFAULT_MC_RESOLUTION = "256"


def generate_mesh(input_png: Path, backend: str) -> trimesh.Trimesh:
    if backend == "cloud_stub":
        raise AppError(
            "CLOUD_BACKEND_NOT_CONFIGURED",
            "Cloud backend is reserved but not configured in MVP.",
        )
    if backend != "local":
        raise AppError("GENERATION_FAILED", f"Unknown backend: {backend}")

    if os.environ.get("GENERATOR_MODE") == "placeholder":
        return _placeholder_image_mesh(input_png)

    triposr_mesh = _generate_with_triposr(input_png)
    if triposr_mesh is not None:
        return triposr_mesh

    return _placeholder_image_mesh(input_png)


def _generate_with_triposr(input_png: Path) -> trimesh.Trimesh | None:
    triposr_dir = PROJECT_ROOT / "models" / "TripoSR"
    triposr_script = triposr_dir / "run.py"
    ai_python = _resolve_triposr_python()
    local_model = triposr_dir / "pretrained" / "TripoSR"

    if not triposr_script.exists() or not ai_python.exists() or not local_model.exists():
        return None

    output_dir = input_png.parent / "triposr_output"
    output_dir.mkdir(parents=True, exist_ok=True)

    command = [
        str(ai_python),
        "run.py",
        str(input_png),
        "--output-dir",
        str(output_dir),
        "--pretrained-model-name-or-path",
        str(local_model),
        "--model-save-format",
        "obj",
        "--mc-resolution",
        os.environ.get("TRIPOSR_MC_RESOLUTION", DEFAULT_MC_RESOLUTION),
    ]

    result = subprocess.run(
        command,
        cwd=triposr_dir,
        capture_output=True,
        text=True,
        timeout=900,
        check=False,
    )
    (input_png.parent / "triposr_stdout.log").write_text(result.stdout, encoding="utf-8")
    (input_png.parent / "triposr_stderr.log").write_text(result.stderr, encoding="utf-8")

    if result.returncode != 0:
        raise AppError(
            "GENERATION_FAILED",
            "TripoSR failed. See triposr_stdout.log and triposr_stderr.log in the job folder.",
        )

    mesh_path = output_dir / "0" / "mesh.obj"
    if not mesh_path.exists():
        raise AppError("GENERATION_FAILED", "TripoSR finished but mesh.obj was not found.")

    loaded = trimesh.load(mesh_path, force="mesh")
    if isinstance(loaded, trimesh.Scene):
        loaded = trimesh.util.concatenate(tuple(loaded.geometry.values()))
    if loaded.is_empty:
        raise AppError("GENERATION_FAILED", "TripoSR generated an empty mesh.")
    return loaded


def _resolve_triposr_python() -> Path:
    configured = os.environ.get("TRIPOSR_PYTHON")
    if configured:
        return Path(configured)

    # Use the same Python that starts the backend by default. In this project,
    # that is the environment where TripoSR was already verified manually.
    current = Path(sys.executable)
    if current.exists():
        return current

    ai_python = PROJECT_ROOT / ".venv-ai" / "Scripts" / "python.exe"
    if ai_python.exists():
        return ai_python

    return Path("python")


def _placeholder_image_mesh(input_png: Path) -> trimesh.Trimesh:
    """Temporary backend: creates a printable relief-like mesh from image alpha."""
    image = Image.open(input_png).convert("RGBA").resize((96, 96))
    alpha = np.asarray(image.getchannel("A"), dtype=np.float32) / 255.0
    gray = np.asarray(image.convert("L"), dtype=np.float32) / 255.0
    mask = alpha > 0.05

    if not mask.any():
        raise AppError("GENERATION_FAILED", "Input image has no visible pixels.")

    height = 2.0 + 8.0 * gray * alpha
    height[~mask] = 0.0

    rows, cols = height.shape
    width_mm = 80.0
    depth_mm = 80.0
    xs = np.linspace(-width_mm / 2, width_mm / 2, cols)
    ys = np.linspace(-depth_mm / 2, depth_mm / 2, rows)

    vertices = []
    for y in ys:
        for x in xs:
            vertices.append([x, y, 0.0])
    for r, y in enumerate(ys):
        for c, x in enumerate(xs):
            vertices.append([x, y, float(height[r, c])])

    faces = []
    top_offset = rows * cols
    for r in range(rows - 1):
        for c in range(cols - 1):
            a = r * cols + c
            b = a + 1
            d = (r + 1) * cols + c
            e = d + 1
            ta, tb, td, te = top_offset + a, top_offset + b, top_offset + d, top_offset + e
            faces.extend([[ta, td, tb], [tb, td, te]])
            faces.extend([[a, b, d], [b, e, d]])

    for c in range(cols - 1):
        _add_side(faces, c, c + 1, top_offset + c, top_offset + c + 1)
        a = (rows - 1) * cols + c
        b = a + 1
        _add_side(faces, b, a, top_offset + b, top_offset + a)

    for r in range(rows - 1):
        a = r * cols
        b = (r + 1) * cols
        _add_side(faces, b, a, top_offset + b, top_offset + a)
        a = r * cols + cols - 1
        b = (r + 1) * cols + cols - 1
        _add_side(faces, a, b, top_offset + a, top_offset + b)

    mesh = trimesh.Trimesh(vertices=np.asarray(vertices), faces=np.asarray(faces), process=True)
    if mesh.is_empty:
        raise AppError("GENERATION_FAILED", "Generated mesh is empty.")
    return mesh


def _add_side(faces: list[list[int]], bottom_a: int, bottom_b: int, top_a: int, top_b: int) -> None:
    faces.extend([[bottom_a, bottom_b, top_a], [bottom_b, top_b, top_a]])
