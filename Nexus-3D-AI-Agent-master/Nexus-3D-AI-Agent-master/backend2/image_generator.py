import os
import requests
import urllib.parse
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("ImageGen")

class ImageGeneratorTool:
    def __init__(self):
        # We use Pollinations.ai because it provides free, open-source stable diffusion models without API keys.
        self.base_url = "https://image.pollinations.ai/prompt/"

    def generate(self, prompt: str, output_path: str = "temp_image.jpg") -> str:
        """
        根据文本提示词生成 2D 图像并保存到本地
        """
        logger.info(f"Task: Text to 2D Image. Prompt: '{prompt}'")
        
        # 将提示词进行 URL 编码
        encoded_prompt = urllib.parse.quote(prompt)
        
        # 加上一些质量控制的词
        full_url = f"{self.base_url}{encoded_prompt}?width=1024&height=1024&nologo=true&enhance=true"
        
        try:
            logger.info("正在生成图片，可能需要几秒钟...")
            response = requests.get(full_url)
            response.raise_for_status()
            
            with open(output_path, "wb") as f:
                f.write(response.content)
                
            logger.info(f"图片生成成功，已保存至: {os.path.abspath(output_path)}")
            return os.path.abspath(output_path)
            
        except Exception as e:
            logger.error(f"生成图片时发生错误: {e}")
            raise Exception(f"图片生成失败: {e}")

if __name__ == "__main__":
    tool = ImageGeneratorTool()
    tool.generate("A beautiful cyber ninja humanoid character, detailed 3d render")
