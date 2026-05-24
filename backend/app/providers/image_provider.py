"""
文生图 Provider

DashScope 万相 2.7+ 使用:
  POST /api/v1/services/aigc/multimodal-generation/generation
"""

from __future__ import annotations

import base64
import uuid
from abc import ABC, abstractmethod
from pathlib import Path

import httpx

from app.config import settings


class ImageProvider(ABC):
    @abstractmethod
    async def generate(
        self,
        prompt: str,
        negative_prompt: str,
        width: int,
        height: int,
        output_dir: Path,
    ) -> tuple[str, Path]:
        """返回 (image_url, local_path)"""


async def _download_image(client: httpx.AsyncClient, url: str, output_dir: Path) -> Path:
    resp = await client.get(url)
    resp.raise_for_status()
    filename = f"{uuid.uuid4().hex}.png"
    path = output_dir / filename
    path.write_bytes(resp.content)
    return path


async def _save_base64_image(b64_data: str, output_dir: Path) -> Path:
    filename = f"{uuid.uuid4().hex}.png"
    path = output_dir / filename
    path.write_bytes(base64.b64decode(b64_data))
    return path


def _build_wan27_text(prompt: str, negative_prompt: str) -> str:
    """万相 2.7 无 negative_prompt 参数，合并进正文。"""
    text = prompt.strip()
    if negative_prompt.strip():
        text = f"{text}\n\nAvoid: {negative_prompt.strip()}"
    return text


def _resolve_wan27_size(width: int, height: int, model: str) -> str:
    """
    万相 2.7 size 参数：
    - 推荐 1K / 2K / 4K（pro 文生图支持 4K）
    - 或像素值如 1024*1024
    """
    if settings.dashscope_size:
        return settings.dashscope_size

    pixels = width * height
    if pixels <= 1024 * 1024:
        return "1K"
    if pixels <= 2048 * 2048:
        return "2K"
    if "pro" in model.lower():
        return "4K"
    return "2K"


def _extract_image_urls(payload: dict) -> list[str]:
    output = payload.get("output") or {}
    urls: list[str] = []

    for choice in output.get("choices") or []:
        message = choice.get("message") or {}
        for item in message.get("content") or []:
            if isinstance(item, dict) and item.get("image"):
                urls.append(item["image"])

    return urls


class DashScopeProvider(ImageProvider):
    """万相 2.7 — multimodal-generation/generation（同步调用）"""

    GENERATION_URL = (
        "https://dashscope.aliyuncs.com/api/v1/services/aigc/multimodal-generation/generation"
    )

    async def generate(self, prompt, negative_prompt, width, height, output_dir) -> tuple[str, Path]:
        if not settings.dashscope_api_key:
            raise ValueError("DASHSCOPE_API_KEY 未配置")

        model = settings.dashscope_model
        text = _build_wan27_text(prompt, negative_prompt)
        size = _resolve_wan27_size(width, height, model)

        headers = {
            "Authorization": f"Bearer {settings.dashscope_api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": model,
            "input": {
                "messages": [
                    {
                        "role": "user",
                        "content": [{"text": text}],
                    }
                ]
            },
            "parameters": {
                "size": size,
                "n": 1,
                "watermark": settings.dashscope_watermark,
                "thinking_mode": settings.dashscope_thinking_mode,
            },
        }

        url = settings.dashscope_api_url or self.GENERATION_URL

        async with httpx.AsyncClient(timeout=180.0) as client:
            resp = await client.post(url, headers=headers, json=payload)
            if resp.is_error:
                try:
                    err = resp.json()
                    msg = err.get("message") or err
                except Exception:
                    msg = resp.text
                raise RuntimeError(f"DashScope HTTP {resp.status_code}: {msg}")

            data = resp.json()

            if data.get("code"):
                raise RuntimeError(f"DashScope 生图失败: [{data.get('code')}] {data.get('message')}")

            image_urls = _extract_image_urls(data)
            if not image_urls:
                raise RuntimeError(f"DashScope 响应中未找到图片: {data}")

            image_url = image_urls[0]
            local_path = await _download_image(client, image_url, output_dir)
            return image_url, local_path


class OpenAIProvider(ImageProvider):
    """OpenAI DALL-E"""

    async def generate(self, prompt, negative_prompt, width, height, output_dir) -> tuple[str, Path]:
        if not settings.openai_api_key:
            raise ValueError("OPENAI_API_KEY 未配置")

        url = f"{settings.openai_base_url.rstrip('/')}/images/generations"
        headers = {
            "Authorization": f"Bearer {settings.openai_api_key}",
            "Content-Type": "application/json",
        }
        size = "1024x1024"
        if width == 1024 and height == 1792:
            size = "1024x1792"
        elif width == 1792 and height == 1024:
            size = "1792x1024"

        payload = {
            "model": settings.openai_model,
            "prompt": prompt,
            "n": 1,
            "size": size,
            "response_format": "url",
        }

        async with httpx.AsyncClient(timeout=120.0) as client:
            resp = await client.post(url, headers=headers, json=payload)
            resp.raise_for_status()
            image_url = resp.json()["data"][0]["url"]
            local_path = await _download_image(client, image_url, output_dir)
            return image_url, local_path


class CustomProvider(ImageProvider):
    """自定义 HTTP 接口"""

    async def generate(self, prompt, negative_prompt, width, height, output_dir) -> tuple[str, Path]:
        if not settings.custom_api_url:
            raise ValueError("CUSTOM_API_URL 未配置")

        headers = {"Content-Type": "application/json"}
        if settings.custom_api_key:
            headers["Authorization"] = f"Bearer {settings.custom_api_key}"

        payload = {
            "prompt": prompt,
            "negative_prompt": negative_prompt,
            "width": width,
            "height": height,
            "n": 1,
        }

        async with httpx.AsyncClient(timeout=120.0) as client:
            resp = await client.post(settings.custom_api_url, headers=headers, json=payload)
            resp.raise_for_status()
            data = resp.json()

            item = data["data"][0]
            if "url" in item:
                image_url = item["url"]
                local_path = await _download_image(client, image_url, output_dir)
                return image_url, local_path
            if "b64_json" in item:
                local_path = await _save_base64_image(item["b64_json"], output_dir)
                return str(local_path), local_path

            raise ValueError(f"无法解析 custom API 响应: {data}")


def get_image_provider() -> ImageProvider:
    providers = {
        "dashscope": DashScopeProvider,
        "openai": OpenAIProvider,
        "custom": CustomProvider,
    }
    key = settings.image_provider.lower()
    if key not in providers:
        raise ValueError(f"未知 IMAGE_PROVIDER: {key}，可选: {list(providers)}")
    return providers[key]()
