from __future__ import annotations

import traceback
import json
from pathlib import Path

from app.core.errors import AppError
from app.core.exporter import export_outputs
from app.core.generator import generate_mesh
from app.core.input_processor import normalize_input
from app.core.job_store import fail_job, job_dir, load_state, log_path, save_state
from app.core.mesh_processor import build_mesh_report, process_mesh


def run_job(job_id: str, pdf_page: int) -> None:
    state = load_state(job_id)
    path = job_dir(job_id)

    try:
        state.status = "preprocessing"
        state.progress = 0.15
        save_state(state)

        originals = sorted(path.glob("input_original*"))
        if not originals:
            raise AppError("IMAGE_PREPROCESS_FAILED", "Original input file is missing.")
        input_file = originals[0]
        input_png = path / "input.png"
        normalize_input(input_file, input_png, pdf_page=pdf_page)

        state.status = "generating"
        state.progress = 0.45
        save_state(state)

        mesh = generate_mesh(input_png, state.backend)

        state.status = "processing_mesh"
        state.progress = 0.70
        save_state(state)

        mesh = process_mesh(mesh, state.profile)
        report = build_mesh_report(mesh)
        (path / "mesh_report.json").write_text(
            json.dumps(report, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

        state.status = "exporting"
        state.progress = 0.88
        save_state(state)

        archive_stem = f"{Path(state.input_file or 'model').stem}-{job_id[:8]}"
        outputs = export_outputs(mesh, path, archive_stem=archive_stem)
        state.outputs.obj = bool(outputs.get("obj"))
        state.outputs.threemf = bool(outputs.get("3mf"))
        state.outputs.preview = bool(outputs.get("preview"))
        state.status = "done"
        state.progress = 1.0
        save_state(state)
    except AppError as exc:
        log_path(job_id).write_text(traceback.format_exc(), encoding="utf-8")
        fail_job(job_id, exc.code, exc.message)
    except Exception as exc:
        log_path(job_id).write_text(traceback.format_exc(), encoding="utf-8")
        fail_job(job_id, "GENERATION_FAILED", str(exc))
