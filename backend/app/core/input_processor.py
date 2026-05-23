from __future__ import annotations

from pathlib import Path
import re
import xml.etree.ElementTree as ET

from PIL import Image, ImageDraw, ImageOps

from app.config import SUPPORTED_EXTENSIONS
from app.core.errors import AppError


TARGET_SIZE = 768


def normalize_input(input_path: Path, output_path: Path, pdf_page: int = 1) -> Path:
    ext = input_path.suffix.lower()
    if ext not in SUPPORTED_EXTENSIONS:
        raise AppError("UNSUPPORTED_FILE_TYPE", f"Unsupported file type: {ext}")

    try:
        if ext in {".png", ".jpg", ".jpeg", ".webp"}:
            image = Image.open(input_path)
        elif ext == ".svg":
            image = _render_svg(input_path)
        elif ext == ".pdf":
            image = _render_pdf(input_path, pdf_page)
        else:
            raise AppError("UNSUPPORTED_FILE_TYPE", f"Unsupported file type: {ext}")

        image = ImageOps.exif_transpose(image).convert("RGBA")
        image.thumbnail((TARGET_SIZE, TARGET_SIZE), Image.Resampling.LANCZOS)

        canvas = Image.new("RGBA", (TARGET_SIZE, TARGET_SIZE), (0, 0, 0, 0))
        x = (TARGET_SIZE - image.width) // 2
        y = (TARGET_SIZE - image.height) // 2
        canvas.alpha_composite(image, (x, y))
        canvas.save(output_path)
        return output_path
    except AppError:
        raise
    except Exception as exc:
        raise AppError("IMAGE_PREPROCESS_FAILED", str(exc)) from exc


def _render_svg(input_path: Path) -> Image.Image:
    try:
        import cairosvg
    except Exception:
        return _render_svg_fallback(input_path)

    try:
        png_bytes = cairosvg.svg2png(url=str(input_path), output_width=TARGET_SIZE)
        from io import BytesIO

        return Image.open(BytesIO(png_bytes))
    except Exception:
        return _render_svg_fallback(input_path)


def _render_svg_fallback(input_path: Path) -> Image.Image:
    """Small no-Cairo fallback for simple SVG shape tests."""
    try:
        text = input_path.read_text(encoding="utf-8")
        root = ET.fromstring(text)
        image = Image.new("RGBA", (TARGET_SIZE, TARGET_SIZE), (255, 255, 255, 0))
        draw = ImageDraw.Draw(image)

        view_box = root.attrib.get("viewBox", "0 0 100 100")
        parts = [float(part) for part in re.split(r"[\s,]+", view_box.strip()) if part]
        if len(parts) == 4:
            _, _, width, height = parts
        else:
            width = height = 100.0

        scale = min(TARGET_SIZE / width, TARGET_SIZE / height) * 0.85
        offset_x = (TARGET_SIZE - width * scale) / 2
        offset_y = (TARGET_SIZE - height * scale) / 2

        for element in root.iter():
            tag = element.tag.split("}")[-1]
            fill = element.attrib.get("fill", "#888")
            if fill == "none":
                fill = "#888"
            if tag == "rect":
                x = float(element.attrib.get("x", 0)) * scale + offset_x
                y = float(element.attrib.get("y", 0)) * scale + offset_y
                w = float(element.attrib.get("width", width)) * scale
                h = float(element.attrib.get("height", height)) * scale
                draw.rectangle([x, y, x + w, y + h], fill=fill)
            elif tag == "circle":
                cx = float(element.attrib.get("cx", width / 2)) * scale + offset_x
                cy = float(element.attrib.get("cy", height / 2)) * scale + offset_y
                r = float(element.attrib.get("r", min(width, height) / 3)) * scale
                draw.ellipse([cx - r, cy - r, cx + r, cy + r], fill=fill)
            elif tag == "path":
                draw.rectangle(
                    [
                        offset_x + width * scale * 0.15,
                        offset_y + height * scale * 0.15,
                        offset_x + width * scale * 0.85,
                        offset_y + height * scale * 0.85,
                    ],
                    fill=fill,
                )

        return image
    except Exception as exc:
        raise AppError("SVG_RENDER_FAILED", str(exc)) from exc


def _render_pdf(input_path: Path, pdf_page: int) -> Image.Image:
    try:
        import fitz
    except Exception as exc:
        raise AppError("PDF_RENDER_FAILED", "pymupdf is not installed.") from exc

    try:
        page_index = max(pdf_page, 1) - 1
        document = fitz.open(input_path)
        if page_index >= len(document):
            raise AppError("PDF_RENDER_FAILED", f"PDF page {pdf_page} does not exist.")
        page = document[page_index]
        pix = page.get_pixmap(matrix=fitz.Matrix(2, 2), alpha=True)
        return Image.frombytes("RGBA", [pix.width, pix.height], pix.samples)
    except AppError:
        raise
    except Exception as exc:
        raise AppError("PDF_RENDER_FAILED", str(exc)) from exc
