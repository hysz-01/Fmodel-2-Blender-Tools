# FModel_Tools/Fmodel/Pipeline/steps/navigate.py
# 重置向导 + 步骤跳转

import bpy


class PIPELINE_OT_WizardReset(bpy.types.Operator):
    """重置向导"""
    bl_idname = "pipeline.wizard_reset"
    bl_label = "重新开始"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        state = context.scene.pipeline_wizard
        state.current_step = 1
        state.scan_completed = False
        state.import_completed = False
        state.lib_completed = False
        self.report({'INFO'}, "向导已重置")
        return {'FINISHED'}


class PIPELINE_OT_GotoStep(bpy.types.Operator):
    """跳转到指定步骤"""
    bl_idname = "pipeline.wizard_goto_step"
    bl_label = "跳转步骤"
    bl_options = {'REGISTER', 'UNDO'}

    target_step: bpy.props.IntProperty(name="目标步骤", default=1, min=1, max=4)

    def execute(self, context):
        state = context.scene.pipeline_wizard

        if self.target_step == 2 and not state.flow_type:
            self.report({'WARNING'}, "请先选择流程类型")
            return {'CANCELLED'}
        if self.target_step == 3 and not (state.source_dir and state.output_dir):
            self.report({'WARNING'}, "请先填写项目目录")
            return {'CANCELLED'}
        if self.target_step == 4 and not state.scan_completed:
            self.report({'WARNING'}, "请先执行扫描")
            return {'CANCELLED'}

        if self.target_step < state.current_step:
            if self.target_step <= 3:
                state.scan_completed = False
            if self.target_step <= 4:
                state.import_completed = False
                state.lib_completed = False

        state.current_step = self.target_step
        return {'FINISHED'}


def register():
    bpy.utils.register_class(PIPELINE_OT_WizardReset)
    bpy.utils.register_class(PIPELINE_OT_GotoStep)


def unregister():
    bpy.utils.unregister_class(PIPELINE_OT_GotoStep)
    bpy.utils.unregister_class(PIPELINE_OT_WizardReset)
