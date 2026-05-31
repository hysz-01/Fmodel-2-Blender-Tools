# FModel_Tools/ui.py
# UI 面板 — 插件偏好设置、主面板与子面板
# Merged: backup pipeline/asset panels + new material/preferences/tools panels

import bpy
import os
import json
import re
from bpy_extras.io_utils import ExportHelper

from .core.i18n import t


class PIPELINE_OT_PickSkeleton(bpy.types.Operator):
    """从选中骨架拾取 FModel_Skeleton 属性填入过滤字段"""
    bl_idname = "pipeline.pick_skeleton_filter"
    bl_label = "拾取骨架名"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        obj = context.active_object
        return obj is not None and obj.type == 'ARMATURE'

    def execute(self, context):
        obj = context.active_object
        state = context.scene.pipeline_wizard
        sk_name = obj.get("FModel_Skeleton", "")
        if sk_name:
            state.skeleton_filter = str(sk_name)
            self.report({'INFO'}, f"已填入: {sk_name}")
        else:
            state.skeleton_filter = obj.name
            self.report({'INFO'}, f"无 FModel_Skeleton 属性, 已填入对象名: {obj.name}")
        return {'FINISHED'}


# ============================================================
# 插件偏好设置 (new)
# ============================================================

class FMODEL_AddonPreferences(bpy.types.AddonPreferences):
    bl_idname = __package__


class FMODEL_CoreProperties(bpy.types.PropertyGroup):
    active_pipeline: bpy.props.EnumProperty(
        name="格式",
        items=[
            ('UEFORMAT', "UE", "UEFormat 原生格式"),
            ('GLTF', "glTF", "标准 glTF 格式"),
            ('PSK', "PSK", "原始 UE 格式")
        ],
        default='UEFORMAT'
    )
    fix_bones: bpy.props.BoolProperty(name="自动修复骨骼", default=True)
    transfer_anim: bpy.props.BoolProperty(name="无损重定向", default=True)
    clean_old_anim: bpy.props.BoolProperty(name="清理缓存", default=True)
    purge_orphans: bpy.props.BoolProperty(name="导入后深度清理材质", default=True)
    merge_morphs: bpy.props.BoolProperty(name="自动合并形态键", default=False)
    fix_meshes: bpy.props.BoolProperty(name="修复网格撕裂", default=True)


# ============================================================
# 1. 主面板
# ============================================================

class FMODEL_PT_Toolbox(bpy.types.Panel):
    bl_label = "FModel 工具箱"
    bl_idname = "FMODEL_PT_toolbox"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'FModel'

    def draw(self, context):
        layout = self.layout
        props = context.scene.fmodel_core

        row = layout.row(align=True)
        row.prop(props, "active_pipeline", expand=True)
        layout.separator()
        split = layout.split(factor=0.5, align=True)
        col_in = split.column(align=True)
        col_out = split.column(align=True)

        if props.active_pipeline == 'UEFORMAT':
            col_in.operator("fmodel.import_model_uemodel", text=t("模型 (.uemodel)"), icon='MESH_DATA')
            col_in.operator("fmodel.import_anim_ueanim", text=t("动画 (.ueanim)"), icon='ANIM_DATA')
            col_in.operator("fmodel.import_anim_uepose", text=t("姿势 (.uepose)"), icon='ARMATURE_DATA')
            col_out.label(text=t("导出暂不支持"))
        elif props.active_pipeline == 'GLTF':
            col_in.operator("fmodel.import_model_gltf", text=t("导入 glTF"), icon='IMPORT')
            col_out.operator("fmodel.export_gltf_batch", text=t("导出 glTF"), icon='EXPORT')
        elif props.active_pipeline == 'PSK':
            col_in.operator("fmodel.import_model_psk", text=t("PSK 模型"), icon='MESH_DATA')
            col_in.operator("fmodel.import_anim_psa", text=t("PSA 动画"), icon='ANIM_DATA')
            col_out.label(text=t("导出暂不支持"))


# ============================================================
# 2. 资产管线 (from backup)
# ============================================================

class FMODEL_PT_Pipeline(bpy.types.Panel):
    bl_label = "资产管线"
    bl_idname = "FMODEL_PT_pipeline"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'FModel'
    bl_options = {'DEFAULT_CLOSED'}

    def draw(self, context):
        layout = self.layout
        if not hasattr(context.scene, "pipeline_wizard"):
            layout.label(text=t("管线模块未加载"), icon='INFO')
            return

        state = context.scene.pipeline_wizard
        step = state.current_step

        row = layout.row(align=True)
        row.scale_y = 1.2
        steps = [
            (1, "流程", state.flow_type != ''),
            (2, "项目", bool(state.source_dir and state.output_dir)),
            (3, "扫描", state.scan_completed),
            (4, "导入/打包", state.lib_completed),
        ]
        for num, name, done in steps:
            sub = row.row(align=True)
            if num == state.current_step:
                sub.alert = True
                op = sub.operator("pipeline.wizard_goto_step", text=t(name), depress=True)
            elif done:
                op = sub.operator("pipeline.wizard_goto_step", text=t(name), icon='CHECKMARK')
            else:
                op = sub.operator("pipeline.wizard_goto_step", text=t(name), icon='RADIOBUT_OFF')
            op.target_step = num

        layout.separator()

        if step == 1:
            col = layout.column(align=True)
            col.scale_y = 1.3
            op = col.operator("pipeline.wizard_step1", text=t("FModel 流程"), icon='MESH_DATA')
            op.flow = 'FMODEL'

        elif step == 2:
            col = layout.column(align=True)
            col.prop(state, "source_dir", text="项目目录")
            col.prop(state, "output_dir", text="输出目录")
            col.prop(state, "library_name", text="库名称")
            if state.flow_type == 'FMODEL':
                row = col.row(align=True)
                row.prop(state, "skeleton_filter", text="骨架过滤")
                row.operator("pipeline.pick_skeleton_filter", text="", icon='EYEDROPPER')

            ready = bool(state.source_dir and state.output_dir and state.library_name)
            layout.separator()
            if ready:
                layout.operator("pipeline.wizard_step2", text=t("下一步: 扫描"), icon='FORWARD')
            else:
                box = layout.box()
                box.label(text=t("请填写以上三项"), icon='INFO')

        elif step == 3:
            can_scan = bool(state.source_dir and state.output_dir)
            if not can_scan:
                layout.label(text=t("需先完成步骤2"), icon='ERROR')
                return
            if not state.scan_completed:
                row = layout.row(align=True)
                row.scale_y = 1.3
                row.operator("pipeline.wizard_step3", text=t("执行扫描"), icon='VIEWZOOM')
            else:
                col = layout.column(align=True)
                col.label(text=f"骨架: {state.scan_skeleton_count}", icon='ARMATURE_DATA')
                col.label(text=f"动画: {state.scan_anim_count}", icon='ANIM_DATA')
                col.label(text=f"新增: {state.scan_new_count}", icon='ADD')
                layout.separator()
                op = layout.operator("pipeline.wizard_goto_step", text=t("下一步: 导入并打包"), icon='FORWARD')
                op.target_step = 4

        elif step == 4:
            can_import = state.scan_completed
            obj = context.active_object
            has_arm = obj is not None and obj.type == 'ARMATURE'
            if not can_import:
                layout.label(text=t("需先完成步骤3"), icon='ERROR')
                return
            if has_arm:
                layout.label(text=f"骨架: {obj.name}", icon='ARMATURE_DATA')
            else:
                layout.label(text=t("请选中骨架"), icon='ERROR')
            layout.separator()

            # Import params
            box_import = layout.box()
            box_import.label(text=t("导入参数"), icon='PREFERENCES')
            col = box_import.column(align=True)
            col.prop(state, "import_scale")
            col.prop(state, "rotation_only")
            col.prop(state, "import_curves")

            # Thumbnail params
            box_thumb = layout.box()
            box_thumb.label(text=t("缩略图"), icon='RENDER_STILL')
            col = box_thumb.column(align=True)
            col.prop(state, "lib_generate_thumbnails")
            if state.lib_generate_thumbnails:
                col.prop(state, "lib_thumb_resolution", text="分辨率")
                col.prop(state, "lib_thumb_quality", text="质量")
                if state.lib_thumb_quality == 'RENDER':
                    col.prop(state, "lib_thumb_isolate", text="仅渲染骨架子级")

            # Build params
            box_build = layout.box()
            box_build.label(text=t("打包选项"), icon='PACKAGE')
            col = box_build.column(align=True)
            col.prop(state, "lib_chunk_size")
            col.prop(state, "lib_force_rebuild")
            col.prop(state, "lib_save_model", icon='OUTLINER_OB_MESH')
            if state.lib_save_model:
                col.prop(state, "lib_model_preview", icon='CAMERA_DATA')

            layout.separator()
            row = layout.row(align=True)
            row.scale_y = 1.3
            row.enabled = has_arm and not state.lib_completed
            row.operator("pipeline.wizard_step4", text=t("导入并打包"), icon='IMPORT')
            row = layout.row(align=True)
            row.scale_y = 1.0
            row.enabled = state.lib_completed
            row.operator("pipeline.rebake_thumbnails", text=t("重新生成缩略图"), icon='RENDER_STILL')

        layout.separator()
        layout.operator("pipeline.wizard_reset", text=t("重新开始"), icon='FILE_REFRESH')


class FMODEL_PT_PipelineDebug(bpy.types.Panel):
    bl_label = "管线调试"
    bl_idname = "FMODEL_PT_pipeline_debug"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'FModel'
    bl_parent_id = "FMODEL_PT_pipeline"
    bl_options = {'DEFAULT_CLOSED'}

    def draw(self, context):
        layout = self.layout
        from .core import PipelineContext
        row_ops = layout.row(align=True)
        row_ops.operator("pipeline.export_context_json", text=t("导出上下文"), icon='EXPORT')
        row_ops.operator("pipeline.clear_context", text=t("清空上下文"), icon='TRASH')
        layout.separator()
        ctx = PipelineContext.load_from_blender_text()
        if ctx:
            layout.label(text=f"状态: {ctx.current_stage}")
            if ctx.config and ctx.config.get("source_dir"):
                layout.label(text=f"项目: {ctx.config['source_dir']}")


# ============================================================
# 3. 材质工具 (new optimized)
# ============================================================

class FMODEL_PT_Material(bpy.types.Panel):
    bl_label = "材质工具"
    bl_idname = "FMODEL_PT_material"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'FModel'

    def draw(self, context):
        layout = self.layout
        props = context.scene.fmodel_material

        box_path = layout.box()
        box_path.label(text=t("贴图搜索"), icon='FILEBROWSER')
        col_path = box_path.column(align=True)
        col_path.prop(props, "umodel_tex_dir", text="纹理目录")
        col_path.prop(props, "umodel_mat_path", text="材质目录")
        col_path.prop(props, "search_depth", text="搜索深度（层）")

        box_auto = layout.box()
        box_auto.label(text=t("自动解析"), icon='AUTO')
        box_auto.prop(props, "auto_resolve_on_import", text="导入时自动解析材质")
        if props.auto_resolve_on_import:
            row_h = box_auto.row()
            row_h.prop(props, "heuristic_fallback_enabled", text="无JSON时猜测式匹配")
            if props.heuristic_fallback_enabled:
                box_auto.label(text=t("⚠ 匹配基于文本相似度，可能将错误的贴图链接到材质"), icon='ERROR')

        box_v2 = layout.box()
        box_v2.label(text=t("手动预设应用"), icon='SHADING_RENDERED')
        row_preset = box_v2.row(align=True)
        row_preset.prop(props, "resolver_preset", text="预设")
        row_preset.prop(props, "preset_category_filter", text="", icon='FILTER')

        from .Universal_tools.material.presets import get_preset
        preset = get_preset(props.resolver_preset)
        if preset and hasattr(preset, 'draw_options'):
            box_opts = box_v2.box()
            box_opts.label(text=f"{preset.PRESET_LABEL} 选项", icon='PREFERENCES')
            preset.draw_options(box_opts, props)

        row_v2 = box_v2.row(align=True)
        row_v2.scale_y = 1.1
        row_v2.operator("fmodel.analyze_material_resolution", text=t("分析(选中)"), icon='VIEWZOOM').mode = 'ACTIVE'
        row_v2.operator("fmodel.analyze_material_resolution", text=t("分析(全场景)"), icon='SCENE_DATA').mode = 'BATCH'
        row_apply = box_v2.row(align=True)
        row_apply.scale_y = 1.1
        row_apply.operator("fmodel.apply_material_resolution_v2", text=t("应用(选中)"), icon='CHECKBOX_HLT').mode = 'ACTIVE'
        row_apply.operator("fmodel.apply_material_resolution_v2", text=t("应用(全场景)"), icon='SCENE_DATA').mode = 'BATCH'
        box_v2.prop(props, "analyze_only", text="仅分析不写入")
        box_adv = box_v2.box()
        row_adv = box_adv.row()
        row_adv.prop(props, "strict_mode", text="严格模式", emboss=False)
        row_adv.prop(props, "strict_apply_only", text="仅严格应用", emboss=False)
        box_adv.prop(props, "report_out_path", text="报告路径")
        row_report = box_adv.row(align=True)
        row_report.operator("fmodel.export_material_report", text=t("导出报告"), icon='EXPORT').mode = 'BATCH'
        row_report.operator("fmodel.open_material_report", text=t("打开报告"), icon='FILE_FOLDER')
        if props.last_summary:
            box_v2.label(text=props.last_summary, icon='INFO')
        if props.last_failed_count > 0:
            box_v2.label(text=f"失败材质: {props.last_failed_count}", icon='ERROR')
        if props.last_error_summary:
            box_v2.label(text=props.last_error_summary[:120], icon='ERROR')


# ============================================================
# 4. 拓展工具 (new - with per-panel poll)
# ============================================================

class FMODEL_PT_GeneralTools(bpy.types.Panel):
    bl_label = "拓展工具"
    bl_idname = "FMODEL_PT_general_tools"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'FModel'
    bl_options = {'DEFAULT_CLOSED'}

    def draw(self, context):
        pass


class FMODEL_PT_Mesh(bpy.types.Panel):
    bl_label = "网格工具"
    bl_idname = "FMODEL_PT_mesh"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'FModel'
    bl_parent_id = "FMODEL_PT_general_tools"
    bl_options = {'DEFAULT_CLOSED'}

    def draw(self, context):
        layout = self.layout
        col = layout.column(align=True)
        col.scale_y = 1.2
        col.operator("fmodel.clean_empty_morphs", text=t("清理空白形态键"), icon='BRUSH_DATA')
        col.operator("fmodel.separate_by_material_smart", text=t("按材质分离"), icon='MATERIAL')


class FMODEL_PT_Skeleton(bpy.types.Panel):
    bl_label = "骨架 / 姿态"
    bl_idname = "FMODEL_PT_skeleton"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'FModel'
    bl_parent_id = "FMODEL_PT_general_tools"
    bl_options = {'DEFAULT_CLOSED'}

    def draw(self, context):
        layout = self.layout
        skel_props = context.scene.fmodel_skeleton
        obj = context.active_object

        col = layout.column(align=True)
        col.scale_y = 1.2
        col.operator("fmodel.sort_bones", text=t("整理骨骼层级"), icon='GROUP_BONE')
        row = col.row(align=True)
        row.operator("fmodel.rename_bones", text=t("批量重命名"), icon='SORTALPHA')
        row.operator("fmodel.fix_bone_names", text=t("UE标准"), icon='CHECKMARK')
        row = col.row(align=True)
        row.operator("fmodel.generate_bone_mapping", text=t("生成映射"), icon='TEXT')
        row.operator("fmodel.map_bone_names", text=t("应用映射"), icon='FILE_TEXT')

        layout.separator()
        if not (obj and obj.type == 'ARMATURE' and obj.mode == 'POSE'):
            layout.label(text=t("姿态镜像需进入姿态模式"), icon='INFO')
            return

        row_src = layout.row(align=True)
        row_src.prop_search(skel_props, "mirror_source_bone", obj.pose, "bones", text="源", icon='BONE_DATA')
        row_src.operator("fmodel.grab_active_bone", text="", icon='EYEDROPPER').target_field = 'SOURCE'
        row_tgt = layout.row(align=True)
        row_tgt.prop_search(skel_props, "mirror_target_bone", obj.pose, "bones", text="目标", icon='BONE_DATA')
        row_tgt.operator("fmodel.grab_active_bone", text="", icon='EYEDROPPER').target_field = 'TARGET'
        row_adv = layout.row()
        row_adv.prop(skel_props, "show_mirror_adv", text="选项",
                     icon='TRIA_DOWN' if skel_props.show_mirror_adv else 'TRIA_RIGHT', emboss=False)
        if skel_props.show_mirror_adv:
            box = layout.box()
            box.prop(skel_props, "mirror_plane", expand=True)
            row = box.row(align=True)
            row.prop(skel_props, "mirror_apply_loc", toggle=True)
            row.prop(skel_props, "mirror_apply_rot", toggle=True)
            row.prop(skel_props, "mirror_strict_axis", toggle=True)
        layout.operator("fmodel.mirror_pose_custom", text=t("执行镜像"), icon='PLAY')


class FMODEL_PT_Animation(bpy.types.Panel):
    bl_label = "动画工具"
    bl_idname = "FMODEL_PT_animation"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'FModel'
    bl_parent_id = "FMODEL_PT_general_tools"
    bl_options = {'DEFAULT_CLOSED'}

    def draw(self, context):
        layout = self.layout

        box_bake = layout.box()
        box_bake.label(text=t("烘焙工具"), icon='ARMATURE_DATA')
        col_bake = box_bake.column(align=True)
        col_bake.scale_y = 1.2
        col_bake.operator("fmodel.clean_all_actions", text=t("清理动画数据"), icon='TRASH')
        col_bake.operator("fmodel.clean_action", text=t("清理当前动作"), icon='BRUSH_DATA')


# ============================================================
# 5. 资产库 (from backup)
# ============================================================

class FMODEL_PT_AssetLibrary(bpy.types.Panel):
    bl_label = "资产库"
    bl_idname = "FMODEL_PT_asset_library"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'FModel'
    bl_options = {'DEFAULT_CLOSED'}

    def draw(self, context):
        pass


class FMODEL_PT_LibrarySettings(bpy.types.Panel):
    """资产库设置"""
    bl_label = "资产库设置"
    bl_idname = "FMODEL_PT_library_settings"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'FModel'
    bl_parent_id = "FMODEL_PT_asset_library"

    def draw(self, context):
        layout = self.layout

        if not hasattr(context.scene, "fmodel_assets"):
            layout.label(text=t("资产库模块未加载"), icon='INFO')
            return

        if not hasattr(context.scene, "fmodel_anim_manager"):
            layout.label(text=t("请先扫描"), icon='INFO')
            return

        props = context.scene.fmodel_assets
        manager = context.scene.fmodel_anim_manager

        row = layout.row()
        row.template_list(
            "ASSETS_UL_LibraryTree", "",
            manager, "tree_items",
            manager, "active_folder_index",
            rows=8
        )
        col_btns = row.column(align=True)
        col_btns.operator("fmodel.add_library", text="", icon='ADD')
        col_btns.operator("fmodel.remove_library", text="", icon='REMOVE')
        col_btns.separator()
        col_btns.operator("fmodel.browse_lib_path", text="", icon='FILE_FOLDER')
        col_btns.operator("fmodel.mount_blend_file", text="", icon='FILE_BLEND')
        col_btns.separator()
        col_btns.operator("fmodel.open_lib_folder", text="", icon='SCREEN_BACK')

        layout.separator()
        row_scan = layout.row(align=True)
        row_scan.scale_y = 1.2
        row_scan.operator("fmodel.scan_anims", text=t("扫描全部"), icon='VIEWZOOM')
        row_scan.operator("fmodel.scan_local_anims", text=t("本地"), icon='FILE_REFRESH')

        row_mount = layout.row(align=True)
        row_mount.operator("fmodel.mount_all_libs", text=t("挂载到 Blender"), icon='LINKED')
        row_mount.operator("fmodel.unmount_all_libs", text=t("卸载"), icon='UNLINKED')


def _model_draw_panel(self, context):
    from .Assets.Models.operators import get_model_dir, _scan_models, _get_preview_icon
    layout = self.layout

    if not hasattr(context.scene, "fmodel_model_assets"):
        layout.label(text=t("模型资产模块未加载"), icon='INFO')
        return

    props = context.scene.fmodel_model_assets

    # ── Actions ──
    row = layout.row(align=True)
    row.scale_y = 1.3
    row.operator("fmodel.save_model", text=t("保存模型"), icon='EXPORT')
    row.operator("fmodel.open_model_selector", text=t("浏览导入"), icon='IMPORT')

    active_lib_path = get_model_dir(context)
    if active_lib_path:
        display_path = active_lib_path
        if len(display_path) > 45:
            display_path = "..." + display_path[-42:]
        layout.label(text=display_path, icon='FILE_FOLDER')

    layout.separator()

    # ── Model list ──
    models = _scan_models(context)
    if not models:
        layout.label(text=t("未保存模型"), icon='INFO')
        return

    layout.label(text=f"{len(models)} 个模型", icon='OUTLINER_OB_ARMATURE')

    selected_name = props.selected_model
    selected_model = next((m for m in models if m["name"] == selected_name), None)

    # ── Selected detail ──
    if selected_model:
        box = layout.box()
        icon_id = _get_preview_icon(selected_model["preview"])
        if icon_id:
            icon_row = box.row()
            icon_row.alignment = 'CENTER'
            icon_row.template_icon(icon_value=icon_id, scale=6.0)
        metadata = box.row(align=True)
        metadata.alignment = 'CENTER'
        metadata.label(text=selected_model["name"], icon='OUTLINER_OB_ARMATURE')

        meta = selected_model.get("meta", {})
        if meta:
            stats = box.row(align=True)
            stats.alignment = 'CENTER'
            parts = []
            if meta.get("bone_count"): parts.append(f"{meta['bone_count']} 骨骼")
            if meta.get("mesh_count"): parts.append(f"{meta['mesh_count']} 网格")
            if meta.get("vert_count"): parts.append(f"{meta['vert_count']:,} 顶点")
            stats.label(text=" · ".join(parts) if parts else "")

        row_ops = box.row(align=True)
        row_ops.scale_y = 1.2
        op_imp = row_ops.operator("fmodel.import_model_from_browser", text=t("导入"), icon='IMPORT')
        op_imp.model_name = selected_model["name"]
        op_imp.model_dir = selected_model["path"]
        op_del = row_ops.operator("fmodel.delete_model", text=t("删除"), icon='TRASH')
        op_del.model_name = selected_model["name"]
        op_del.model_dir = selected_model["path"]

    # ── Grid ──
    col_count = 3
    for i in range(0, len(models), col_count):
        row_cards = layout.row(align=True)
        for j in range(col_count):
            idx = i + j
            card = row_cards.column(align=True)
            if idx < len(models):
                model = models[idx]
                is_selected = model["name"] == selected_name
                icon_id = _get_preview_icon(model["preview"])
                btn = card.operator(
                    "fmodel.select_model", text=model["name"],
                    icon_value=icon_id if icon_id else 0, depress=is_selected
                )
                btn.model_name = model["name"]
            else:
                card.label(text="")


class FMODEL_PT_ModelAssets(bpy.types.Panel):
    bl_label = "模型资产"
    bl_idname = "FMODEL_PT_model_assets"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'FModel'
    bl_parent_id = "FMODEL_PT_asset_library"

    def draw(self, context):
        _model_draw_panel(self, context)


class FMODEL_PT_AnimationAssets(bpy.types.Panel):
    bl_label = "动画资产"
    bl_idname = "FMODEL_PT_animation_assets"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'FModel'
    bl_parent_id = "FMODEL_PT_asset_library"
    bl_options = {'DEFAULT_CLOSED'}

    def draw(self, context):
        layout = self.layout
        if not hasattr(context.scene, "fmodel_anim_manager"):
            box = layout.box()
            box.label(text=t("在 [资产库设置] 中点击扫描"), icon='INFO')
            return

        manager = context.scene.fmodel_anim_manager
        anim_count = sum(1 for it in manager.tree_items if it.item_type == 'ANIM')
        if anim_count == 0:
            box = layout.box()
            box.label(text=t("未找到动画"), icon='INFO')
            return

        layout.label(text=f"{len(manager.skeleton_items)} 骨架 / {anim_count} 动画", icon='ANIM_DATA')
        row_filter = layout.row(align=True)
        row_filter.prop(manager, "active_skeleton", text="")
        row_filter.prop(manager, "search_filter", text="", icon='VIEWZOOM')
        if manager.search_filter:
            op = row_filter.operator("wm.context_set_string", text="", icon='X')
            op.data_path = "scene.fmodel_anim_manager.search_filter"
            op.value = ""

        if manager.search_filter:
            count = sum(
                1 for it in manager.tree_items
                if it.item_type == 'ANIM' and manager.search_filter.lower() in it.name.lower()
                and (manager.active_skeleton in ("ALL", "NONE") or it.skeleton == manager.active_skeleton)
            )
            layout.label(text=f"{count} 个匹配", icon='INFO')


class FMODEL_PT_AnimDisplay(bpy.types.Panel):
    bl_label = "显示设置"
    bl_idname = "FMODEL_PT_anim_display"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'FModel'
    bl_parent_id = "FMODEL_PT_animation_assets"
    bl_options = {'DEFAULT_CLOSED'}

    def draw(self, context):
        layout = self.layout
        if not hasattr(context.scene, "fmodel_anim_manager"):
            return
        manager = context.scene.fmodel_anim_manager
        row_mode = layout.row(align=True)
        row_mode.prop(manager, "display_mode", expand=True)
        layout.separator()
        row_method = layout.row(align=True)
        row_method.prop(manager, "import_mode", text="")
        row_method.prop(manager, "apply_method", text="")
        row_view = layout.row(align=True)
        row_view.prop(manager, "show_as_grid", icon='MESH_GRID', text="卡片视图", toggle=True)
        row_params = layout.row(align=True)
        row_params.prop(manager, "list_rows", text="行")
        row_col = row_params.row(align=True)
        row_col.enabled = manager.display_mode == 'DETAIL_V' and manager.show_as_grid
        row_col.prop(manager, "grid_columns", text="列")
        row_scale = row_params.row(align=True)
        row_scale.enabled = manager.show_as_grid
        row_scale.prop(manager, "grid_icon_scale", text="缩放", slider=True)
        if manager.display_mode == 'DETAIL_H':
            layout.prop(manager, "split_factor", text="分栏", slider=True)


class FMODEL_PT_AnimList(bpy.types.Panel):
    """动画列表与播放"""
    bl_label = "动画列表"
    bl_idname = "FMODEL_PT_anim_list"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'FModel'
    bl_parent_id = "FMODEL_PT_animation_assets"

    def draw(self, context):
        layout = self.layout
        manager = getattr(context.scene, "fmodel_anim_manager", None)
        if not manager:
            return

        self._draw_anim_list(layout, context, manager)

        layout.separator()
        row = layout.row(align=True)
        row.scale_y = 1.2
        op = row.operator("screen.frame_jump", text="", icon='REW')
        op.end = False
        row.operator("screen.animation_play", text="", icon='PAUSE' if context.screen.is_animation_playing else 'PLAY')
        row.prop(context.scene, "frame_current", text="", slider=True)

        col = layout.column(align=True)
        col.scale_y = 1.3
        col.operator("fmodel.apply_anim", text=t("应用到骨架"), icon='IMPORT')

    def _draw_anim_list(self, layout, context, manager):
        active_folder_id = ""
        active_skel = ""
        if manager.tree_items and manager.active_folder_index < len(manager.tree_items):
            sel_item = manager.tree_items[manager.active_folder_index]
            if sel_item.item_type == 'FOLDER':
                active_folder_id = sel_item.node_id
                active_skel = sel_item.skeleton

        if manager.display_mode == 'TREE':
            layout.template_list(
                "ASSETS_UL_AnimTree", "",
                manager, "tree_items",
                manager, "active_item_index",
                rows=manager.list_rows
            )
        elif manager.display_mode == 'DETAIL_H':
            box_split = layout.box()
            split = box_split.split(factor=manager.split_factor)
            col_l = split.column()
            col_l.label(text=t("文件夹"), icon='FILE_FOLDER')
            col_l.template_list(
                "ASSETS_UL_FolderTree", "",
                manager, "tree_items",
                manager, "active_folder_index",
                rows=manager.list_rows
            )
            col_r = split.column()
            col_r.label(text=t("动画"), icon='ANIM_DATA')
            v_idxs = _get_visible_anims(manager, active_folder_id, active_skel)
            if manager.show_as_grid:
                from .Assets.Anims import ui_custom_grid
                ui_custom_grid.FModelCustomGrid.draw(
                    col_r, context, manager, v_idxs,
                    _draw_grid_card, _draw_empty_card
                )
            else:
                col_r.template_list(
                    "ASSETS_UL_AnimGrid", "",
                    manager, "tree_items",
                    manager, "active_item_index",
                    rows=manager.list_rows
                )
        elif manager.display_mode == 'DETAIL_V':
            col = layout.column(align=True)
            col.template_list(
                "ASSETS_UL_FolderTree", "",
                manager, "tree_items",
                manager, "active_folder_index",
                rows=manager.list_rows
            )
            col.separator(factor=1.5)
            v_idxs = _get_visible_anims(manager, active_folder_id, active_skel)
            if manager.show_as_grid:
                from .Assets.Anims import ui_custom_grid
                ui_custom_grid.FModelCustomGrid.draw(
                    col, context, manager, v_idxs,
                    _draw_grid_card, _draw_empty_card
                )
            else:
                col.template_list(
                    "ASSETS_UL_AnimGrid", "",
                    manager, "tree_items",
                    manager, "active_item_index",
                    rows=manager.list_rows
                )


class FMODEL_PT_AnimDetail(bpy.types.Panel):
    """动画详情"""
    bl_label = "详情"
    bl_idname = "FMODEL_PT_anim_detail"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'FModel'
    bl_parent_id = "FMODEL_PT_animation_assets"
    bl_options = {'DEFAULT_CLOSED'}

    def draw(self, context):
        layout = self.layout
        manager = getattr(context.scene, "fmodel_anim_manager", None)
        if not manager:
            return

        if not manager.tree_items or manager.active_item_index >= len(manager.tree_items):
            layout.label(text=t("选择一个动画"), icon='INFO')
            return

        item = manager.tree_items[manager.active_item_index]
        if item.item_type != 'ANIM':
            layout.label(text=t("选择一个动画"), icon='INFO')
            return

        from .Assets.Anims.anim_manager import get_custom_icon

        # ── Upper: preview image ──
        box_img = layout.box()
        col_img = box_img.column(align=True)
        col_img.scale_y = 1.2
        icon_id = get_custom_icon(item.thumb_path, item.blend_path)
        if icon_id:
            icon_row = col_img.row(align=True)
            icon_row.alignment = 'CENTER'
            icon_row.template_icon(icon_value=icon_id, scale=8.0)
        else:
            icon_row = col_img.row(align=True)
            icon_row.alignment = 'CENTER'
            icon_row.label(text=t("无预览图"), icon='IMAGE_DATA')

        # ── Lower: details ──
        box_info = layout.box()
        col_info = box_info.column(align=True)
        col_info.scale_y = 0.9
        col_info.label(text=item.name, icon='ANIM_DATA')

        act = bpy.data.actions.get(item.action_name)
        if act and act.frame_range:
            frames = int(act.frame_range[1] - act.frame_range[0])
            fps = context.scene.render.fps
            duration = frames / fps if fps > 0 else 0
            col_info.label(text=f"帧数: {frames} ({duration:.1f}s @ {fps}fps)")
        col_info.label(text=f"骨架: {item.skeleton}")

        if item.blend_path:
            import os
            col_info.label(text=f"源: {os.path.basename(item.blend_path)}")


# ============================================================
# 动画辅助函数 (from backup)
# ============================================================

def _get_visible_anims(manager, active_folder_id, active_skel):
    search = manager.search_filter.lower().strip()
    return [
        i for i, it in enumerate(manager.tree_items)
        if it.item_type == 'ANIM' and it.parent_id == active_folder_id
        and it.skeleton == active_skel
        and (not search or search in it.name.lower())
    ]


def _draw_grid_card(ctx, col_layout, item, item_idx, is_active, mgr):
    from .Assets.Anims.anim_manager import get_custom_icon
    card = col_layout.box()
    card.scale_x = 1.0
    card.scale_y = 1.0
    card_col = card.column(align=True)
    card_col.ui_units_x = mgr.grid_icon_scale + 2
    icon_id = get_custom_icon(item.thumb_path, item.blend_path)
    icon_row = card_col.row(align=True)
    icon_row.alignment = 'CENTER'
    icon_row.template_icon(icon_value=icon_id if icon_id else 0, scale=mgr.grid_icon_scale)
    name_row = card_col.row(align=True)
    name_row.alignment = 'CENTER'
    op_sel = name_row.operator("fmodel.select_grid_item", text=item.name, emboss=False)
    op_sel.target_index = item_idx
    ops = card_col.row(align=True)
    ops.alignment = 'CENTER'
    op_prev = ops.operator("fmodel.preview_anim", text="", icon='RESTRICT_VIEW_OFF')
    op_prev.target_node_id = item.node_id
    op_app = ops.operator("fmodel.apply_anim", text="", icon='IMPORT')
    op_app.target_node_id = item.node_id


def _draw_empty_card(ctx, col_layout, mgr):
    card = col_layout.box()
    card.scale_x = 1.0
    card.scale_y = 1.0
    card_col = card.column(align=True)
    card_col.ui_units_x = mgr.grid_icon_scale + 2
    icon_row = card_col.row(align=True)
    icon_row.alignment = 'CENTER'
    icon_row.template_icon(icon_value=0, scale=mgr.grid_icon_scale)


# ============================================================
# 资产库 + 管线 Operators (from backup)
# ============================================================

_LIB_TREE_EXPANDED = {}

class FMODEL_OT_ToggleTreeNode(bpy.types.Operator):
    bl_idname = "fmodel.toggle_tree_node"
    bl_label = "展开/折叠"
    bl_options = {'INTERNAL'}
    node_id: bpy.props.StringProperty()

    def execute(self, context):
        _LIB_TREE_EXPANDED[self.node_id] = not _LIB_TREE_EXPANDED.get(self.node_id, False)
        return {'FINISHED'}


class FMODEL_OT_SelectTreeNode(bpy.types.Operator):
    bl_idname = "fmodel.select_tree_node"
    bl_label = "选中"
    bl_options = {'INTERNAL'}
    lib_index: bpy.props.IntProperty()

    def execute(self, context):
        props = context.scene.fmodel_assets
        if self.lib_index < len(props.project_libs):
            props.active_lib_index = self.lib_index
        return {'FINISHED'}


class FMODEL_OT_AddLibrary(bpy.types.Operator):
    bl_idname = "fmodel.add_library"
    bl_label = "添加资产库"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        props = context.scene.fmodel_assets
        item = props.project_libs.add()
        item.name = f"Library_{len(props.project_libs)}"
        props.active_lib_index = len(props.project_libs) - 1
        return {'FINISHED'}


class FMODEL_OT_RemoveLibrary(bpy.types.Operator):
    bl_idname = "fmodel.remove_library"
    bl_label = "移除资产库"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        props = context.scene.fmodel_assets
        return len(props.project_libs) > 0 and props.active_lib_index < len(props.project_libs)

    def execute(self, context):
        props = context.scene.fmodel_assets
        props.project_libs.remove(props.active_lib_index)
        props.active_lib_index = max(0, props.active_lib_index - 1)
        return {'FINISHED'}


class ASSETS_UL_LibList(bpy.types.UIList):
    """旧版资产库列表（保留以防兼容性问题）"""
    def draw_item(self, context, layout, data, item, icon, active_data, active_propname):
        row = layout.row(align=True)
        row.prop(item, "name", text="", emboss=False, icon='FILE_FOLDER')


class PIPELINE_OT_ClearContext(bpy.types.Operator):
    bl_idname = "pipeline.clear_context"
    bl_label = "清空管线上下文"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        from .core import PipelineContext
        PipelineContext.clear_blender_text()
        self.report({'INFO'}, "已清空 PipelineContext")
        return {'FINISHED'}


class PIPELINE_OT_ExportContextJson(bpy.types.Operator, ExportHelper):
    bl_idname = "pipeline.export_context_json"
    bl_label = "导出管线上下文"
    bl_options = {'REGISTER'}
    filename_ext = ".json"
    filter_glob: bpy.props.StringProperty(default="*.json", options={'HIDDEN'})

    def invoke(self, context, event):
        if not self.filepath:
            self.filepath = bpy.path.abspath("//PipelineContext.json")
        return super().invoke(context, event)

    def execute(self, context):
        from .core import PipelineContext
        ctx = PipelineContext.load_from_blender_text()
        if not ctx:
            self.report({'ERROR'}, "没有可导出的 PipelineContext")
            return {'CANCELLED'}
        try:
            os.makedirs(os.path.dirname(self.filepath) or '.', exist_ok=True)
            with open(self.filepath, 'w', encoding='utf-8') as f:
                json.dump(ctx.to_dict(), f, indent=2, ensure_ascii=False)
        except Exception as e:
            self.report({'ERROR'}, f"导出失败: {e}")
            return {'CANCELLED'}
        self.report({'INFO'}, f"已导出到: {self.filepath}")
        return {'FINISHED'}


# ============================================================
# GameProfile 管理器
# ============================================================

_PROFILES_DIR = os.path.join(os.path.dirname(__file__), "Shaders", "GameProfiles")


def _list_profiles():
    if not os.path.isdir(_PROFILES_DIR):
        return []
    return sorted([f[:-5] for f in os.listdir(_PROFILES_DIR) if f.endswith(".json")])


def _load_profile(game_id):
    fp = os.path.join(_PROFILES_DIR, f"{game_id}.json")
    if not os.path.exists(fp):
        return {}
    with open(fp, 'r', encoding='utf-8') as f:
        return json.load(f)


def _save_profile(game_id, data):
    os.makedirs(_PROFILES_DIR, exist_ok=True)
    fp = os.path.join(_PROFILES_DIR, f"{game_id}.json")
    with open(fp, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def _get_profile_enum(self, context):
    return [(p, p, "") for p in _list_profiles()] or [("__NONE__", "(无预设)", "")]


class GP_OT_CreateProfile(bpy.types.Operator):
    bl_idname = "fmodel.gp_create_profile"
    bl_label = "新建预设"
    game_id: bpy.props.StringProperty(name="游戏ID", default="new_game")
    display_name: bpy.props.StringProperty(name="显示名", default="新游戏")

    def execute(self, context):
        game_id = self.game_id.strip().lower().replace(" ", "_")
        if not game_id:
            return {'CANCELLED'}
        data = {"game_id": game_id, "display_name": self.display_name,
                 "param_mapping": {}, "parent_inheritance": True,
                 "colorspace_rules": {}, "tool_groups_default": []}
        _save_profile(game_id, data)
        context.scene.fmodel_gp_editor.active_profile = game_id
        return {'FINISHED'}

    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self, width=300)


class GP_OT_DeleteProfile(bpy.types.Operator):
    bl_idname = "fmodel.gp_delete_profile"
    bl_label = "删除预设"
    game_id: bpy.props.StringProperty()

    def execute(self, context):
        fp = os.path.join(_PROFILES_DIR, f"{self.game_id}.json")
        if os.path.exists(fp):
            os.remove(fp)
        if context.scene.fmodel_gp_editor.active_profile == self.game_id:
            context.scene.fmodel_gp_editor.active_profile = ""
        return {'FINISHED'}

    def invoke(self, context, event):
        return context.window_manager.invoke_confirm(self, event, title=f"删除 {self.game_id}？")


class GP_OT_SaveProfile(bpy.types.Operator):
    bl_idname = "fmodel.gp_save_profile"
    bl_label = "保存预设"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        state = context.scene.fmodel_gp_editor
        game_id = state.active_profile.strip()
        if not game_id:
            return {'CANCELLED'}
        mapping = {}
        for item in state.mappings:
            if item.ue_param.strip():
                mapping[item.ue_param.strip().lower()] = item.channel.strip() if item.channel.strip() else None
        data = _load_profile(game_id)
        data["game_id"] = game_id
        data["display_name"] = state.display_name or game_id
        data["param_mapping"] = mapping
        data["parent_inheritance"] = state.parent_inheritance
        _save_profile(game_id, data)
        self.report({'INFO'}, f"已保存: {game_id}")
        return {'FINISHED'}


class GP_OT_AddMapping(bpy.types.Operator):
    bl_idname = "fmodel.gp_add_mapping"
    bl_label = "添加映射"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        item = context.scene.fmodel_gp_editor.mappings.add()
        item.ue_param = "new_param"
        return {'FINISHED'}


class GP_OT_RemoveMapping(bpy.types.Operator):
    bl_idname = "fmodel.gp_remove_mapping"
    bl_label = "移除映射"
    bl_options = {'REGISTER', 'UNDO'}
    index: bpy.props.IntProperty()

    def execute(self, context):
        state = context.scene.fmodel_gp_editor
        if 0 <= self.index < len(state.mappings):
            state.mappings.remove(self.index)
        return {'FINISHED'}


class GPMappingItem(bpy.types.PropertyGroup):
    ue_param: bpy.props.StringProperty(name="UE参数名")
    channel: bpy.props.EnumProperty(
        name="通道",
        items=lambda s, c: _gp_channel_enum(),
    )


def _gp_channel_enum():
    from .Universal_tools.material.shader_manager import STANDARD_INTERFACES
    items = [("", "(未映射)", "")]
    for ch_id, info in STANDARD_INTERFACES.items():
        items.append((ch_id, info["label"], ""))
    items.append(("other", "Other", ""))
    return items


def _gp_on_profile_changed(self, context):
    """active_profile selected → load profile data from JSON"""
    if not self.active_profile or self.active_profile == "__NONE__":
        return
    profile = _load_profile(self.active_profile)
    self.mappings.clear()
    self.display_name = profile.get("display_name", self.active_profile)
    self.parent_inheritance = profile.get("parent_inheritance", True)
    for ue_param, channel in profile.get("param_mapping", {}).items():
        item = self.mappings.add()
        item.ue_param = ue_param
        item.channel = channel or ""


class GPEditorState(bpy.types.PropertyGroup):
    active_profile: bpy.props.EnumProperty(name="预设", items=_get_profile_enum, update=_gp_on_profile_changed)
    display_name: bpy.props.StringProperty(name="显示名")
    parent_inheritance: bpy.props.BoolProperty(name="继承父材质", default=True)
    mappings: bpy.props.CollectionProperty(type=GPMappingItem)


class FMODEL_PT_GameProfileManager(bpy.types.Panel):
    bl_label = "GameProfile"
    bl_idname = "FMODEL_PT_game_profile"
    bl_space_type = 'NODE_EDITOR'
    bl_region_type = 'UI'
    bl_category = 'FModel'

    def draw(self, context):
        layout = self.layout
        state = context.scene.fmodel_gp_editor

        row = layout.row(align=True)
        row.prop(state, "active_profile", text="")
        row.operator("fmodel.gp_create_profile", text="", icon='ADD')
        if state.active_profile and state.active_profile != "__NONE__":
            row.operator("fmodel.gp_delete_profile", text="", icon='TRASH').game_id = state.active_profile

        if not state.active_profile or state.active_profile == "__NONE__":
            layout.label(text=t("选择或新建 GameProfile"), icon='INFO')
            return

        profile = _load_profile(state.active_profile)
        layout.prop(state, "display_name")
        layout.prop(state, "parent_inheritance")

        layout.separator()
        layout.label(text=f"参数映射 ({len(state.mappings)})", icon='MODIFIER')

        for i, item in enumerate(state.mappings):
            row = layout.row(align=True)
            row.prop(item, "ue_param", text="")
            row.prop(item, "channel", text="")
            op = row.operator("fmodel.gp_remove_mapping", text="", icon='X')
            op.index = i

        row = layout.row(align=True)
        row.operator("fmodel.gp_add_mapping", text=t("添加映射"), icon='ADD')
        row.operator("fmodel.gp_save_profile", text=t("保存"), icon='FILE_TICK')

    @classmethod
    def poll(cls, context):
        return hasattr(context.scene, "fmodel_gp_editor")


# ============================================================
# Registration
# ============================================================

_classes = (
    FMODEL_AddonPreferences,
    FMODEL_CoreProperties,
    FMODEL_OT_ToggleTreeNode,
    FMODEL_OT_SelectTreeNode,
    FMODEL_OT_AddLibrary,
    FMODEL_OT_RemoveLibrary,
    ASSETS_UL_LibList,
    PIPELINE_OT_ClearContext,
    PIPELINE_OT_ExportContextJson,
    PIPELINE_OT_PickSkeleton,
    FMODEL_PT_Toolbox,
    FMODEL_PT_Pipeline,
    FMODEL_PT_PipelineDebug,
    FMODEL_PT_GeneralTools,
    FMODEL_PT_Material,
    FMODEL_PT_Mesh,
    FMODEL_PT_Skeleton,
    FMODEL_PT_Animation,
    FMODEL_PT_AssetLibrary,
    FMODEL_PT_LibrarySettings,
    FMODEL_PT_ModelAssets,
    FMODEL_PT_AnimationAssets,
    FMODEL_PT_AnimDisplay,
    FMODEL_PT_AnimList,
    FMODEL_PT_AnimDetail,
    # GameProfile manager
    GP_OT_CreateProfile,
    GP_OT_DeleteProfile,
    GP_OT_SaveProfile,
    GP_OT_AddMapping,
    GP_OT_RemoveMapping,
    GPMappingItem,
    GPEditorState,
    FMODEL_PT_GameProfileManager,
)


def register():
    for cls in _classes:
        bpy.utils.register_class(cls)
    bpy.types.Scene.fmodel_core = bpy.props.PointerProperty(type=FMODEL_CoreProperties)
    bpy.types.Scene.fmodel_gp_editor = bpy.props.PointerProperty(type=GPEditorState)


def unregister():
    del bpy.types.Scene.fmodel_gp_editor
    del bpy.types.Scene.fmodel_core
    for cls in reversed(_classes):
        bpy.utils.unregister_class(cls)
