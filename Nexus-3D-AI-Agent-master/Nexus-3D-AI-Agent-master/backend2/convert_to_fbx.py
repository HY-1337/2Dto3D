import bpy
import sys
import os

def clear_scene():
    """清理默认场景中的所有物体"""
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete(use_global=False)
    
    # 清理孤立的数据块
    for block in bpy.data.meshes:
        if block.users == 0:
            bpy.data.meshes.remove(block)
    for block in bpy.data.materials:
        if block.users == 0:
            bpy.data.materials.remove(block)
    for block in bpy.data.textures:
        if block.users == 0:
            bpy.data.textures.remove(block)
    for block in bpy.data.images:
        if block.users == 0:
            bpy.data.images.remove(block)

def main():
    # 提取 '--' 之后的参数
    argv = sys.argv
    if '--' not in argv:
        print("Error: '--' separator not found in arguments.")
        sys.exit(1)
        
    args = argv[argv.index('--') + 1:]
    if len(args) < 2:
        print("Usage: blender -b -P convert_to_fbx.py -- <input.glb> <output.fbx>")
        sys.exit(1)
        
    input_model = args[0]
    output_fbx = args[1]
    
    print(f"Starting conversion: {input_model} -> {output_fbx}")
    
    # 清理默认场景
    clear_scene()
    
    # 根据后缀名导入模型
    ext = os.path.splitext(input_model)[1].lower()
    try:
        if ext in ['.glb', '.gltf']:
            bpy.ops.import_scene.gltf(filepath=input_model)
        elif ext == '.obj':
            # Blender 3.2+ 推荐 wm.obj_import
            if hasattr(bpy.ops.wm, 'obj_import'):
                bpy.ops.wm.obj_import(filepath=input_model)
            else:
                bpy.ops.import_scene.obj(filepath=input_model)
        elif ext == '.3mf':
            if hasattr(bpy.ops.wm, 'threemf_import'):
                bpy.ops.wm.threemf_import(filepath=input_model)
            elif hasattr(bpy.ops.import_mesh, 'threemf'):
                bpy.ops.import_mesh.threemf(filepath=input_model)
            else:
                print(f"Failed to import {ext}: 3MF importer not found in this Blender version.")
                sys.exit(1)
        else:
            print(f"Unsupported file format: {ext}")
            sys.exit(1)
            
        print(f"{ext.upper()} imported successfully.")
    except Exception as e:
        print(f"Failed to import {ext}: {e}")
        sys.exit(1)
        
    # 导出 FBX
    # 使用比较通用的导出参数，以确保兼容 Unity
    try:
        bpy.ops.export_scene.fbx(
            filepath=output_fbx,
            use_selection=False,
            global_scale=1.0,
            apply_unit_scale=True,
            apply_scale_options='FBX_SCALE_ALL',
            object_types={'MESH', 'ARMATURE'},
            use_mesh_modifiers=True,
            mesh_smooth_type='FACE',
            path_mode='COPY',     # 关键：将贴图打包到 FBX 中，或者在导入 Unity 时自动提取
            embed_textures=True   # 关键：将贴图打包进 FBX
        )
        print("FBX exported successfully.")
    except Exception as e:
        print(f"Failed to export FBX: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
