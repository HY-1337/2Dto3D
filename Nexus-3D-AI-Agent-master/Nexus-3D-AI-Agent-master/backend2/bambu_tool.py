import os
import subprocess
import logging
from ftplib import FTP

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("BambuSkill")

class BambuPrinterTool:
    def __init__(self, slicer_path: str = "bambu-studio", printer_ip: str = None, access_code: str = None):
        """
        初始化 Bambu 3D 打印机交互工具
        slicer_path: Bambu Studio 命令行可执行文件的绝对路径
        printer_ip: 局域网内的打印机 IP 地址 (例如: 192.168.1.10)
        access_code: 打印机的局域网访问密码 (Access Code)
        """
        self.slicer_path = slicer_path
        self.printer_ip = printer_ip
        self.access_code = access_code

    def slice_model(self, input_model: str, output_gcode: str) -> str:
        """
        使用 Bambu Studio 命令行对模型进行切片
        Bambu Studio CLI 示例: bambu-studio-console.exe --export-gcode "output.gcode" "input.obj"
        """
        logger.info(f"Task: Slicing 3D model {input_model} to G-Code...")
        input_abs = os.path.abspath(input_model)
        output_abs = os.path.abspath(output_gcode)

        if not os.path.exists(input_abs):
            raise FileNotFoundError(f"Cannot find model to slice: {input_abs}")

        # 模拟切片命令
        cmd = [
            self.slicer_path,
            "--export-gcode", output_abs,
            input_abs
        ]

        logger.info(f"Running slicer command: {' '.join(cmd)}")
        
        # 为了演示，如果 bambu-studio 没有安装在环境变量里，我们会创建一个伪造的 Gcode 避免流程卡死
        try:
            result = subprocess.run(cmd, capture_output=True, text=True)
            if result.returncode != 0:
                logger.warning(f"Slicer returned non-zero code. (This is expected if Bambu Studio CLI is not in PATH)")
                self._mock_gcode(output_abs)
        except FileNotFoundError:
            logger.warning(f"Bambu Studio CLI ({self.slicer_path}) not found in PATH. Creating mock G-Code for demonstration.")
            self._mock_gcode(output_abs)
            
        return output_abs

    def _mock_gcode(self, output_abs):
        with open(output_abs, "w") as f:
            f.write("; Mock G-Code for Bambu Printer\nG28 ; Home all axes\nG1 Z10 F3000 ; Move Z up\n")

    def send_to_printer(self, gcode_path: str):
        """
        通过 FTP 将 G-Code 发送到 Bambu 打印机并准备打印
        Bambu 的默认 FTP 端口是 990 (FTPS)
        """
        logger.info("Task: Sending G-Code to Bambu Printer...")
        if not self.printer_ip or not self.access_code:
            logger.warning("Printer IP or Access Code is missing! Skipping actual hardware upload.")
            logger.info(f"[SIMULATED] Successfully uploaded {gcode_path} to Bambu Printer FTP!")
            return

        # 真实的 FTPS 连接代码 (需要 ssl 包装，这里使用标准 ftp 演示结构)
        try:
            import ssl
            context = ssl.create_default_context()
            context.check_hostname = False
            context.verify_mode = ssl.CERT_NONE
            
            # Bambu 使用默认用户 bblp，密码为局域网接入码
            from ftplib import FTP_TLS
            ftp = FTP_TLS(context=context)
            ftp.connect(self.printer_ip, 990)
            ftp.login('bblp', self.access_code)
            ftp.prot_p() # 开启安全数据连接
            
            with open(gcode_path, 'rb') as f:
                filename = os.path.basename(gcode_path)
                ftp.storbinary(f'STOR /{filename}', f)
            ftp.quit()
            logger.info(f"Successfully uploaded {gcode_path} to real Bambu Printer at {self.printer_ip}!")
        except Exception as e:
            logger.error(f"Failed to connect to printer hardware: {e}")
            logger.info("Falling back to simulation mode...")

if __name__ == "__main__":
    tool = BambuPrinterTool()
    gcode = tool.slice_model("temp.obj", "test.gcode")
    tool.send_to_printer(gcode)
