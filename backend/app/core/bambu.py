from __future__ import annotations

import os
from pathlib import Path
import subprocess

from app.core.errors import AppError


def find_bambu_studio() -> Path | None:
    candidates = [
        Path(r"C:\Program Files\Bambu Studio\bambu-studio.exe"),
        Path(r"C:\Program Files\Bambu Studio\BambuStudio.exe"),
    ]

    local_app_data = os.environ.get("LOCALAPPDATA")
    if local_app_data:
        candidates.append(Path(local_app_data) / "Programs" / "Bambu Studio" / "BambuStudio.exe")
        candidates.append(Path(local_app_data) / "Programs" / "Bambu Studio" / "bambu-studio.exe")

    for path in candidates:
        if path.exists():
            return path
    return None


def open_bambu_with_file(model_path: Path) -> Path:
    if not model_path.exists():
        raise AppError("EXPORT_3MF_FAILED", "3MF output does not exist.")

    executable = find_bambu_studio()
    if executable is None:
        raise AppError(
            "BAMBU_STUDIO_NOT_FOUND",
            "Bambu Studio was not found. Please open the 3MF manually.",
        )

    subprocess.Popen([str(executable), str(model_path)])
    return executable

