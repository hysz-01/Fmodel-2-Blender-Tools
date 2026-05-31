# FModel_Tools/Assets/Models/ui.py
# 角色模型 UI — 属性和操作符（面板已移至 FModel_Tools/ui.py）

import bpy


class ModelAssetsProperties(bpy.types.PropertyGroup):
    """模型资产属性"""
    model_dir: bpy.props.StringProperty(name="模型目录", subtype='DIR_PATH')
    show_details: bpy.props.BoolProperty(name="高级", default=False)
    selected_model: bpy.props.StringProperty(name="选中模型")


class MODEL_OT_BrowseDir(bpy.types.Operator):
    """选择模型存储目录"""
    bl_idname = "fmodel.browse_model_dir"
    bl_label = "选择目录"
    bl_options = {'REGISTER', 'UNDO'}

    directory: bpy.props.StringProperty(subtype='DIR_PATH')

    def execute(self, context):
        if self.directory:
            context.scene.fmodel_model_assets.model_dir = self.directory
        return {'FINISHED'}

    def invoke(self, context, event):
        context.window_manager.fileselect_add(self)
        return {'RUNNING_MODAL'}


class MODEL_OT_SelectModel(bpy.types.Operator):
    """选中模型"""
    bl_idname = "fmodel.select_model"
    bl_label = "选中模型"
    bl_options = {'INTERNAL'}

    model_name: bpy.props.StringProperty()

    def execute(self, context):
        context.scene.fmodel_model_assets.selected_model = self.model_name
        return {'FINISHED'}


_classes = (
    ModelAssetsProperties,
    MODEL_OT_BrowseDir,
    MODEL_OT_SelectModel,
)


def register():
    for cls in _classes:
        bpy.utils.register_class(cls)
    bpy.types.Scene.fmodel_model_assets = bpy.props.PointerProperty(type=ModelAssetsProperties)


def unregister():
    del bpy.types.Scene.fmodel_model_assets
    for cls in reversed(_classes):
        bpy.utils.unregister_class(cls)
