# FModel_Tools/Universal_tools/material/operators.py
# 材质操作符 — 手动材质解析、应用、报告

import bpy
import os

from .resolver import (
    resolve_objects_materials_with_options,
    format_summary,
    export_report_json,
)


def _safe_error_summary(failed: list) -> str:
    """安全获取失败摘要, 防止 IndexError / AttributeError"""
    if not failed:
        return ""
    try:
        return f"{failed[0].material_name}: {failed[0].errors[0]}"
    except (AttributeError, IndexError, TypeError):
        return f"{len(failed)} 个材质解析失败"


def _get_mesh_targets(context, mode='ACTIVE'):
    """统一获取目标网格列表: ACTIVE=选中对象, BATCH=全场景"""
    objs = context.selected_objects if mode == 'ACTIVE' else context.scene.objects
    return [o for o in objs if o.type == 'MESH']


def _update_failure_stats(props, results):
    """统一更新失败统计到材质属性"""
    failed = [r for r in results if not r.success]
    props.last_failed_count = len(failed)
    props.last_error_summary = _safe_error_summary(failed)


def _try_phase3(targets):
    """对选中对象尝试 Phase 1-3 管线（需有 gltf_import_path 标记）。返回成功数。"""
    succeeded = 0
    for obj in targets:
        model_path = obj.get("gltf_import_path", "")
        if model_path:
            try:
                from .auto_resolve import auto_resolve_materials_for_import
                auto_resolve_materials_for_import([obj], model_path)
                succeeded += 1
            except Exception:
                pass
    return succeeded


class MAT_OT_ProcessMaterial(bpy.types.Operator):
    bl_idname = "fmodel.process_material"
    bl_label = "智能链接材质"
    bl_options = {'REGISTER', 'UNDO'}
    mode: bpy.props.EnumProperty(items=[('ACTIVE', "选中", ""), ('BATCH', "全场景", "")], default='ACTIVE')

    def execute(self, context):
        props = context.scene.fmodel_material
        if self.mode == 'ACTIVE':
            targets = [o for o in context.selected_objects if o.type == 'MESH']
        else:
            targets = [o for o in context.scene.objects if o.type == 'MESH']
        if not targets:
            self.report({'WARNING'}, "请选中网格对象")
            return {'CANCELLED'}

        # Try Phase 1-3 first (imported objects with known filepath)
        phase3_done = _try_phase3(targets)

        # Fallback: old resolver for objects without filepath info
        tex_dir = bpy.path.abspath(props.umodel_tex_dir) if props.umodel_tex_dir else ""
        mat_dir = bpy.path.abspath(props.umodel_mat_path) if props.umodel_mat_path else ""

        strict_mode = props.strict_mode and (not props.strict_apply_only or not props.analyze_only)
        results = resolve_objects_materials_with_options(
            targets, tex_dir, mat_dir, props.resolver_style,
            analyze_only=props.analyze_only, strict_mode=strict_mode,
        )
        props.last_summary = format_summary(results)
        _update_failure_stats(props, results)
        self.report({'INFO'}, f"Phase3={phase3_done} + Resolver: {props.last_summary}")
        return {'FINISHED'}


class MAT_OT_AnalyzeMaterialResolution(bpy.types.Operator):
    bl_idname = "fmodel.analyze_material_resolution"
    bl_label = "分析材质解析"
    bl_options = {'REGISTER', 'UNDO'}
    mode: bpy.props.EnumProperty(items=[('ACTIVE', "选中", ""), ('BATCH', "全场景", "")], default='ACTIVE')

    def execute(self, context):
        props = context.scene.fmodel_material
        targets = _get_mesh_targets(context, self.mode)
        if not targets:
            self.report({'WARNING'}, "请选中网格对象")
            return {'CANCELLED'}
        tex_dir = bpy.path.abspath(props.umodel_tex_dir) if props.umodel_tex_dir else ""
        mat_dir = bpy.path.abspath(props.umodel_mat_path) if props.umodel_mat_path else ""
        results = resolve_objects_materials_with_options(targets, tex_dir, mat_dir, props.resolver_style, analyze_only=True)
        props.last_summary = format_summary(results)
        _update_failure_stats(props, results)
        self.report({'INFO'}, f"分析完成: {props.last_summary}")
        return {'FINISHED'}


class MAT_OT_ApplyMaterialResolutionV2(bpy.types.Operator):
    bl_idname = "fmodel.apply_material_resolution_v2"
    bl_label = "应用Resolver v2"
    bl_options = {'REGISTER', 'UNDO'}
    mode: bpy.props.EnumProperty(items=[('ACTIVE', "选中", ""), ('BATCH', "全场景", "")], default='ACTIVE')

    def execute(self, context):
        props = context.scene.fmodel_material
        targets = _get_mesh_targets(context, self.mode)
        if not targets:
            self.report({'WARNING'}, "请选中网格对象")
            return {'CANCELLED'}
        tex_dir = bpy.path.abspath(props.umodel_tex_dir) if props.umodel_tex_dir else ""
        mat_dir = bpy.path.abspath(props.umodel_mat_path) if props.umodel_mat_path else ""
        results = resolve_objects_materials_with_options(targets, tex_dir, mat_dir, props.resolver_style, analyze_only=False, strict_mode=props.strict_mode)
        props.last_summary = format_summary(results)
        _update_failure_stats(props, results)
        self.report({'INFO'}, f"应用完成: {props.last_summary}")
        return {'FINISHED'}


class MAT_OT_ExportMaterialReport(bpy.types.Operator):
    bl_idname = "fmodel.export_material_report"
    bl_label = "导出材质报告"
    bl_options = {'REGISTER', 'UNDO'}
    mode: bpy.props.EnumProperty(items=[('ACTIVE', "选中", ""), ('BATCH', "全场景", "")], default='BATCH')

    def execute(self, context):
        props = context.scene.fmodel_material
        targets = _get_mesh_targets(context, self.mode)
        if not targets:
            self.report({'WARNING'}, "请选中网格对象")
            return {'CANCELLED'}
        tex_dir = bpy.path.abspath(props.umodel_tex_dir) if props.umodel_tex_dir else ""
        mat_dir = bpy.path.abspath(props.umodel_mat_path) if props.umodel_mat_path else ""
        results = resolve_objects_materials_with_options(targets, tex_dir, mat_dir, props.resolver_style, analyze_only=True)
        out_path = bpy.path.abspath(props.report_out_path) if props.report_out_path else bpy.path.abspath("//MaterialResolveReport.json")
        saved = export_report_json(results, out_path)
        props.last_report_path = saved
        props.last_summary = format_summary(results)
        _update_failure_stats(props, results)
        self.report({'INFO'}, f"报告已导出: {saved}")
        return {'FINISHED'}


class MAT_OT_OpenMaterialReport(bpy.types.Operator):
    bl_idname = "fmodel.open_material_report"
    bl_label = "打开报告"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        import subprocess, sys
        props = context.scene.fmodel_material
        path = props.last_report_path or (bpy.path.abspath(props.report_out_path) if props.report_out_path else "")
        if not path or not os.path.exists(path):
            self.report({'WARNING'}, "报告文件不存在，请先导出")
            return {'CANCELLED'}
        try:
            if sys.platform == 'win32':
                os.startfile(path)
            elif sys.platform == 'darwin':
                subprocess.Popen(['open', path])
            else:
                subprocess.Popen(['xdg-open', path])
        except Exception as e:
            self.report({'ERROR'}, f"无法打开报告: {e}")
            return {'CANCELLED'}
        return {'FINISHED'}
