import asyncio
import websockets
import json
import logging
import base64
import urllib.parse
import urllib.request
import os
import uuid
from openai import AsyncOpenAI
import threading
import http.server
import socketserver

class CORSRequestHandler(http.server.SimpleHTTPRequestHandler):
    def end_headers(self):
        self.send_header('Access-Control-Allow-Origin', '*')
        super().end_headers()

def start_http_server():
    try:
        with socketserver.TCPServer(("127.0.0.1", 8080), CORSRequestHandler) as httpd:
            httpd.serve_forever()
    except Exception as e:
        print(f"HTTP Server failed to start: {e}")

from agent_tools import Generate3DModelTool
from image_generator import ImageGeneratorTool

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("InteractiveServer")

DEEPSEEK_API_KEY = "sk-da49bc3aceff4c799893294ff0163ad9"
DEEPSEEK_BASE_URL = "https://api.deepseek.com/v1"

client = AsyncOpenAI(
    api_key=DEEPSEEK_API_KEY,
    base_url=DEEPSEEK_BASE_URL
)

SYSTEM_PROMPT = """
你是一个运行在 Unity 游戏引擎中的“AI 沙盒创世系统”控制大脑。
你可以与用户聊天，控制数字人动作，或者根据用户需求自动生成 3D 数字人和游戏场景背景。

当前场景的状态（包括各个角色的坐标 `avatars`，以及场景中物理对象的位置 `objects`）将在每次用户发送消息时附加。你需要根据用户输入和当前场景状态，判断意图，并返回严格的 JSON 格式。
你可以返回单个 JSON 对象，或者一个包含多个 JSON 对象的 **JSON 数组 (Array)**，如果你需要同时控制多个角色的行动（并发指令）。

支持的 action：

1. 生成数字人 (generate_avatar)
当用户要求“生成一个武士”、“在这个场景里放一个机器人”等，使用此 action。
{
    "action": "generate_avatar",
    "prompt": "对这个数字人的详细英文英文描述，用于提示词",
    "reply": "好的，正在为您生成数字人..."
}

2. 生成场景 (generate_scene)
当用户要求“生成一个赛博朋克街道场景”等，使用此 action。
{
    "action": "generate_scene",
    "prompt": "对这个场景的高清全景英文描述，用于提示词",
    "reply": "正在生成场景背景..."
}

3. 移动数字人 (move_to)
当你需要数字人走到场景中的特定位置，**或者去踢开/撞开/推开某个场景物体** 时使用。
利用传入的场景状态 `objects` 找到目标物体的 position [x, y, z]，然后输出 destination。因为引擎有物理碰撞，只要数字人走到物体的位置，自然就会踢到/推到它！不需要写 dynamic_code！
{
    "action": "move_to",
    "target": "Avatar 1",
    "destination": [x, y, z],
    "reply": "我这就走过去踢那个箱子。"
}

4. 聊天与控制数字人动作 (chat)
当用户要求某个具体的数字人做动作或聊天时使用。如果没说几号，默认 target 为 "Avatar 1"。
Trigger 支持: "Idle", "Walk", "Wave", "Talk", "Dance", "Jump", "Sing"
{
    "action": "chat",
    "target": "Avatar 1",
    "trigger": "Wave",
    "reply": "你好！我是1号数字人。"
}

5. 动态代码生成 (dynamic_code)
当用户要求数字人执行复杂的动态行为（非简单移动），如飞行、变大等，使用此 action。
{
    "action": "dynamic_code",
    "target": "Avatar 1",
    "trigger": "Idle",
    "code": "group.position.y = 2 + Math.sin(state.clock.elapsedTime * 2);",
    "reply": "正在飞行！"
}

请务必只返回合法的 JSON（或 JSON 数组），不要有任何其他多余的解释。如果用户让你们各自向两边走，你可以返回 [{"action":"move_to", "target":"Avatar 1", "destination":[-5,0,0], "reply":"我去左边"}, {"action":"move_to", "target":"Avatar 2", "destination":[5,0,0], "reply":"我去右边"}]
"""

connected_clients = set()

try:
    image_gen_tool = ImageGeneratorTool()
    model_gen_tool = Generate3DModelTool()
except Exception as e:
    logger.error(f"工具初始化失败: {e}")

async def process_user_input(user_text):
    logger.info(f"发送给大模型: {user_text}")
    try:
        response = await client.chat.completions.create(
            model="deepseek-v4-pro",
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_text}
            ],
            temperature=0.3
        )
        result_text = response.choices[0].message.content.strip()
        # Clean markdown formatting if present
        if result_text.startswith("```json"):
            result_text = result_text[7:]
        if result_text.startswith("```"):
            result_text = result_text[3:]
        if result_text.endswith("```"):
            result_text = result_text[:-3]
            
        result_json = json.loads(result_text)
        logger.info(f"大模型解析意图: {result_json}")
        return result_json
    except Exception as e:
        logger.error(f"大模型调用失败: {e}")
        return {"action": "chat", "target": "Avatar 1", "trigger": "Idle", "reply": "抱歉，我的大脑暂时断线了。"}

async def generate_audio_base64(text):
    try:
        url = f"http://127.0.0.1:9880/?text={urllib.parse.quote(text)}&text_language=zh"
        loop = asyncio.get_event_loop()
        def fetch_audio():
            req = urllib.request.Request(url)
            with urllib.request.urlopen(req, timeout=15) as response:
                return response.read()
        logger.info(f"正在请求 GPT-SoVITS 语音合成...")
        audio_bytes = await loop.run_in_executor(None, fetch_audio)
        return base64.b64encode(audio_bytes).decode('utf-8')
    except Exception as e:
        logger.error(f"语音合成失败: {e}")
        return None

async def background_generate_scene(prompt: str):
    logger.info(f"后台开始生成场景: {prompt}")
    try:
        loop = asyncio.get_event_loop()
        output_filename = f"scene_{uuid.uuid4().hex[:6]}.jpg"
        abs_path = os.path.abspath(output_filename)
        await loop.run_in_executor(None, image_gen_tool.generate, prompt, abs_path)
        url = f"http://127.0.0.1:8080/{output_filename}"
        msg = json.dumps({"action": "load_scene", "path": url})
        websockets.broadcast(connected_clients, msg)
    except Exception as e:
        logger.error(f"生成场景失败: {e}")

async def background_generate_avatar(prompt: str):
    logger.info(f"后台开始生成数字人: {prompt}")
    try:
        loop = asyncio.get_event_loop()
        img_filename = f"avatar_2d_{uuid.uuid4().hex[:6]}.jpg"
        glb_filename = f"avatar_3d_{uuid.uuid4().hex[:6]}.glb"
        abs_img = os.path.abspath(img_filename)
        abs_glb = os.path.abspath(glb_filename)
        await loop.run_in_executor(None, image_gen_tool.generate, prompt, abs_img)
        await loop.run_in_executor(None, model_gen_tool.generate, None, abs_img, abs_glb)
        url = f"http://127.0.0.1:8080/{glb_filename}"
        msg = json.dumps({"action": "load_avatar", "path": url})
        websockets.broadcast(connected_clients, msg)
    except Exception as e:
        logger.error(f"生成数字人失败: {e}")

async def handle_client(websocket): 
    logger.info(f"新的客户端连接建立")
    connected_clients.add(websocket)
    try:
        async for message in websocket:
            logger.info(f"收到客户端消息: {message}")
            user_text = message
            try:
                msg_json = json.loads(message)
                if "text" in msg_json:
                    text_content = msg_json["text"]
                    if "sceneState" in msg_json:
                        user_text = f"【当前场景状态】: {json.dumps(msg_json['sceneState'], ensure_ascii=False)}\n【用户指令】: {text_content}"
                    else:
                        user_text = text_content
            except json.JSONDecodeError:
                pass 
            
            llm_response = await process_user_input(user_text)
            
            actions = llm_response if isinstance(llm_response, list) else [llm_response]
            
            for act in actions:
                action = act.get("action", "chat")
                reply_text = act.get("reply", "")
                if reply_text:
                    audio_b64 = await generate_audio_base64(reply_text)
                    if audio_b64:
                        act["audio_base64"] = audio_b64
                
                if action == "generate_scene":
                    asyncio.create_task(background_generate_scene(act.get("prompt", "a beautiful background")))
                elif action == "generate_avatar":
                    asyncio.create_task(background_generate_avatar(act.get("prompt", "a humanoid character")))
            
            response_str = json.dumps(llm_response, ensure_ascii=False)
            websockets.broadcast(connected_clients, response_str)
            logger.info(f"已广播给客户端")

    except websockets.exceptions.ConnectionClosed as e:
        logger.info(f"客户端断开连接: {e}")
    except Exception as e:
        logger.error(f"WebSocket 异常: {e}")
    finally:
        connected_clients.remove(websocket)

async def main():
    host = "127.0.0.1"
    port = 8765
    logger.info("Starting HTTP server on port 8080 for serving assets...")
    threading.Thread(target=start_http_server, daemon=True).start()
    logger.info(f"正在启动 WebSocket 交互服务器 ws://{host}:{port} ...")
    server = await websockets.serve(handle_client, host, port)
    await asyncio.Future()

if __name__ == "__main__":
    asyncio.run(main())
