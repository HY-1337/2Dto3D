from __future__ import annotations

import numpy as np
import trimesh


def process_mesh(mesh: trimesh.Trimesh, profile: str) -> trimesh.Trimesh:
    mesh = mesh.copy()
    _call_if_available(mesh, "remove_duplicate_faces")
    _call_if_available(mesh, "remove_degenerate_faces")
    mesh.remove_unreferenced_vertices()
    mesh.fix_normals()

    bounds = mesh.bounds
    center_xy = (bounds[0, :2] + bounds[1, :2]) / 2.0
    mesh.apply_translation([-center_xy[0], -center_xy[1], -bounds[0, 2]])

    if profile == "print":
        target_max = 80.0
        extents = mesh.extents
        current_max = float(np.max(extents)) if extents.size else 0.0
        if current_max > 0:
            mesh.apply_scale(target_max / current_max)
        bounds = mesh.bounds
        center_xy = (bounds[0, :2] + bounds[1, :2]) / 2.0
        mesh.apply_translation([-center_xy[0], -center_xy[1], -bounds[0, 2]])

    return mesh


def _call_if_available(mesh: trimesh.Trimesh, method_name: str) -> None:
    method = getattr(mesh, method_name, None)
    if method is not None:
        method()


def build_mesh_report(mesh: trimesh.Trimesh) -> dict:
    return {
        "vertices": int(len(mesh.vertices)),
        "faces": int(len(mesh.faces)),
        "is_watertight": bool(mesh.is_watertight),
        "bounds": mesh.bounds.tolist(),
        "extents": mesh.extents.tolist(),
    }
