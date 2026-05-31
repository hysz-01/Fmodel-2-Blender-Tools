# FModel_Tools/Fmodel/Pipeline/steps/step2_directory.py
# 步骤2: 选择项目目录

import bpy
import os


class PIPELINE_OT_WizardStep2(bpy.types.Operator):
    """向导步骤2: 选择项目目录"""
    bl_idname = "pipeline.wizard_step2"
    bl_label = "下一步: 扫描字典"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        if not hasattr(context.scene, "pipeline_wizard"):
            return False
        state = context.scene.pipeline_wizard
        # 检查目录是否已填写
        return bool(state.source_dir and state.output_dir and state.library_name)

    def execute(self, context):
        state = context.scene.pipeline_wizard

        # 验证目录存在
        source_dir = bpy.path.abspath(state.source_dir)
        if not os.path.exists(source_dir):
            self.report({'ERROR'}, f"项目目录不存在: {source_dir}")
            return {'CANCELLED'}

        # 确保输出目录存在（或创建）
        output_dir = bpy.path.abspath(state.output_dir)
        try:
            os.makedirs(output_dir, exist_ok=True)
        except Exception as e:
            self.report({'ERROR'}, f"创建输出目录失败: {e}")
            return {'CANCELLED'}

        state.current_step = 3
        return {'FINISHED'}


def register():
    bpy.utils.register_class(PIPELINE_OT_WizardStep2)


def unregister():
    bpy.utils.unregister_class(PIPELINE_OT_WizardStep2)
