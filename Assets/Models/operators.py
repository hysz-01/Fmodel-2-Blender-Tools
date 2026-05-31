# FModel_Tools/Assets/Models/operators.py
# 角色模型操作符 — 保存、导入、预览管理

import bpy
import os
import json
import shutil
import re


# ============================================================
# 工具函数
# ============================================================

def get_model_dir(context):
    """获取模型存储目录 — 优先使用选中的资产库路径"""
    # 检查是否有选中的资产库
    if hasattr(context.scene, "fmodel_assets"):
        props = context.scene.fmodel_assets
        if len(props.project_libs) > 0 and props.active_lib_index < len(props.project_libs):
            lib = props.project_libs[props.active_lib_index]
            if lib.path:
                abs_path = bpy.path.abspath(lib.path)
                # 如果是目录，直接使用
                if os.path.isdir(abs_path):
                    return abs_path
                # 如果是 .blend，使用其父目录
                if abs_path.lower().endswith('.blend'):
                    return os.path.dirname(abs_path)

    # 回退到配置的模型目录
    if hasattr(context.scene, "fmodel_model_assets"):
        model_dir = context.scene.fmodel_model_assets.model_dir
        if model_dir:
            return bpy.path.abspath(model_dir)

    # 默认目录
    if bpy.data.filepath:
        return os.path.join(os.path.dirname(bpy.data.filepath), "Models")
    return "//Models"


def find_preview_image(model_dir, model_name):
    """查找模型预览图"""
    preview_dir = os.path.join(model_dir, ".previews")
    if not os.path.isdir(preview_dir):
        return ""
    for ext in ['.png', '.jpg', '.jpeg', '.webp']:
        path = os.path.join(preview_dir, f"{model_name}_preview{ext}")
        if os.path.exists(path):
            return path
    return ""


def export_bone_mapping(armature):
    """导出骨骼映射字典"""
    bones = {}
    for bone in armature.data.bones:
        bones[bone.name] = {
            "head": [round(v, 6) for v in bone.head_local],
            "tail": [round(v, 6) for v in bone.tail_local],
            "parent": bone.parent.name if bone.parent else None,
            "length": round(bone.length, 6),
        }
    return {
        "armature_object": armature.name,
        "armature_data": armature.data.name,
        "bone_count": len(bones),
        "bones": bones,
    }


# ============================================================
# 保存模型
# ============================================================

def save_model_logic(armature, out_dir, model_name, save_preview=True):
    """保存模型的核心逻辑 — 可被 Pipeline 和操作符调用

    返回: True/False
    """
    if not armature or armature.type != 'ARMATURE':
        return False

    model_name = model_name or armature.name
    os.makedirs(out_dir, exist_ok=True)

    prefix = model_name + "__"

    # 创建专用集合
    coll = bpy.data.collections.new(model_name)
    bpy.context.scene.collection.children.link(coll)

    # 复制骨架（带前缀）
    bpy.ops.object.select_all(action='DESELECT')
    armature.select_set(True)
    bpy.context.view_layer.objects.active = armature
    bpy.ops.object.duplicate()
    dup_arm = bpy.context.active_object
    dup_arm.name = prefix + armature.name
    dup_arm.data.name = prefix + armature.data.name

    datablocks = {dup_arm, dup_arm.data, coll}
    coll.objects.link(dup_arm)
    for c in list(dup_arm.users_collection):
        if c != coll:
            c.objects.unlink(dup_arm)

    # 收集子网格和材质
    for child in dup_arm.children:
        if child.type == 'MESH':
            child.name = prefix + child.name
            child.data.name = prefix + child.data.name
            datablocks.add(child)
            datablocks.add(child.data)
            coll.objects.link(child)
            for c in list(child.users_collection):
                if c != coll:
                    c.objects.unlink(child)
            if child.data.materials:
                for mat in child.data.materials:
                    if mat:
                        mat.name = prefix + mat.name
                        datablocks.add(mat)

    # 写入 _mesh.blend
    mesh_blend = os.path.join(out_dir, f"{model_name}_mesh.blend")
    bpy.data.libraries.write(filepath=mesh_blend, datablocks=datablocks, fake_user=True)

    # 导出骨骼映射
    bone_data = export_bone_mapping(armature)
    bone_path = os.path.join(out_dir, f"{model_name}_bones.json")
    with open(bone_path, 'w', encoding='utf-8') as f:
        json.dump(bone_data, f, ensure_ascii=False, indent=2)

    # 写入模型元数据
    mesh_count = sum(1 for c in armature.children if c.type == 'MESH')
    metadata = {
        "name": model_name,
        "armature_object": armature.name,
        "armature_data": armature.data.name,
        "bone_count": len(armature.data.bones),
        "mesh_count": mesh_count,
        "saved_at": __import__('datetime').datetime.now().isoformat(),
    }
    meta_path = os.path.join(out_dir, f"{model_name}.json")
    with open(meta_path, 'w', encoding='utf-8') as f:
        json.dump(metadata, f, ensure_ascii=False, indent=2)

    # 生成预览图（在删除副本前执行，否则无 active object）
    if save_preview:
        try:
            bpy.ops.fmodel.capture_model_preview(
                model_name=model_name,
                model_dir=out_dir
            )
        except Exception:
            pass

    # 清理副本
    bpy.ops.object.select_all(action='DESELECT')
    for obj in list(coll.objects):
        obj.select_set(True)
    bpy.ops.object.delete()
    bpy.data.collections.remove(coll)

    return True


class ASSET_OT_SaveModel(bpy.types.Operator):
    """保存角色模型到资产库"""
    bl_idname = "fmodel.save_model"
    bl_label = "保存模型"
    bl_options = {'REGISTER', 'UNDO'}

    model_name: bpy.props.StringProperty(name="名称", default="")
    model_dir: bpy.props.StringProperty(name="输出目录", subtype='DIR_PATH', default="")
    save_preview: bpy.props.BoolProperty(name="生成预览图", default=True)

    @classmethod
    def poll(cls, context):
        return context.active_object and context.active_object.type == 'ARMATURE'

    def invoke(self, context, event):
        arm = context.active_object
        self.model_name = arm.name
        self.model_dir = get_model_dir(context)
        return context.window_manager.invoke_props_dialog(self)

    def draw(self, context):
        layout = self.layout
        layout.prop(self, "model_name", text="名称")
        layout.prop(self, "model_dir", text="目录")
        layout.prop(self, "save_preview", icon='CAMERA_DATA')

        # 显示当前选中的资产库
        if hasattr(context.scene, "fmodel_assets"):
            props = context.scene.fmodel_assets
            if len(props.project_libs) > 0 and props.active_lib_index < len(props.project_libs):
                lib = props.project_libs[props.active_lib_index]
                if lib.path:
                    layout.label(text=f"资产库: {lib.name}", icon='LINKED')

    def execute(self, context):
        arm = context.active_object
        if not arm or arm.type != 'ARMATURE':
            self.report({'ERROR'}, "请选中骨架")
            return {'CANCELLED'}

        model_name = self.model_name or arm.name
        out_dir = bpy.path.abspath(self.model_dir or get_model_dir(context))

        success = save_model_logic(arm, out_dir, model_name, self.save_preview)
        if success:
            self.report({'INFO'}, f"已保存模型: {model_name}")
            return {'FINISHED'}
        else:
            self.report({'ERROR'}, "保存模型失败")
            return {'CANCELLED'}


# ============================================================
# 导入模型
# ============================================================

class ASSET_OT_ImportModel(bpy.types.Operator):
    """从资产库导入角色模型"""
    bl_idname = "fmodel.import_model"
    bl_label = "导入模型"
    bl_options = {'REGISTER', 'UNDO'}

    model_name: bpy.props.StringProperty()
    model_dir: bpy.props.StringProperty()

    def execute(self, context):
        model_name = self.model_name
        model_dir = bpy.path.abspath(self.model_dir)

        if not model_name or not model_dir:
            self.report({'ERROR'}, "请指定模型")
            return {'CANCELLED'}

        mesh_blend = os.path.join(model_dir, f"{model_name}_mesh.blend")
        if not os.path.exists(mesh_blend):
            self.report({'ERROR'}, f"找不到文件: {mesh_blend}")
            return {'CANCELLED'}

        try:
            with bpy.data.libraries.load(mesh_blend, link=True) as (df, dt):
                dt.objects = list(df.objects)
                dt.collections = list(df.collections)

            # 链接集合到场景
            linked = False
            for coll in dt.collections:
                if coll:
                    context.scene.collection.children.link(coll)
                    linked = True

            # 如果没有集合，手动链接对象
            if not linked:
                for obj in dt.objects:
                    if obj:
                        context.collection.objects.link(obj)

            self.report({'INFO'}, f"已导入模型: {model_name}")
        except Exception as e:
            self.report({'ERROR'}, f"导入失败: {e}")
            return {'CANCELLED'}

        return {'FINISHED'}


# ============================================================
# 预览图操作
# ============================================================

class ASSET_OT_CaptureModelPreview(bpy.types.Operator):
    """截图当前视口作为模型预览图"""
    bl_idname = "fmodel.capture_model_preview"
    bl_label = "截图预览"
    bl_options = {'REGISTER'}

    model_name: bpy.props.StringProperty(default="")
    model_dir: bpy.props.StringProperty(default="")

    def execute(self, context):
        import tempfile

        model_name = self.model_name or (context.active_object.name if context.active_object else "")
        model_dir = bpy.path.abspath(self.model_dir or get_model_dir(context))

        if not model_name:
            self.report({'ERROR'}, "请选中一个对象")
            return {'CANCELLED'}

        preview_dir = os.path.join(model_dir, ".previews")
        os.makedirs(preview_dir, exist_ok=True)

        tmp_dir = tempfile.mkdtemp()
        tmp_path = os.path.join(tmp_dir, "preview.png")

        area = next((a for a in context.screen.areas if a.type == 'VIEW_3D'), None)
        if not area:
            self.report({'ERROR'}, "找不到 3D 视口")
            return {'CANCELLED'}

        region = next((r for r in area.regions if r.type == 'WINDOW'), None)
        if not region:
            self.report({'ERROR'}, "找不到视口区域")
            return {'CANCELLED'}

        with context.temp_override(area=area, region=region):
            bpy.ops.screen.screenshot(filepath=tmp_path)

        dest = os.path.join(preview_dir, f"{model_name}_preview.png")
        shutil.copy2(tmp_path, dest)
        try:
            os.remove(tmp_path)
            os.rmdir(tmp_dir)
        except (OSError, IOError) as e:
            # 清理临时文件失败，不影响截图功能
            pass

        self.report({'INFO'}, f"已截图预览: {model_name}")
        return {'FINISHED'}


class ASSET_OT_UploadModelPreview(bpy.types.Operator):
    """为模型上传自定义预览图"""
    bl_idname = "fmodel.upload_model_preview"
    bl_label = "上传预览图"
    bl_options = {'REGISTER'}

    filepath: bpy.props.StringProperty(subtype='FILE_PATH')
    filter_glob: bpy.props.StringProperty(default='*.png;*.jpg;*.jpeg;*.webp', options={'HIDDEN'})

    @classmethod
    def poll(cls, context):
        return bool(context.active_object)

    def execute(self, context):
        if not self.filepath or not os.path.exists(self.filepath):
            return {'CANCELLED'}

        model_name = context.active_object.name
        model_dir = get_model_dir(context)
        preview_dir = os.path.join(model_dir, ".previews")
        os.makedirs(preview_dir, exist_ok=True)

        ext = os.path.splitext(self.filepath)[1].lower()
        dest = os.path.join(preview_dir, f"{model_name}_preview{ext}")
        shutil.copy2(self.filepath, dest)

        self.report({'INFO'}, f"已设置预览图: {model_name}")
        return {'FINISHED'}

    def invoke(self, context, event):
        context.window_manager.fileselect_add(self)
        return {'RUNNING_MODAL'}


class ASSET_OT_ImportModelWithPreview(bpy.types.Operator):
    """打开模型选择菜单（带预览图）"""
    bl_idname = "fmodel.open_model_browser"
    bl_label = "选择模型"
    bl_options = {'REGISTER'}

    def execute(self, context):
        bpy.ops.wm.call_menu(name="FMODEL_MT_model_browser")
        return {'FINISHED'}


class ASSET_OT_OpenModelSelector(bpy.types.Operator):
    """打开模型选择弹窗（带大图预览）"""
    bl_idname = "fmodel.open_model_selector"
    bl_label = "选择并导入模型"
    bl_options = {'REGISTER', 'UNDO'}

    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self, width=400)

    def draw(self, context):
        layout = self.layout
        models = _scan_models(context)

        if not models:
            layout.label(text="没有已保存的模型", icon='INFO')
            layout.label(text="请先使用'保存模型'功能")
            return

        layout.label(text=f"{len(models)} 个模型", icon='OUTLINER_OB_ARMATURE')
        layout.separator()

        for model in models:
            box = layout.box()
            icon_id = _get_preview_icon(model["preview"])
            meta = model["meta"]

            row = box.row(align=True)

            # 预览图
            col_icon = row.column()
            if icon_id:
                col_icon.template_icon(icon_value=icon_id, scale=3.0)
            else:
                col_icon.template_icon(icon_value=0, scale=3.0)

            # 信息
            col_info = row.column()
            col_info.scale_y = 0.85
            col_info.label(text=model["name"], icon='OUTLINER_OB_ARMATURE')
            if meta:
                parts = []
                if meta.get("bone_count"): parts.append(f"{meta['bone_count']}骨")
                if meta.get("mesh_count"): parts.append(f"{meta['mesh_count']}网格")
                if parts:
                    col_info.label(text=" / ".join(parts))
                saved = meta.get("saved_at", "")
                if saved:
                    col_info.label(text=f"保存: {saved[:10]}")

            # 导入按钮
            col_ops = row.column()
            op_imp = col_ops.operator("fmodel.import_model_from_browser", text="导入", icon='IMPORT')
            op_imp.model_name = model["name"]
            op_imp.model_dir = model["path"]

    def execute(self, context):
        return {'FINISHED'}


# ============================================================
# 模型浏览菜单（大图卡片）
# ============================================================

# 预览图标缓存
_preview_icons = None
_preview_cache = {}


def _get_preview_icon(image_path):
    global _preview_icons, _preview_cache
    if _preview_icons is None:
        _preview_icons = bpy.utils.previews.new()
    if not image_path or not os.path.exists(image_path):
        return 0
    if image_path in _preview_cache:
        return _preview_cache[image_path]
    try:
        thumb = _preview_icons.load(image_path, image_path, 'IMAGE')
        _preview_cache[image_path] = thumb.icon_id
        return thumb.icon_id
    except Exception:
        _preview_cache[image_path] = 0
        return 0


def _scan_models(context):
    """扫描模型目录，返回模型列表"""
    model_dir = get_model_dir(context)
    if not os.path.isdir(model_dir):
        return []
    models = []
    for f in os.listdir(model_dir):
        if f.endswith('_mesh.blend'):
            name = f.replace('_mesh.blend', '')
            meta_path = os.path.join(model_dir, f"{name}.json")
            preview_path = find_preview_image(model_dir, name)
            meta = {}
            if os.path.exists(meta_path):
                try:
                    with open(meta_path, 'r') as mf:
                        meta = json.load(mf)
                except (json.JSONDecodeError, IOError) as e:
                    # 元数据读取失败，使用空字典
                    pass
            models.append({
                "name": name,
                "path": model_dir,
                "meta": meta,
                "preview": preview_path,
            })
    return sorted(models, key=lambda m: m["name"])


class FMODEL_MT_ModelBrowser(bpy.types.Menu):
    """模型浏览菜单"""
    bl_label = "选择模型"
    bl_idname = "FMODEL_MT_model_browser"

    def draw(self, context):
        layout = self.layout
        models = _scan_models(context)

        if not models:
            layout.label(text="没有已保存的模型", icon='INFO')
            layout.label(text="请先使用'保存模型'功能")
            return

        for model in models:
            icon_id = _get_preview_icon(model["preview"])
            meta = model["meta"]
            desc = ""
            if meta:
                bones = meta.get("bone_count", 0)
                meshes = meta.get("mesh_count", 0)
                desc = f"  ({bones}骨/{meshes}网格)"

            op = layout.operator(
                "fmodel.import_model_from_browser",
                text=f"{model['name']}{desc}",
                icon_value=icon_id if icon_id else 0
            )
            op.model_name = model["name"]
            op.model_dir = model["path"]


class ASSET_OT_ImportModelFromBrowser(bpy.types.Operator):
    """从浏览器导入模型"""
    bl_idname = "fmodel.import_model_from_browser"
    bl_label = "导入模型"
    bl_options = {'REGISTER', 'UNDO'}

    model_name: bpy.props.StringProperty()
    model_dir: bpy.props.StringProperty()

    def execute(self, context):
        mesh_blend = os.path.join(self.model_dir, f"{self.model_name}_mesh.blend")
        if not os.path.exists(mesh_blend):
            self.report({'ERROR'}, f"找不到: {mesh_blend}")
            return {'CANCELLED'}

        try:
            with bpy.data.libraries.load(mesh_blend, link=True) as (df, dt):
                dt.objects = list(df.objects)
                dt.collections = list(df.collections)
            for coll in dt.collections:
                if coll:
                    context.scene.collection.children.link(coll)
            if not dt.collections:
                for obj in dt.objects:
                    if obj:
                        context.collection.objects.link(obj)
            self.report({'INFO'}, f"已导入: {self.model_name}")
        except Exception as e:
            self.report({'ERROR'}, f"导入失败: {e}")
            return {'CANCELLED'}
        return {'FINISHED'}


# ============================================================
# 删除模型
# ============================================================

class ASSET_OT_DeleteModel(bpy.types.Operator):
    """从资产库中删除模型"""
    bl_idname = "fmodel.delete_model"
    bl_label = "删除模型"
    bl_options = {'REGISTER', 'UNDO'}

    model_name: bpy.props.StringProperty()
    model_dir: bpy.props.StringProperty()

    def invoke(self, context, event):
        return context.window_manager.invoke_confirm(self, event)

    def execute(self, context):
        model_dir = bpy.path.abspath(self.model_dir or get_model_dir(context))
        name = self.model_name

        removed = []
        for suffix in ['_mesh.blend', '_bones.json', '.json']:
            path = os.path.join(model_dir, f"{name}{suffix}")
            if os.path.exists(path):
                os.remove(path)
                removed.append(suffix)

        preview_dir = os.path.join(model_dir, ".previews")
        for ext in ['.png', '.jpg', '.jpeg', '.webp']:
            path = os.path.join(preview_dir, f"{name}_preview{ext}")
            if os.path.exists(path):
                os.remove(path)

        if removed:
            self.report({'INFO'}, f"已删除模型: {name}")
        else:
            self.report({'WARNING'}, f"未找到: {name}")
        return {'FINISHED'}


# ============================================================
# 注册
# ============================================================

_classes = (
    ASSET_OT_SaveModel,
    ASSET_OT_CaptureModelPreview,
    ASSET_OT_UploadModelPreview,
    ASSET_OT_ImportModelWithPreview,
    ASSET_OT_OpenModelSelector,
    FMODEL_MT_ModelBrowser,
    ASSET_OT_ImportModelFromBrowser,
    ASSET_OT_DeleteModel,
)


def register():
    for cls in _classes:
        bpy.utils.register_class(cls)


def unregister():
    global _preview_icons, _preview_cache
    if _preview_icons is not None:
        bpy.utils.previews.remove(_preview_icons)
        _preview_icons = None
    _preview_cache.clear()

    for cls in reversed(_classes):
        bpy.utils.unregister_class(cls)
