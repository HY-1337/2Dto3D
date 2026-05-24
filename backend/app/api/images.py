from __future__ import annotations

import uuid

from fastapi import APIRouter, File, HTTPException, UploadFile
from pydantic import BaseModel

from app.config import settings
from app.prompts import OffTopicError, StylePreset as PromptStyle
from app.prompts import build_prompt
from app.providers import get_image_provider, get_speech_provider
from app.providers.speech_provider import _detect_format
from app.schemas import GenerateRequest, GenerateResponse, HealthResponse, StylePreset


router = APIRouter(tags=["images"])


class TranscribeResponse(BaseModel):
    text: str


@router.get("/images/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    return HealthResponse(status="ok", provider=settings.image_provider, topic="chaowan")


@router.post("/images/transcribe", response_model=TranscribeResponse)
async def transcribe_audio(audio: UploadFile = File(...)) -> TranscribeResponse:
    if not audio.filename:
        raise HTTPException(status_code=400, detail="Please upload an audio file.")

    audio_bytes = await audio.read()
    if not audio_bytes:
        raise HTTPException(status_code=400, detail="Audio file is empty.")
    if len(audio_bytes) > 10 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="Audio file is too large. Max size is 10 MB.")

    try:
        speech = get_speech_provider()
        text = await speech.transcribe(audio_bytes, _detect_format(audio.filename))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    return TranscribeResponse(text=text)


@router.get("/images/prompt/preview")
async def preview_prompt(
    prompt: str,
    style: StylePreset = StylePreset.chaoplay,
    extra_suffix: str = "",
) -> dict:
    try:
        return build_prompt(prompt, PromptStyle(style.value), extra_suffix)
    except OffTopicError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.post("/images/generate", response_model=GenerateResponse)
async def generate_image(body: GenerateRequest) -> GenerateResponse:
    width = body.width or settings.default_width
    height = body.height or settings.default_height

    try:
        prompt_data = build_prompt(
            user_prompt=body.prompt,
            style=PromptStyle(body.style.value),
            extra_suffix=body.extra_suffix,
        )
    except OffTopicError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    try:
        provider = get_image_provider()
        _provider_url, local_path = await provider.generate(
            prompt=str(prompt_data["prompt"]),
            negative_prompt=str(prompt_data["negative_prompt"]),
            width=width,
            height=height,
            output_dir=settings.output_dir,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except TimeoutError as exc:
        raise HTTPException(status_code=504, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Image generation failed: {exc}") from exc

    return GenerateResponse(
        task_id=uuid.uuid4().hex,
        image_url=f"/image-outputs/{local_path.name}",
        local_path=str(local_path.resolve()),
        prompt=str(prompt_data["prompt"]),
        negative_prompt=str(prompt_data["negative_prompt"]),
        style=str(prompt_data["style"]),
        provider=settings.image_provider,
        topic=str(prompt_data["topic"]),
        normalized_subject=str(prompt_data["normalized_subject"]),
        enforced_rules=list(prompt_data["enforced_rules"]),
    )
