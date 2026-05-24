import os
import argparse
import logging
from agent_tools import Generate3DModelTool, ConvertToFbxTool, UnityImportTool
from image_generator import ImageGeneratorTool
from bambu_tool import BambuPrinterTool

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("Main")

def main():
    parser = argparse.ArgumentParser(description="Nexus 3D - 6 Step Generation Pipeline")
    parser.add_argument("--prompt", type=str, required=False, help="Text prompt to generate 2D image and then 3D model")
    parser.add_argument("--input-file", type=str, required=False, help="Path to a local .obj, .3mf, or .glb file to convert directly")
    parser.add_argument("--unity-path", type=str, required=True, help="Absolute path to the Unity project")
    parser.add_argument("--blender-path", type=str, default="blender", help="Path to Blender executable")
    
    # 3D 打印相关参数
    parser.add_argument("--printer-ip", type=str, required=False, help="IP address of Bambu Printer on local network")
    parser.add_argument("--printer-code", type=str, required=False, help="LAN Access Code of Bambu Printer")
    
    args = parser.parse_args()

    if not args.prompt and not args.input_file:
        logger.error("You must provide either --prompt or --input-file")
        return

    # 初始化工具
    try:
        image_gen = ImageGeneratorTool()
        generator = Generate3DModelTool()
        converter = ConvertToFbxTool(blender_path=args.blender_path)
        importer = UnityImportTool(unity_project_path=args.unity_path)
        printer = BambuPrinterTool(printer_ip=args.printer_ip, access_code=args.printer_code)
    except Exception as e:
        logger.error(f"Initialization error: {e}")
        return

    # 工作流执行
    temp_img = "temp_image.jpg"
    temp_glb = "temp.glb"
    temp_fbx = "temp.fbx"
    temp_gcode = "temp.gcode"

    try:
        if args.input_file:
            logger.info(f"=== Step 1: Using Local Model: {args.input_file} ===")
            model_path = os.path.abspath(args.input_file)
            if not os.path.exists(model_path):
                raise FileNotFoundError(f"Input file not found: {model_path}")
        else:
            # Step 1: Text to 2D Image
            logger.info("=== Step 1: Text to 2D Image ===")
            img_path = image_gen.generate(prompt=args.prompt, output_path=temp_img)

            # Step 2: 2D Image to 3D Model
            logger.info("=== Step 2: 2D Image to 3D Model ===")
            model_path = generator.generate(image_path=img_path, output_path=temp_glb)
        
        # Step 3: Convert to FBX (For Virtual Avatar)
        logger.info("=== Step 3: Converting Format to FBX ===")
        fbx_path = converter.convert(input_model=model_path, output_fbx=temp_fbx)

        # Step 4: Import to Unity & Auto-Rig
        logger.info("=== Step 4: Importing to Unity (Virtual Realm) ===")
        final_path = importer.import_to_unity(source_fbx=fbx_path)
        
        # Step 5: Send to 3D Printer (Physical Realm)
        logger.info("=== Step 5: Sending to 3D Printer (Physical Realm) ===")
        gcode_path = printer.slice_model(input_model=model_path, output_gcode=temp_gcode)
        if args.printer_ip:
            printer.send_to_printer(gcode_path)
        else:
            logger.info("No printer IP provided. Skipping physical upload.")

        logger.info(f"=== Pipeline Completed Successfully ===")
        logger.info(f"Virtual Model deployed to: {final_path}")
        logger.info(f"Physical G-Code sliced to: {gcode_path}")
        logger.info("Step 6 (Brain & Voice AI) is running in the background via interactive_server.py")
        
    except Exception as e:
        logger.error(f"Pipeline failed: {e}")
    finally:
        # 清理临时文件 (只有当我们生成了临时文件时才清理)
        if not args.input_file and os.path.exists(temp_glb):
            os.remove(temp_glb)
        if os.path.exists(temp_img):
            os.remove(temp_img)
        if os.path.exists(temp_fbx):
            os.remove(temp_fbx)
        if os.path.exists(temp_gcode):
            os.remove(temp_gcode)

if __name__ == "__main__":
    main()
