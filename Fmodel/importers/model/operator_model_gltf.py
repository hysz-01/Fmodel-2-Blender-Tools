# FModel_Tools/Fmodel/importers/model/operator_model_gltf.py
# glTF 模型导入 — 支持自动修复骨骼、形态键、材质链接

import bpy
import os
from bpy_extras.io_utils import ImportHelper
from ....Universal_tools.Animations import utils_anim
from ....Universal_tools import material as mat_module
from ....Universal_tools.mesh import scheme_morph_merge
from ....Universal_tools.skeleton import scheme_auto


class MODEL_OT_ImportGLTF(bpy.types.Operator, ImportHelper):
    """导入 glTF 模型并自动修复"""
    bl_idname = "fmodel.import_model_gltf"
    bl_label = "导入 glTF 模型"
    bl_options = {'REGISTER', 'UNDO'}

    filename_ext = ".glb;.gltf"
    filter_glob: bpy.props.StringProperty(default="*.glb;*.gltf", options={'HIDDEN'}) # type: ignore

    fix_bones: bpy.props.BoolProperty(name="自动对齐 UE 骨骼", default=True) # type: ignore
    transfer_anim: bpy.props.BoolProperty(name="无损重定向动画", default=True) # type: ignore
    clean_old_anim: bpy.props.BoolProperty(name="清理缓存", default=True) # type: ignore
    merge_morphs: bpy.props.BoolProperty(name="自动合并形态键", default=False) # type: ignore

    delete_end_bones: bpy.props.BoolProperty(name="清理无贡献骨骼", default=True) # type: ignore
    ignore_end_bones: bpy.props.BoolProperty(name="忽略 End 骨骼", default=True) # type: ignore
    use_adaptive_length: bpy.props.BoolProperty(name="自适应骨骼长度", default=True) # type: ignore
    search_subfolders: bpy.props.BoolProperty(name="包含子文件夹", default=False) # type: ignore

    auto_link_mat: bpy.props.BoolProperty(name="导入后自动链接材质", default=True) # type: ignore

    def draw(self, context):
        layout = self.layout
        box_main = layout.box()
        box_main.label(text="glTF 导入配置", icon='PREFERENCES')
        
        box_main.prop(self, "fix_bones", icon='BONE_DATA')
        if self.fix_bones:
            col = box_main.column()
            row_anim = col.row()
            row_anim.separator(factor=2)
            row_anim.prop(self, "transfer_anim", icon='ANIM_DATA')
            if self.transfer_anim:
                row_clean = col.row()
                row_clean.separator(factor=4)
                row_clean.prop(self, "clean_old_anim", text="清理缓存并恢复原名", icon='BRUSH_DATA')
                
        box_main.separator(factor=0.5)
        box_main.prop(self, "merge_morphs", icon='SHAPEKEY_DATA')
        
        if self.fix_bones:
            box_bone = layout.box()
            box_bone.label(text="UE 骨骼校准规则", icon='MODIFIER')
            col = box_bone.column(align=True)
            col.prop(self, "delete_end_bones")
            col.prop(self, "ignore_end_bones")
            col.prop(self, "use_adaptive_length")

        if self.merge_morphs:
            box_morph = layout.box()
            box_morph.label(text="形态键合并规则", icon='MESH_DATA')
            box_morph.prop(self, "search_subfolders")

        box_mat = layout.box()
        box_mat.label(text="材质自动处理", icon='NODE_MATERIAL')
        box_mat.prop(self, "auto_link_mat")

    def invoke(self, context, event):
        props = context.scene.fmodel_core
        self.fix_bones = props.fix_bones
        self.transfer_anim = props.transfer_anim
        self.clean_old_anim = props.clean_old_anim
        self.merge_morphs = props.merge_morphs

        self.delete_end_bones = props.props_auto.delete_end_bones
        self.ignore_end_bones = props.props_auto.ignore_end_bones
        self.use_adaptive_length = props.props_auto.use_adaptive_length
        self.search_subfolders = props.props_morph_merge.search_subfolders

        context.window_manager.fileselect_add(self)
        return {'RUNNING_MODAL'}

    def execute(self, context):
        props = context.scene.fmodel_core
        props.fix_bones = self.fix_bones
        props.transfer_anim = self.transfer_anim
        props.clean_old_anim = self.clean_old_anim
        props.merge_morphs = self.merge_morphs

        props.props_auto.delete_end_bones = self.delete_end_bones
        props.props_auto.ignore_end_bones = self.ignore_end_bones
        props.props_auto.use_adaptive_length = self.use_adaptive_length
        props.props_morph_merge.search_subfolders = self.search_subfolders

        safe_path = os.path.normpath(self.filepath)

        old_objs = set(context.scene.objects)
        try:
            bpy.ops.import_scene.gltf(filepath=safe_path, bone_heuristic='TEMPERANCE')
        except Exception as e:
            self.report({'ERROR'}, f"基础导入失败: {e}")
            return {'CANCELLED'}

        new_objs = list(set(context.scene.objects) - old_objs)
        for obj in new_objs: obj["gltf_import_path"] = safe_path

        armatures = [o for o in new_objs if o.type == 'ARMATURE']
        meshes = [o for o in new_objs if o.type == 'MESH']

        try:
            from ....Assets.Utils import utils_asset
            json_path = os.path.splitext(safe_path)[0] + ".json"
            ue_sk_name = utils_asset.get_skeleton_name_from_json(json_path)
            if ue_sk_name:
                for arm in armatures:
                    arm["FModel_Skeleton"] = ue_sk_name
        except Exception as e:
            print(f"[FModel GLTF] 骨架真实属性写入失败: {e}")
            # 使用日志系统
            from ....core import log_error
            log_error("IMPORT_GLTTF", f"骨架真实属性写入失败: {e}")

        for arm in armatures:
            if self.fix_bones:
                has_anim = arm.animation_data and (arm.animation_data.action or arm.animation_data.nla_tracks)
                if has_anim and self.transfer_anim:
                    temp_arm = None
                    try:
                        bpy.ops.object.select_all(action='DESELECT')
                        arm.select_set(True)
                        bpy.context.view_layer.objects.active = arm
                        bpy.ops.object.duplicate()
                        temp_arm = bpy.context.active_object
                        
                        bpy.context.view_layer.objects.active = arm
                        scheme_auto.execute(context, context.scene.fmodel_core.props_auto)
                        
                        utils_anim.transfer_all_animations(temp_arm, arm, clean_old=self.clean_old_anim)
                    finally:
                        if temp_arm:
                            temp_data = temp_arm.data
                            try:
                                bpy.data.objects.remove(temp_arm, do_unlink=True)
                                if temp_data and temp_data.users == 0:
                                    bpy.data.armatures.remove(temp_data)
                            except: pass
                else:
                    bpy.context.view_layer.objects.active = arm
                    scheme_auto.execute(context, context.scene.fmodel_core.props_auto)

        if self.auto_link_mat:
            try:
                mat_module.auto_resolve_materials_for_import(meshes, self.filepath)
            except Exception as e:
                print(f"[FModel] 自动材质解析失败: {e}")

        if self.merge_morphs:
            for mesh_obj in meshes:
                bpy.context.view_layer.objects.active = mesh_obj
                scheme_morph_merge.execute(context, context.scene.fmodel_core.props_morph_merge)

        if props.purge_orphans:
            utils_anim.deep_purge_orphans()

        self.report({'INFO'}, "glTF 模型导入修复完成")
        return {'FINISHED'}


def register():
    bpy.utils.register_class(MODEL_OT_ImportGLTF)


def unregister():
    bpy.utils.unregister_class(MODEL_OT_ImportGLTF)
