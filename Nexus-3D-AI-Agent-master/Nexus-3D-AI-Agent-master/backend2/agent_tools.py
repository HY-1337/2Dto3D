import os
import time
import requests
import subprocess
import shutil
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("3DAgent")

class Generate3DModelTool:
    def __init__(self, api_key: str = None):
        self.api_key = api_key or os.environ.get("TRIPO_API_KEY")
        if not self.api_key:
            logger.warning("No TRIPO_API_KEY found! Please set it in environment variables.")
        self.base_url = "https://api.tripo3d.ai/v2/openapi/task"
        self.upload_url = "https://api.tripo3d.ai/v2/openapi/upload"
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

    def upload_image(self, image_path: str) -> str:
        """上传图片到 Tripo3D 获取 token"""
        logger.info(f"Uploading image {image_path} to Tripo3D...")
        if not os.path.exists(image_path):
            raise FileNotFoundError(f"Image not found: {image_path}")
            
        # 注意上传接口不需要 Content-Type，requests 会自动处理 multipart/form-data
        upload_headers = {"Authorization": f"Bearer {self.api_key}"}
        
        with open(image_path, "rb") as f:
            files = {"file": (os.path.basename(image_path), f, "image/jpeg")}
            res = requests.post(self.upload_url, headers=upload_headers, files=files)
            res.raise_for_status()
            data = res.json()
            if data.get("code") != 0:
                raise Exception(f"Tripo Image Upload Failed: {data.get('msg')}")
            return data.get("data", {}).get("image_token")

    def generate(self, prompt: str = None, image_path: str = None, output_path: str = "temp.glb") -> str:
        """
        根据文本或图像使用 Tripo3D 生成 3D 模型并下载为 GLB 格式
        如果提供了 image_path，则优先使用 image_to_model (2D转3D)
        """
        if not self.api_key:
            raise ValueError("TRIPO_API_KEY is missing.")

        payload = {}
        if image_path:
            logger.info(f"Task: Image to 3D. Image: '{image_path}'")
            image_token = self.upload_image(image_path)
            payload = {
                "type": "image_to_model",
                "file": {
                    "type": "jpg",
                    "file_token": image_token
                }
            }
        elif prompt:
            logger.info(f"Task: Text to 3D. Prompt: '{prompt}'")
            payload = {
                "type": "text_to_model",
                "prompt": prompt
            }
        else:
            raise ValueError("Must provide either prompt or image_path")
        
        # 1. 提交任务
        response = requests.post(self.base_url, headers=self.headers, json=payload)
        response.raise_for_status()
        data = response.json()
        if data.get("code") != 0:
            raise Exception(f"Tripo Task Creation Failed: {data.get('msg')}")
        
        # Tripo v2 API 结构中通常在 data['data']['task_id']
        task_id = data.get("data", {}).get("task_id")
        logger.info(f"Task created successfully. Task ID: {task_id}")

        # 2. 轮询任务状态
        task_url = f"{self.base_url}/{task_id}"
        model_url = None
        while True:
            res = requests.get(task_url, headers=self.headers)
            res.raise_for_status()
            status_response = res.json()
            
            if status_response.get("code") != 0:
                raise Exception(f"Tripo Polling Failed: {status_response.get('msg')}")
                
            task_data = status_response.get("data", {})
            status = task_data.get("status")
            
            if status == "success":
                # 获取下载链接
                model_url = task_data.get("output", {}).get("pbr_model") or task_data.get("result", {}).get("model", {}).get("url")
                if not model_url:
                    model_url = task_data.get("result", {}).get("pbr_model", {}).get("url")
                logger.info("Generation succeeded!")
                break
            elif status in ["failed", "cancelled"]:
                raise Exception(f"Generation failed: {status}")
            else:
                progress = task_data.get("progress", 0)
                logger.info(f"Status: {status} ({progress}%)... waiting 5 seconds.")
                time.sleep(5)

        # 3. 提交自动绑骨任务 (Auto-Rigging with Mixamo spec)
        if model_url:
            logger.info("Submitting auto-rigging task for the generated model...")
            rig_payload = {
                "type": "animate_rig",
                "original_model_task_id": task_id,
                "rig_type": "biped",
                "spec": "mixamo",
                "out_format": "glb"
            }
            rig_res = requests.post(self.base_url, headers=self.headers, json=rig_payload)
            rig_res.raise_for_status()
            rig_data = rig_res.json()
            if rig_data.get("code") != 0:
                logger.error(f"Rig task failed, fallback to original model. MSG: {rig_data.get('msg')}")
                rigged_model_url = model_url # 回退到无骨骼模型
            else:
                rig_task_id = rig_data.get("data", {}).get("task_id")
                logger.info(f"Rig task created successfully. Task ID: {rig_task_id}")
                
                # 轮询绑骨任务
                rig_task_url = f"{self.base_url}/{rig_task_id}"
                rigged_model_url = None
                while True:
                    r_res = requests.get(rig_task_url, headers=self.headers)
                    r_res.raise_for_status()
                    r_status = r_res.json()
                    
                    if r_status.get("code") != 0:
                        logger.error(f"Rig polling failed. MSG: {r_status.get('msg')}")
                        rigged_model_url = model_url
                        break
                        
                    r_data = r_status.get("data", {})
                    r_state = r_data.get("status")
                    
                    if r_state == "success":
                        # 获取带骨架的模型下载链接
                        rigged_model_url = r_data.get("output", {}).get("model") or r_data.get("result", {}).get("model", {}).get("url")
                        if not rigged_model_url:
                            rigged_model_url = model_url # fallback
                        logger.info("Rigging succeeded!")
                        break
                    elif r_state in ["failed", "cancelled"]:
                        logger.warning(f"Rigging failed with state {r_state}, fallback to original model.")
                        rigged_model_url = model_url
                        break
                    else:
                        progress = r_data.get("progress", 0)
                        logger.info(f"Rigging Status: {r_state} ({progress}%)... waiting 5 seconds.")
                        time.sleep(5)

            # 4. 下载模型
            logger.info(f"Downloading rigged model from {rigged_model_url}...")
            model_res = requests.get(rigged_model_url)
            model_res.raise_for_status()
            with open(output_path, "wb") as f:
                f.write(model_res.content)
            logger.info(f"Rigged Model saved to {output_path}")
            return os.path.abspath(output_path)
        else:
            raise Exception("Model URL not found in response.")


class ConvertToFbxTool:
    def __init__(self, blender_path: str = "blender"):
        # 如果 blender 不在系统 PATH 中，需要传入 blender 绝对路径
        self.blender_path = blender_path
        self.script_path = os.path.abspath("convert_to_fbx.py")

    def convert(self, input_model: str, output_fbx: str) -> str:
        """
        使用 Blender headless 模式将模型转为 FBX
        """
        logger.info(f"Task: Format Conversion. {input_model} -> FBX")
        input_abs = os.path.abspath(input_model)
        output_abs = os.path.abspath(output_fbx)

        if not os.path.exists(input_abs):
            raise FileNotFoundError(f"Input model file not found: {input_abs}")

        cmd = [
            self.blender_path,
            "-b",  # headless mode
            "-P", self.script_path,
            "--",  # 分隔符，传递给 python 脚本的参数
            input_abs,
            output_abs
        ]

        logger.info(f"Running command: {' '.join(cmd)}")
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode != 0:
            logger.error(f"Blender conversion failed:\n{result.stderr}")
            raise Exception("Blender conversion failed.")
        
        if not os.path.exists(output_abs):
            raise FileNotFoundError("Output FBX was not created by Blender.")

        logger.info(f"Conversion successful. Saved to {output_abs}")
        return output_abs


class UnityImportTool:
    def __init__(self, unity_project_path: str):
        self.unity_models_dir = os.path.join(unity_project_path, "Assets", "Models", "AutoGenerated")
        os.makedirs(self.unity_models_dir, exist_ok=True)

    def import_to_unity(self, source_fbx: str) -> str:
        """
        将生成的 FBX 移动到 Unity 的特定目录下，触发 Unity 自动导入
        """
        logger.info(f"Task: Unity Import")
        if not os.path.exists(source_fbx):
            raise FileNotFoundError(f"Source FBX not found: {source_fbx}")

        filename = os.path.basename(source_fbx)
        dest_path = os.path.join(self.unity_models_dir, filename)

        # 移动文件（为了安全也可以用 copy）
        shutil.copy2(source_fbx, dest_path)
        logger.info(f"Model copied to Unity project: {dest_path}")
        logger.info("Switch back to Unity Editor to trigger AssetPostprocessor.")
        
        return dest_path
