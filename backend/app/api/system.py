from __future__ import annotations

import shutil
import subprocess
import sys

from fastapi import APIRouter

from app.config import MODELS_DIR
from app.core.bambu import find_bambu_studio
from app.models.system import SystemCheck


router = APIRouter(tags=["system"])


@router.get("/system/check", response_model=SystemCheck)
def system_check() -> SystemCheck:
    bambu = find_bambu_studio()
    gpu = False
    cuda = False
    if shutil.which("nvidia-smi"):
        try:
            result = subprocess.run(
                ["nvidia-smi"],
                capture_output=True,
                text=True,
                timeout=5,
                check=False,
            )
            gpu = result.returncode == 0
            cuda = "CUDA Version" in result.stdout
        except Exception:
            gpu = False
            cuda = False

    return SystemCheck(
        python=bool(sys.version_info >= (3, 11)),
        gpu=gpu,
        cuda=cuda,
        local_model=(MODELS_DIR / "local_backend").exists(),
        bambu_studio=bambu is not None,
        bambu_path=str(bambu) if bambu else None,
    )

