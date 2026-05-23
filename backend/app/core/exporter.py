from __future__ import annotations

from pathlib import Path
import json
from zipfile import ZipFile, ZIP_DEFLATED

import trimesh

from app.core.errors import AppError


def export_outputs(mesh: trimesh.Trimesh, job_path: Path, archive_stem: str | None = None) -> dict:
    outputs = {}
    try:
        obj_path = job_path / "output.obj"
        mesh.export(obj_path)
        outputs["obj"] = obj_path.exists()
    except Exception as exc:
        raise AppError("EXPORT_OBJ_FAILED", str(exc)) from exc

    try:
        threemf_path = job_path / "output.3mf"
        mesh.export(threemf_path)
        outputs["3mf"] = threemf_path.exists()
    except Exception as exc:
        raise AppError("EXPORT_3MF_FAILED", str(exc)) from exc

    try:
        preview_path = job_path / "preview.glb"
        mesh.export(preview_path)
        outputs["preview"] = preview_path.exists()
    except Exception:
        outputs["preview"] = False

    if obj_path.exists():
        build_obj_archive(job_path, archive_stem or "model")

    return outputs


def build_obj_archive(job_path: Path, archive_stem: str) -> Path:
    obj_path = job_path / "output.obj"
    zip_path = job_path / "model.zip"
    mtl_path = job_path / "output.mtl"
    texture_path = job_path / "texture.png"

    with ZipFile(zip_path, "w", ZIP_DEFLATED) as archive:
        archive.write(obj_path, f"{archive_stem}.obj")
        if mtl_path.exists():
            archive.write(mtl_path, f"{archive_stem}.mtl")
        if texture_path.exists():
            archive.write(texture_path, f"{archive_stem}-texture.png")
        archive.writestr(
            "job_manifest.json",
            json.dumps(
                {
                    "job_archive_stem": archive_stem,
                    "obj": f"{archive_stem}.obj",
                    "source_obj": "output.obj",
                },
                ensure_ascii=False,
                indent=2,
            ),
        )
    return zip_path
