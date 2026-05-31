# FModel_Tools/Assets/Utils/link_existing_library.py
# 库链接 — 关联已有资产库目录
import bpy
import os

class FMODEL_OT_link_existing_library(bpy.types.Operator):
    bl_idname = "fmodel.link_existing_library"
    bl_label = "直连现有资产库"
    bl_options = {'REGISTER', 'UNDO'}
    
    directory: bpy.props.StringProperty(name="库目录", subtype='DIR_PATH') # type: ignore
    
    def invoke(self, context, event):
        # 唤起系统文件夹选择器
        context.window_manager.fileselect_add(self)
        return {'RUNNING_MODAL'}
        
    def execute(self, context):
        if not self.directory or not os.path.exists(self.directory):
            return {'CANCELLED'}
            
        # 嗅探该文件夹是否是合法的 FModel 资产库
        has_manifest = any(f.endswith("_manifest.json") for f in os.listdir(self.directory))
        if not has_manifest:
            self.report({'ERROR'}, "⛔ 未检测到清单文件 (_manifest.json)，请选择之前打包好的资产库根目录！")
            return {'CANCELLED'}
            
        props = context.scene.fmodel_assets
        
        # ⭐ 跨盘符容错机制：尝试获取相对路径，如果跨硬盘则降级使用绝对路径
        try:
            rel_dir = bpy.path.relpath(self.directory)
        except ValueError:
            rel_dir = self.directory
        
        # 查重：避免重复添加
        exists = False
        existing_lib = None
        for lib in props.project_libs:
            if bpy.path.abspath(lib.path) == bpy.path.abspath(self.directory):
                exists = True
                existing_lib = lib
                break
                
        if not exists:
            new_lib = props.project_libs.add()
            new_lib.name = os.path.basename(os.path.normpath(self.directory))
            new_lib.path = rel_dir
            existing_lib = new_lib
            
        # 调用核心函数挂载至全局并扫描
        from . import utils_asset
        utils_asset.mount_dynamic_library(existing_lib.name, self.directory)
        bpy.ops.fmodel.scan_anims()
        
        self.report({'INFO'}, f"✅ 成功跨工程加载资产库: {existing_lib.name}")
        return {'FINISHED'}

def register():
    bpy.utils.register_class(FMODEL_OT_link_existing_library)

def unregister():
    bpy.utils.unregister_class(FMODEL_OT_link_existing_library)