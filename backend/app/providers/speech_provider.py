"""
语音识别 Provider — DashScope Paraformer 实时 WebSocket ASR

协议: paraformer-realtime-v2, wss://dashscope.aliyuncs.com/api-ws/v1/inference
"""

from __future__ import annotations

import asyncio
import io
import json
import uuid
from abc import ABC, abstractmethod
from io import BytesIO

import websockets

from app.config import settings


class SpeechProvider(ABC):
    @abstractmethod
    async def transcribe(self, audio_bytes: bytes, audio_format: str) -> str:
        """返回转录文本"""


def _detect_format(filename: str) -> str:
    mapping = {
        "wav": "wav", "wave": "wav",
        "mp3": "mp3", "mpeg": "mp3",
        "webm": "webm",
        "m4a": "m4a", "mp4": "m4a", "aac": "m4a",
        "ogg": "ogg", "oga": "ogg", "opus": "ogg",
        "flac": "flac",
        "pcm": "pcm",
    }
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    return mapping.get(ext, "wav")


def _read_wav_info(audio_bytes: bytes) -> tuple[int, int, bytes]:
    """读取 WAV 信息，返回 (sample_rate, channels, raw_pcm_bytes)。"""
    import wave as _wave
    with _wave.open(BytesIO(audio_bytes), "rb") as wf:
        sr = wf.getframerate()
        nch = wf.getnchannels()
        raw = wf.readframes(wf.getnframes())
    return sr, nch, raw


class DashScopeRealtimeASRProvider(SpeechProvider):
    """阿里云 Paraformer 实时语音识别 (WebSocket)"""

    WS_URL = "wss://dashscope.aliyuncs.com/api-ws/v1/inference"

    async def transcribe(self, audio_bytes: bytes, audio_format: str) -> str:
        if not settings.dashscope_api_key:
            raise ValueError("DASHSCOPE_API_KEY 未配置")

        # 准备传给 API 的音频数据和参数
        if audio_format in ("wav", "wave"):
            # WAV 直接传完整文件（含头），API 从 WAV 头解析采样率
            sample_rate, _, _ = _read_wav_info(audio_bytes)
            audio_data = audio_bytes
            send_fmt = "wav"
        elif audio_format == "pcm":
            sample_rate = 16000
            audio_data = audio_bytes
            send_fmt = "pcm"
        else:
            try:
                from pydub import AudioSegment
                buf = BytesIO(audio_bytes)
                seg = AudioSegment.from_file(buf, format=audio_format or "wav")
                seg = seg.set_channels(1)
                sample_rate = seg.frame_rate
                audio_data = seg.raw_data
                send_fmt = "pcm"
            except Exception:
                raise RuntimeError(
                    f"音频格式转换失败（{audio_format}），请使用 WAV 格式录音。"
                )

        task_id = uuid.uuid4().hex
        headers = {"Authorization": f"Bearer {settings.dashscope_api_key}"}

        async with websockets.connect(
            self.WS_URL,
            additional_headers=headers,
            ping_interval=20,
            ping_timeout=10,
        ) as ws:
            run_msg = {
                "header": {
                    "action": "run-task",
                    "task_id": task_id,
                    "streaming": "duplex",
                },
                "payload": {
                    "task_group": "audio",
                    "task": "asr",
                    "function": "recognition",
                    "model": "paraformer-realtime-v2",
                    "parameters": {
                        "format": send_fmt,
                        "sample_rate": sample_rate,
                        "language_hints": ["zh"],
                    },
                    "input": {},
                },
            }
            await ws.send(json.dumps(run_msg))

            resp = await ws.recv()
            parsed = json.loads(resp)
            event = parsed.get("header", {}).get("event", "")
            if event == "task-failed":
                raise RuntimeError(f"ASR 任务启动失败: {parsed}")

            # 分块发送
            chunk_size = sample_rate * 2 // 10  # 100ms 一帧
            final_text = ""

            for i in range(0, len(audio_data), chunk_size):
                chunk = audio_data[i : i + chunk_size]
                if not chunk:
                    break
                await ws.send(chunk)

                try:
                    result = await asyncio.wait_for(ws.recv(), timeout=0.05)
                    text, is_final = _extract_sentence(result)
                    if is_final and len(text) > len(final_text):
                        final_text = text
                except asyncio.TimeoutError:
                    pass

            # 4. 发送 finish-task
            finish_msg = {
                "header": {
                    "action": "finish-task",
                    "task_id": task_id,
                    "streaming": "duplex",
                },
                "payload": {"input": {}},
            }
            await ws.send(json.dumps(finish_msg))

            # 5. 收尾结果直到 task-finished
            while True:
                try:
                    result = await asyncio.wait_for(ws.recv(), timeout=3)
                    text, is_final = _extract_sentence(result)
                    if is_final and len(text) > len(final_text):
                        final_text = text
                    parsed = json.loads(result)
                    if parsed.get("header", {}).get("event") == "task-finished":
                        break
                except asyncio.TimeoutError:
                    break

        if not final_text:
            raise RuntimeError("语音识别结果为空，请检查音频是否有有效语音内容")
        return final_text


def _extract_sentence(raw: str) -> tuple[str, bool]:
    """从 WebSocket 消息中提取识别文本和是否为最终结果。"""
    try:
        data = json.loads(raw)
        sent = data.get("payload", {}).get("output", {}).get("sentence", {})
        text = sent.get("text", "").strip()
        is_final = sent.get("is_final", False) or sent.get("end_time") is not None
        return text, is_final
    except Exception:
        return "", False


def get_speech_provider() -> SpeechProvider:
    return DashScopeRealtimeASRProvider()
