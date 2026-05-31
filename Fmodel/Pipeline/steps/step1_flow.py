# FModel_Tools/Fmodel/Pipeline/steps/step1_flow.py
# 步骤1: 选择流程

import bpy


class PIPELINE_OT_WizardStep1(bpy.types.Operator):
    """向导步骤1: 选择流程"""
    bl_idname = "pipeline.wizard_step1"
    bl_label = "选择流程"
    bl_options = {'REGISTER', 'UNDO'}

    flow: bpy.props.EnumProperty(
        items=[
            ('FMODEL', "FModel", ""),
            ('UNITY', "Unity", ""),
        ]
    )

    def execute(self, context):
        state = context.scene.pipeline_wizard
        state.flow_type = self.flow
        state.current_step = 2
        # 重置后续步骤
        state.scan_completed = False
        state.import_completed = False
        state.lib_completed = False
        return {'FINISHED'}


def register():
    bpy.utils.register_class(PIPELINE_OT_WizardStep1)


def unregister():
    bpy.utils.unregister_class(PIPELINE_OT_WizardStep1)
