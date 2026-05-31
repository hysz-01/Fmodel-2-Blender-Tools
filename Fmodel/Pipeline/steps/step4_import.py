# FModel_Tools/Fmodel/Pipeline/steps/step4_import.py
# 步骤4: 导入动画 + 建立资产库 (合并原步骤4/5)

import bpy

from ....core import PipelineStage
from .runner import run_wizard_stage


class PIPELINE_OT_WizardStep4(bpy.types.Operator):
    """向导步骤4: 导入动画并建立资产库"""
    bl_idname = "pipeline.wizard_step4"
    bl_label = "导入并打包"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        if not hasattr(context.scene, "pipeline_wizard"):
            return False
        state = context.scene.pipeline_wizard
        obj = context.active_object
        return state.scan_completed and obj and obj.type == 'ARMATURE'

    def execute(self, context):
        state = context.scene.pipeline_wizard

        obj = context.active_object
        if not obj or obj.type != 'ARMATURE':
            self.report({'ERROR'}, "请先选中目标骨架")
            return {'CANCELLED'}

        state.import_target_skeleton = obj.name

        # Save model BEFORE import (avoid contamination from last imported anim)
        out_dir = bpy.path.abspath(state.output_dir)
        if state.lib_save_model:
            try:
                from ....Assets.Models.operators import save_model_logic
                save_model_logic(obj, out_dir, state.library_name, state.lib_model_preview)
            except Exception:
                pass

        # Stage 4: Import
        success = run_wizard_stage(context, state, PipelineStage.ASSET_IMPORT.value)
        if not success:
            self.report({'ERROR'}, "导入失败，请查看日志")
            return {'CANCELLED'}

        # Post-import cleanup
        cleaned_count = 0
        if state.clean_after_import:
            from ....Universal_tools.Animations.clean_Anim import clean_action
            for action in list(bpy.data.actions):
                if "Pipeline_Skeleton" not in action:
                    continue
                try:
                    stats = clean_action(action, threshold=state.clean_threshold,
                                         clean_channels=True, clean_flat=state.clean_flat_channels)
                    if stats.get('removed_keyframes', 0) > 0:
                        cleaned_count += 1
                except Exception:
                    pass

        state.import_completed = True

        # Stage 5: Build library + thumbnails
        ok_build = run_wizard_stage(context, state, PipelineStage.LIBRARY_BUILDING.value)
        if not ok_build:
            self.report({'ERROR'}, "资产库构建失败，请查看日志")
            return {'CANCELLED'}
        ok_final = run_wizard_stage(context, state, PipelineStage.FINALIZATION.value)
        if not ok_final:
            self.report({'ERROR'}, "资产库后处理失败，请查看日志")
            return {'CANCELLED'}

        state.lib_completed = True
        msg = "导入并打包完成"
        if cleaned_count > 0:
            msg += f"，已清理 {cleaned_count} 个动作"
        self.report({'INFO'}, msg)
        return {'FINISHED'}

    def draw(self, context):
        pass


class PIPELINE_OT_RebakeThumbnails(bpy.types.Operator):
    """仅重新生成缩略图，不重新导入动画"""
    bl_idname = "pipeline.rebake_thumbnails"
    bl_label = "重新生成缩略图"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        if not hasattr(context.scene, "pipeline_wizard"):
            return False
        state = context.scene.pipeline_wizard
        return state.lib_completed and bool(state.output_dir and state.library_name)

    def execute(self, context):
        state = context.scene.pipeline_wizard
        # Force rebuild to re-process all actions for thumbnail regeneration
        state.lib_force_rebuild = True
        try:
            ok_build = run_wizard_stage(context, state, PipelineStage.LIBRARY_BUILDING.value)
        except Exception as e:
            import traceback
            traceback.print_exc()
            self.report({'ERROR'}, f"重建失败: {e}")
            return {'CANCELLED'}
        if not ok_build:
            state.lib_force_rebuild = False
            self.report({'ERROR'}, "缩略图重建失败，请查看日志 (LibraryBuilding stage returned False)")
            return {'CANCELLED'}
        state.lib_force_rebuild = False
        self.report({'INFO'}, "缩略图已更新")
        return {'FINISHED'}


def register():
    bpy.utils.register_class(PIPELINE_OT_WizardStep4)
    bpy.utils.register_class(PIPELINE_OT_RebakeThumbnails)


def unregister():
    bpy.utils.unregister_class(PIPELINE_OT_RebakeThumbnails)
    bpy.utils.unregister_class(PIPELINE_OT_WizardStep4)
