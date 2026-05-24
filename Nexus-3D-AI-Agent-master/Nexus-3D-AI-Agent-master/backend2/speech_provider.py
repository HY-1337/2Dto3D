import os
import asyncio
import json
import uuid
import io
import subprocess
import tempfile
from fastapi import FastAPI, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
import imageio_ffmpeg
import dashscope
from dashscope.audio.asr import Recognition, RecognitionCallback, RecognitionResult

class DummyCallback(RecognitionCallback):
    def on_open(self) -> None: pass
    def on_close(self) -> None: pass
    def on_event(self, result: RecognitionResult) -> None: pass
    def on_complete(self) -> None: pass
    def on_error(self, message: str) -> None: pass

FFMPEG_EXE = imageio_ffmpeg.get_ffmpeg_exe()

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

DASHSCOPE_API_KEY = "sk-05da6cdc29c941afb5a016fa0dc42c8d"
dashscope.api_key = DASHSCOPE_API_KEY

async def dashscope_asr(pcm_data: bytes) -> str:
    print("Calling DashScope SDK...")
    try:
        # DashScope SDK provides a synchronous recognition call
        # Save PCM to a temp file because SDK expects file or url
        fd, temp_audio = tempfile.mkstemp(suffix=".wav")
        with os.fdopen(fd, 'wb') as f:
            f.write(pcm_data)
            
        def run_recognition():
            recognition = Recognition(model='paraformer-realtime-v2', format='pcm', sample_rate=16000, callback=DummyCallback())
            return recognition.call(temp_audio)
            
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(None, run_recognition)
        
        try:
            os.remove(temp_audio)
        except:
            pass
            
        print("DashScope SDK result:", result)
        
        if result.status_code == 200:
            sentences = result.get_sentence()
            if sentences:
                text = "".join([s['text'] for s in sentences])
                
                # Filter out known hallucinations
                hallucinations = ["牛逼啊，", "牛逼啊", "我发现，", "我发现", "哦，", "哦", "啊", "嗯", "这", "那个", "呢"]
                for h in hallucinations:
                    if text.startswith(h):
                        text = text[len(h):]
                        
                return text.strip()
            else:
                return ""
        else:
            print("DashScope SDK Error:", result.message)
            return f"Error: {result.message}"
            
    except Exception as e:
        print("DashScope SDK Exception:", e)
        return f"Error: {e}"

@app.post("/api/v1/transcribe")
async def transcribe_audio(file: UploadFile = File(...)):
    temp_webm = ""
    temp_pcm = ""
    try:
        audio_bytes = await file.read()
        
        print("Received audio file, size:", len(audio_bytes))
        
        # Write to temporary file
        fd_webm, temp_webm = tempfile.mkstemp(suffix=".webm")
        with os.fdopen(fd_webm, 'wb') as f:
            f.write(audio_bytes)
            
        fd_pcm, temp_pcm = tempfile.mkstemp(suffix=".pcm")
        os.close(fd_pcm) # close so ffmpeg can overwrite it
        
        print("Running ffmpeg...")
        # Call ffmpeg directly to bypass pydub/ffprobe issues
        cmd = [
            FFMPEG_EXE, "-y",
            "-i", temp_webm,
            "-f", "s16le",
            "-acodec", "pcm_s16le",
            "-ac", "1",
            "-ar", "16000",
            temp_pcm
        ]
        
        process = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        print("FFMPEG returned:", process.returncode)
        if process.returncode != 0:
            print("FFMPEG ERROR:", process.stderr.decode())
            return {"text": "", "error": "Audio conversion failed"}
            
        with open(temp_pcm, 'rb') as f:
            pcm_data = f.read()
        
        print(f"PCM data ready, size: {len(pcm_data)} bytes. Calling DashScope...")
        # Call DashScope WebSocket ASR
        text = await dashscope_asr(pcm_data)
        print("DashScope returned:", text)
        
        return {"text": text}
    except Exception as e:
        print(f"Error processing audio: {e}")
        return {"text": "", "error": str(e)}
    finally:
        # Cleanup temp files
        if os.path.exists(temp_webm):
            try: os.remove(temp_webm)
            except: pass
        if os.path.exists(temp_pcm):
            try: os.remove(temp_pcm)
            except: pass

if __name__ == "__main__":
    print("Starting Speech Provider on port 8000...")
    uvicorn.run(app, host="127.0.0.1", port=8000)
