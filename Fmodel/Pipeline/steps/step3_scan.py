# FModel_Tools/Fmodel/Pipeline/steps/step3_scan.py
# 步骤3: 扫描字典

import bpy

from ....core import DictionaryManifest, PipelineContext, PipelineStage
from .runner import run_wizard_stage


class PIPELINE_OT_WizardStep3(bpy.types.Operator):
    """向导步骤3: 扫描字典"""
    bl_idname = "pipeline.wizard_step3"
    bl_label = "扫描字典"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        if not hasattr(context.scene, "pipeline_wizard"):
            return False
        state = context.scene.pipeline_wizard
        return state.source_dir and state.output_dir

    def execute(self, context):
        state = context.scene.pipeline_wizard
        ok_stage1 = run_wizard_stage(context, state, PipelineStage.DICTIONARY_ACQUISITION.value)
        if not ok_stage1:
            self.report({'ERROR'}, "扫描失败：字典阶段未通过")
            return {'CANCELLED'}

        ok_stage2 = run_wizard_stage(context, state, PipelineStage.FORMAT_CONVERSION.value)
        if not ok_stage2:
            self.report({'ERROR'}, "扫描失败：格式中转阶段未通过")
            return {'CANCELLED'}

        pipeline_context = PipelineContext.load_from_blender_text()
        if not pipeline_context or not pipeline_context.dictionary_manifest:
            self.report({'ERROR'}, "扫描失败：未生成字典清单")
            return {'CANCELLED'}

        manifest = DictionaryManifest.from_dict(pipeline_context.dictionary_manifest)
        anim_total = len(manifest.get_all_animations())
        skeleton_total = len(manifest.skeletons)

        state.scan_skeleton_count = skeleton_total
        state.scan_anim_count = anim_total
        state.scan_new_count = anim_total
        state.scan_existing_count = 0
        state.scan_completed = True

        if state.flow_type == 'FMODEL':
            self.report({'INFO'}, f"扫描完成: {anim_total} 个动画, {skeleton_total} 个骨架")
        else:
            self.report({'INFO'}, f"扫描完成: {anim_total} 个动画")

        return {'FINISHED'}


def register():
    bpy.utils.register_class(PIPELINE_OT_WizardStep3)


def unregister():
    bpy.utils.unregister_class(PIPELINE_OT_WizardStep3)
