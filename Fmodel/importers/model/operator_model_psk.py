# FModel_Tools/Fmodel/importers/model/operator_model_psk.py
# PSK 模型导入 — 支持自动网格修复与材质链接

import bpy
import os
from bpy_extras.io_utils import ImportHelper
from ....Universal_tools.Animations import utils_anim
from ....Universal_tools import material as mat_module
from ....Universal_tools.mesh import scheme_psk_mesh_fix


class MODEL_OT_ImportPSK(bpy.types.Operator, ImportHelper):
    """导入 PSK 模型"""
    bl_idname = "fmodel.import_model_psk"
    bl_label = "导入 PSK 模型"
    bl_options = {'REGISTER', 'UNDO'}
    
    filename_ext = ".psk;.pskx"
    filter_glob: bpy.props.StringProperty(default="*.psk;*.pskx", options={'HIDDEN'}) # type: ignore

    import_scale: bpy.props.FloatProperty(name="模型缩放 (Scale)", default=0.01, min=0.0001, max=100.0) # type: ignore
    bone_length: bpy.props.FloatProperty(name="基础骨骼长度", default=1.0, min=0.001, max=100.0) # type: ignore
    fix_meshes: bpy.props.BoolProperty(name="导入后自动修复网格撕裂", default=True) # type: ignore
    auto_link_mat: bpy.props.BoolProperty(name="自动查找并链接材质", default=True) # type: ignore

    def invoke(self, context, event):
        self.fix_meshes = context.scene.fmodel_core.fix_meshes
        context.window_manager.fileselect_add(self)
        return {'RUNNING_MODAL'}

    def execute(self, context):
        context.scene.fmodel_core.fix_meshes = self.fix_meshes
        
        safe_path = os.path.normpath(self.filepath)
        import_kwargs = { 'filepath': safe_path, 'scale': self.import_scale, 'bone_length': self.bone_length }
        
        old_objs = set(context.scene.objects)
        try:
            # 根据参考插件 io_scene_psk_psa，正确的操作符是 psk.import_file
            if hasattr(bpy.ops.psk, "import_file"):
                bpy.ops.psk.import_file(**import_kwargs)
            else:
                self.report({'ERROR'}, "找不到 PSK 导入命令 (需要 io_scene_psk_psa 插件)")
                return {'CANCELLED'}
        except Exception as e:
            self.report({'ERROR'}, f"PSK 导入失败: {e}")
            return {'CANCELLED'}
            
        new_objs = list(set(context.scene.objects) - old_objs)
        meshes = [o for o in new_objs if o.type == 'MESH']
        armatures = [o for o in new_objs if o.type == 'ARMATURE']
        
        for obj in new_objs: obj["gltf_import_path"] = safe_path
           
        try:
            from ....Assets.Utils import utils_asset
            json_path = os.path.splitext(safe_path)[0] + ".json"
            ue_sk_name = utils_asset.get_skeleton_name_from_json(json_path)
            if ue_sk_name:
                for arm in armatures:
                    arm["FModel_Skeleton"] = ue_sk_name
        except Exception as e:
            print(f"[FModel PSK] 骨架真实属性写入失败: {e}")
            # 使用日志系统
            from ....core import log_error
            log_error("IMPORT_PSK", f"骨架真实属性写入失败: {e}")
            
        if meshes and self.fix_meshes:
            for mesh_obj in meshes:
                bpy.context.view_layer.objects.active = mesh_obj
                scheme_psk_mesh_fix.execute(context, context.scene.fmodel_core.props_psk_mesh_fix)
            
        if context.scene.fmodel_core.purge_orphans:
            utils_anim.deep_purge_orphans()

        self.report({'INFO'}, "PSK 模型已导入！")
        
        if self.auto_link_mat:
            try:
                mat_module.auto_resolve_materials_for_import(meshes, self.filepath)
            except Exception as e:
                print(f"[FModel] 自动材质解析失败: {e}")
                
        return {'FINISHED'}


def register():
    bpy.utils.register_class(MODEL_OT_ImportPSK)


def unregister():
    bpy.utils.unregister_class(MODEL_OT_ImportPSK)
