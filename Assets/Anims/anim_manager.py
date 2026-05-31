# FModel_Tools/Assets/Anims/anim_manager.py
# 动画管理器 — 树形数据结构、扫描引擎、预览操作符

import bpy
import os
import json
import re
import hashlib
import shutil
from datetime import datetime
from ...core.i18n import t
from bpy.app.handlers import persistent
import bpy.utils.previews

from ...core import (
    SourceType,
    get_or_create_catalog_uuid, ensure_dir,
    DictionaryManifest, SkeletonNode, FolderNode, AnimationEntry
)


# ============================================================
# 图标管理
# ============================================================

if "fmodel_custom_icons" not in locals():
    fmodel_custom_icons = None

_PATH_EXISTS_CACHE = {}
# 使用简单的锁机制保护全局变量
import threading
_global_lock = threading.RLock()


def get_custom_icon(rel_path, blend_path):
    """获取自定义图标"""
    global fmodel_custom_icons, _PATH_EXISTS_CACHE

    # 使用锁保护并发访问
    with _global_lock:
        if fmodel_custom_icons is None:
            fmodel_custom_icons = bpy.utils.previews.new()

        if not rel_path:
            return 0

        abs_path = os.path.normpath(os.path.join(os.path.dirname(blend_path), rel_path))

        if abs_path in fmodel_custom_icons:
            return fmodel_custom_icons[abs_path].icon_id

    with _global_lock:
        if abs_path in _PATH_EXISTS_CACHE and not _PATH_EXISTS_CACHE[abs_path]:
            return 0

        if not os.path.exists(abs_path):
            _PATH_EXISTS_CACHE[abs_path] = False
            return 0

        _PATH_EXISTS_CACHE[abs_path] = True
        try:
            thumb = fmodel_custom_icons.load(abs_path, abs_path, 'IMAGE')
            return thumb.icon_id
        except Exception:
            _PATH_EXISTS_CACHE[abs_path] = False
            return 0


def clear_custom_icons():
    """清理自定义图标"""
    global fmodel_custom_icons
    with _global_lock:
        if fmodel_custom_icons is not None:
            bpy.utils.previews.remove(fmodel_custom_icons)
            fmodel_custom_icons = None


# ============================================================
# 数据结构
# ============================================================

class AnimTreeItem(bpy.types.PropertyGroup):
    """动画树形项目 - 统一的数据结构"""
    name: bpy.props.StringProperty()
    item_type: bpy.props.StringProperty()  # 'LIBRARY' | 'FOLDER' | 'ANIM' | 'MODEL'
    lib_type: bpy.props.StringProperty()   # 'DIRECTORY' | 'BLEND_ANIM' | 'BLEND_MODEL'
    node_id: bpy.props.StringProperty()
    parent_id: bpy.props.StringProperty()
    skeleton: bpy.props.StringProperty()
    blend_path: bpy.props.StringProperty()
    action_name: bpy.props.StringProperty()
    thumb_path: bpy.props.StringProperty()
    depth: bpy.props.IntProperty(default=0)
    is_expanded: bpy.props.BoolProperty(default=False)
    anim_count: bpy.props.IntProperty(default=0)
    volume_count: bpy.props.IntProperty(default=0)


class SkeletonItem(bpy.types.PropertyGroup):
    """骨架项目"""
    name: bpy.props.StringProperty()


def get_dynamic_skeletons(self, context):
    """动态获取骨架列表"""
    try:
        manager = getattr(context.scene, "fmodel_anim_manager", None)
        if not manager or not manager.skeleton_items:
            return [("NONE", "无资产数据", "")]
        items = [("ALL", "显示所有骨架", "")]
        for item in manager.skeleton_items:
            items.append((item.name, item.name, ""))
        return items if items else [("NONE", "无资产数据", "")]
    except Exception:
        return [("NONE", "获取出错", "")]


class AnimManagerProps(bpy.types.PropertyGroup):
    """动画管理器属性 - 统一的属性组"""
    tree_items: bpy.props.CollectionProperty(type=AnimTreeItem)
    skeleton_items: bpy.props.CollectionProperty(type=SkeletonItem)
    active_skeleton: bpy.props.EnumProperty(name="目标骨架", items=lambda s, c: get_dynamic_skeletons(s, c))
    search_filter: bpy.props.StringProperty(name="搜索", description="全局搜索动作或文件夹名称", default="")
    
    # 显示模式
    display_mode: bpy.props.EnumProperty(
        name="布局",
        items=[('TREE', "一体化", ""), ('DETAIL_H', "左右分栏", ""), ('DETAIL_V', "上下分栏", "")],
        default='TREE'
    )
    
    # 导入/引用模式
    import_mode: bpy.props.EnumProperty(
        name="引用模式",
        items=[('LINK', "链接 (Link)", "", 'LINKED', 0), ('APPEND', "追加 (Append)", "", 'APPEND_BLEND', 1)],
        default='LINK'
    )
    
    # 应用模式
    apply_method: bpy.props.EnumProperty(
        name="应用模式",
        items=[('REPLACE', "替换预览", "", 'RECOVER_LAST', 0), ('APPEND_NLA', "拼接 NLA", "", 'NLA', 1)],
        default='REPLACE'
    )

    nla_insert_mode: bpy.props.EnumProperty(
        name="NLA部署",
        items=[
            ('END', "末尾追加", "追加到最后一个条带后"),
            ('CURRENT', "当前帧插入", "从当前帧开始插入"),
            ('OVERWRITE_TRACK', "覆盖当前范围", "在目标轨道删除重叠条带后插入"),
        ],
        default='END'
    )
    nla_overwrite_scope: bpy.props.EnumProperty(
        name="覆盖策略",
        items=[
            ('ALL_OVERLAPS', "删除全部重叠", "删除该轨道上当前范围内所有重叠条带"),
            ('SAME_NAME_ONLY', "仅删同名重叠", "仅删除与当前动作同名且重叠的条带"),
        ],
        default='ALL_OVERLAPS'
    )
    nla_auto_focus_new_strip: bpy.props.BoolProperty(
        name="部署后聚焦新条带",
        default=True
    )
    
    # 布局参数
    split_factor: bpy.props.FloatProperty(name="分栏比例", default=0.5, min=0.1, max=0.9)
    list_rows: bpy.props.IntProperty(name="统一高度(行)", default=8, min=3, max=30)
    
    # 网格视图
    show_as_grid: bpy.props.BoolProperty(name="平铺视图", default=False)
    grid_columns: bpy.props.IntProperty(name="网格列数", default=2, min=1, max=8)
    grid_row_count: bpy.props.IntProperty(name="网格行数", default=2, min=1, max=8)
    grid_icon_scale: bpy.props.FloatProperty(name="卡片尺寸", default=6.0, min=3.0, max=15.0)
    grid_page: bpy.props.IntProperty(name="当前页", default=1, min=1)
    
    # 索引
    active_item_index: bpy.props.IntProperty(default=0)
    active_folder_index: bpy.props.IntProperty(default=0)


# ============================================================
# 辅助函数
# ============================================================

def merge_dict(target, source, blend_path):
    """合并字典结构"""
    for k, v in source.items():
        if k == "__actions__":
            if "__actions__" not in target:
                target["__actions__"] = []
            for act in v:
                if isinstance(act, list):
                    target["__actions__"].append((act[0], blend_path, act[1] if len(act) > 1 else ""))
                else:
                    target["__actions__"].append((act, blend_path, ""))
        elif isinstance(v, dict):
            if k not in target:
                target[k] = {}
            merge_dict(target[k], v, blend_path)


def traverse_tree(skel, parent_id, current_dict, depth, manager):
    """遍历树结构"""
    for key in sorted(current_dict.keys()):
        if key == "__actions__":
            continue
        folder_id = f"{parent_id}/{key}" if parent_id else key
        item = manager.tree_items.add()
        item.name = key
        item.item_type = 'FOLDER'
        item.node_id = folder_id
        item.parent_id = parent_id
        item.skeleton = skel
        item.depth = depth
        item.is_expanded = False
        traverse_tree(skel, folder_id, current_dict[key], depth + 1, manager)
    
    if "__actions__" in current_dict:
        for act_name, blend_path, thumb_path in sorted(current_dict["__actions__"], key=lambda x: x[0]):
            item = manager.tree_items.add()
            item.name = act_name
            item.item_type = 'ANIM'
            item.node_id = f"{parent_id}/{act_name}"
            item.parent_id = parent_id
            item.skeleton = skel
            item.blend_path = blend_path
            item.action_name = act_name
            item.depth = depth
            item.thumb_path = thumb_path


def _count_actions_recursive(tree_dict):
    """递归统计manifest树中的动作数量"""
    if not isinstance(tree_dict, dict):
        return 0
    total = 0
    for k, v in tree_dict.items():
        if k == "__actions__" and isinstance(v, list):
            total += len(v)
        elif isinstance(v, dict):
            total += _count_actions_recursive(v)
    return total


# ============================================================
# 操作符
# ============================================================

_VOL_PATTERN = re.compile(r'(.+)_Vol_\d+$', re.IGNORECASE)


def _get_base_name(filename):
    """获取文件名基础名（去除 _Vol_N 后缀）"""
    name = os.path.splitext(filename)[0]
    m = _VOL_PATTERN.match(name)
    return m.group(1) if m else name


def _scan_library_directory(abs_dir, lib_name):
    """扫描目录，返回 (blend_entries, model_entries)

    blend_entries: [(base_name, [blend_paths], anim_count), ...]  合并分卷
    model_entries: [(name, path), ...]
    """
    if not os.path.isdir(abs_dir):
        return [], []

    # 收集所有 blend 文件
    anim_groups = {}  # base_name -> [blend_paths]
    anim_counts = {}  # base_name -> total_anim_count
    model_entries = []

    for f in os.listdir(abs_dir):
        if not f.lower().endswith('.blend'):
            continue

        full_path = os.path.join(abs_dir, f)

        # 模型文件
        if f.endswith('_mesh.blend'):
            model_name = f.replace('_mesh.blend', '')
            model_entries.append((model_name, full_path))
            continue

        # 使用与blend同名manifest（支持分卷）
        base = _get_base_name(f)
        manifest_name = f"{os.path.splitext(f)[0]}_manifest.json"
        manifest_path = os.path.join(abs_dir, manifest_name)
        if not os.path.exists(manifest_path):
            continue

        if base not in anim_groups:
            anim_groups[base] = []
            anim_counts[base] = 0
        anim_groups[base].append(full_path)

        # 统计该分卷动作数量（递归）
        try:
            with open(manifest_path, 'r', encoding='utf-8') as mf:
                data = json.load(mf)
                for skel, tree in data.items():
                    if skel == "__processed_sources__":
                        continue
                    if isinstance(tree, dict):
                        anim_counts[base] += _count_actions_recursive(tree)
        except Exception:
            pass

    blend_entries = []
    for base, paths in sorted(anim_groups.items()):
        blend_entries.append((base, paths, anim_counts.get(base, 0)))

    return blend_entries, model_entries


def _scan_single_blend(blend_path, lib_name):
    """扫描单个 .blend 文件中的 Action 数量"""
    count = 0
    try:
        with bpy.data.libraries.load(blend_path, link=True) as (df, dt):
            count = len(df.actions)
    except Exception:
        pass
    return count


class ANIM_OT_ScanAnims(bpy.types.Operator):
    """扫描动画库 - 构建库优先的树状视图"""
    bl_idname = "fmodel.scan_anims"
    bl_label = "扫描资产库"

    def execute(self, context):
        if not hasattr(context.scene, "fmodel_anim_manager"):
            self.report({'ERROR'}, t("动画管理器未初始化，请重载插件"))
            return {'CANCELLED'}
        if not hasattr(context.scene, "fmodel_assets"):
            self.report({'ERROR'}, t("资产系统未初始化，请重载插件"))
            return {'CANCELLED'}
        manager = context.scene.fmodel_anim_manager
        manager.active_item_index = 0
        manager.active_folder_index = 0
        manager.tree_items.clear()
        manager.skeleton_items.clear()

        props = context.scene.fmodel_assets

        # 初始化skeleton树用于跟踪已添加的skeleton
        skeleton_tree = {}

        for lib in props.project_libs:
            if not lib.path:
                continue
            abs_path = bpy.path.abspath(lib.path)

            if not os.path.exists(abs_path):
                continue

            # === 目录类型 ===
            if os.path.isdir(abs_path):
                # 创建 LIBRARY 条目
                lib_item = manager.tree_items.add()
                lib_item.name = lib.name
                lib_item.item_type = 'LIBRARY'
                lib_item.lib_type = 'DIRECTORY'
                lib_item.node_id = f"lib_{lib.name}"
                lib_item.blend_path = abs_path
                lib_item.depth = 0
                lib_item.is_expanded = True

                blend_entries, model_entries = _scan_library_directory(abs_path, lib.name)
                lib_item.anim_count = sum(e[2] for e in blend_entries)

                # 动画 .blend 条目
                for base_name, paths, anim_count in blend_entries:
                    entry = manager.tree_items.add()
                    entry.name = base_name
                    entry.item_type = 'ANIM_LIB'  # 库设置用
                    entry.lib_type = 'BLEND_ANIM'
                    entry.node_id = f"anim_{lib.name}_{base_name}"
                    entry.parent_id = lib_item.node_id
                    entry.blend_path = paths[0]
                    entry.depth = 1
                    entry.anim_count = anim_count
                    entry.volume_count = len(paths)

                    # 读取所有分卷manifest并合并后生成树
                    merged_by_skel = {}
                    for blend_path in paths:
                        manifest_path = os.path.splitext(blend_path)[0] + "_manifest.json"
                        if not os.path.exists(manifest_path):
                            continue
                        try:
                            with open(manifest_path, 'r', encoding='utf-8') as mf:
                                data = json.load(mf)
                            for skel, folder_tree in data.items():
                                if skel == "__processed_sources__" or not isinstance(folder_tree, dict):
                                    continue
                                if skel not in merged_by_skel:
                                    merged_by_skel[skel] = {}
                                merge_dict(merged_by_skel[skel], folder_tree, blend_path)
                        except Exception:
                            pass

                    for skel, folder_tree in merged_by_skel.items():
                        if folder_tree:
                            traverse_tree(skel, entry.node_id, folder_tree, 2, manager)
                            if skel not in skeleton_tree:
                                manager.skeleton_items.add().name = skel
                                skeleton_tree[skel] = True

                # 模型 .blend 条目
                for model_name, model_path in model_entries:
                    entry = manager.tree_items.add()
                    entry.name = model_name
                    entry.item_type = 'MODEL'
                    entry.lib_type = 'BLEND_MODEL'
                    entry.node_id = f"model_{lib.name}_{model_name}"
                    entry.parent_id = lib_item.node_id
                    entry.blend_path = model_path
                    entry.depth = 1

            # === .blend 文件类型 ===
            elif abs_path.lower().endswith('.blend'):
                is_model = abs_path.endswith('_mesh.blend')
                lib_item = manager.tree_items.add()
                lib_item.name = lib.name
                lib_item.item_type = 'MODEL' if is_model else 'ANIM'
                lib_item.lib_type = 'BLEND_MODEL' if is_model else 'BLEND_ANIM'
                lib_item.node_id = f"lib_{lib.name}"
                lib_item.blend_path = abs_path
                lib_item.depth = 0
                if not is_model:
                    lib_item.anim_count = _scan_single_blend(abs_path, lib.name)

        return {'FINISHED'}


class ANIM_OT_ScanLocalAnims(bpy.types.Operator):
    """扫描本地动作（基于自定义属性）"""
    bl_idname = "fmodel.scan_local_anims"
    bl_label = "扫描本地动作"
    bl_options = {'REGISTER', 'UNDO'}
    
    def execute(self, context):
        manager = context.scene.fmodel_anim_manager
        manager.tree_items.clear()
        manager.skeleton_items.clear()
        
        global_tree = {}
        action_count = 0
        
        for action in bpy.data.actions:
            grp = action.get("SA_Group", "未分类资产 (Unassigned)")
            folder = action.get("SA_Folder", "Root")
            
            if grp not in global_tree:
                global_tree[grp] = {}
            
            current_level = global_tree[grp]
            if folder and folder not in ("Uncategorized", "Root", ""):
                parts = folder.split('/')
                for part in parts:
                    if part not in current_level:
                        current_level[part] = {}
                    current_level = current_level[part]
            
            if "__actions__" not in current_level:
                current_level["__actions__"] = []
            current_level["__actions__"].append((action.name, "", ""))
            action_count += 1
        
        for grp in sorted(global_tree.keys()):
            sk_item = manager.skeleton_items.add()
            sk_item.name = grp
            traverse_tree(grp, "", global_tree[grp], 0, manager)
        
        self.report({'INFO'}, f"扫描完成：共提取到 {action_count} 个本地动作。")
        return {'FINISHED'}


class ANIM_OT_ToggleFolder(bpy.types.Operator):
    """展开/折叠文件夹或资产库"""
    bl_idname = "fmodel.toggle_folder"
    bl_label = "展开/折叠"
    bl_options = {'INTERNAL'}
    node_id: bpy.props.StringProperty()
    
    def execute(self, context):
        manager = context.scene.fmodel_anim_manager
        for i, item in enumerate(manager.tree_items):
            if item.node_id == self.node_id and item.item_type in ('FOLDER', 'LIBRARY'):
                item.is_expanded = not item.is_expanded
                manager.active_folder_index = i
                break
        manager.grid_page = 1
        return {'FINISHED'}


class ANIM_OT_SelectGridItem(bpy.types.Operator):
    """选中网格项目"""
    bl_idname = "fmodel.select_grid_item"
    bl_label = "选中动作"
    bl_options = {'INTERNAL'}
    target_index: bpy.props.IntProperty()
    
    def execute(self, context):
        manager = context.scene.fmodel_anim_manager
        manager.active_item_index = self.target_index
        return {'FINISHED'}


class ANIM_OT_PreviewAnim(bpy.types.Operator):
    """预览动画"""
    bl_idname = "fmodel.preview_anim"
    bl_label = "预览动作"
    bl_options = {'REGISTER', 'UNDO'}
    target_node_id: bpy.props.StringProperty(default="")
    
    def execute(self, context):
        manager = getattr(context.scene, "fmodel_anim_manager", None)
        if not manager:
            return {'CANCELLED'}
        
        selected = None
        if self.target_node_id:
            for item in manager.tree_items:
                if item.node_id == self.target_node_id:
                    selected = item
                    break
        
        if not selected or selected.item_type != 'ANIM':
            return {'CANCELLED'}
        
        target_arm = context.active_object
        if not target_arm or target_arm.type != 'ARMATURE':
            self.report({'WARNING'}, t("请先在 3D 视图中选中目标骨架！"))
            return {'CANCELLED'}
        
        for i, item in enumerate(manager.tree_items):
            if item == selected:
                manager.active_item_index = i
                break
        
        action_name = selected.action_name
        blend_path = selected.blend_path
        use_link = (manager.import_mode == 'LINK')
        arm_name = target_arm.name
        
        try:
            arm = bpy.data.objects.get(arm_name)
            if not arm:
                return {'CANCELLED'}
            
            action = bpy.data.actions.get(action_name)
            
            if action and not use_link and action.library:
                try:
                    action.make_local()
                except Exception:
                    pass
            elif not action and blend_path:
                with bpy.data.libraries.load(blend_path, link=use_link) as (data_from, data_to):
                    if action_name in data_from.actions:
                        data_to.actions = [action_name]
                action = bpy.data.actions.get(action_name)
            
            if action:
                if not arm.animation_data:
                    arm.animation_data_create()
                arm.animation_data.action = action
                if action.frame_range:
                    context.scene.frame_start = int(action.frame_range[0])
                    context.scene.frame_end = int(action.frame_range[1])
                    context.scene.frame_current = int(action.frame_range[0])
        except Exception as e:
            self.report({'ERROR'}, f"预览加载失败: {e}")
        
        return {'FINISHED'}


class ANIM_OT_ApplyAnim(bpy.types.Operator):
    """应用动画"""
    bl_idname = "fmodel.apply_anim"
    bl_label = "应用动作"
    bl_options = {'REGISTER', 'UNDO'}
    target_node_id: bpy.props.StringProperty(default="")
    apply_method_override: bpy.props.EnumProperty(
        items=[
            ('AUTO', "Auto", "使用当前应用模式"),
            ('REPLACE', "Replace", "应用到骨架"),
            ('APPEND_NLA', "Append NLA", "部署到NLA轨道"),
        ],
        default='AUTO'
    )

    def _focus_new_strip(self, context, manager, anim_data, track, strip):
        if not manager.nla_auto_focus_new_strip:
            return

        for t in anim_data.nla_tracks:
            t.select = False
            for s in t.strips:
                s.select = False

        track.select = True
        strip.select = True
        anim_data.nla_tracks.active = track

        context.scene.frame_current = int(strip.frame_start)
        context.scene.frame_start = min(context.scene.frame_start, int(strip.frame_start))
        context.scene.frame_end = max(context.scene.frame_end, int(strip.frame_end))

        try:
            if hasattr(context.scene, "fmodel_nla_studio"):
                bpy.ops.fmodel.nla_refresh()

                studio = context.scene.fmodel_nla_studio
                target_index = -1
                best_delta = 10**9
                for i, item in enumerate(studio.items):
                    if item.track_name != track.name or item.strip_name != strip.name:
                        continue
                    delta = abs(float(item.frame_start) - float(strip.frame_start))
                    if delta < best_delta:
                        best_delta = delta
                        target_index = i

                if target_index >= 0:
                    studio.active_index = target_index

                studio.show_advanced_tools = True
                studio.handoff_message = (
                    f"已部署: {strip.name} | 轨道: {track.name} | "
                    f"范围: {int(strip.frame_start)}-{int(strip.frame_end)}"
                )
                studio.highlight_track_name = track.name
                studio.highlight_strip_name = strip.name
                studio.highlight_frame_start = float(strip.frame_start)
                studio.highlight_cycles = 2
        except Exception:
            pass
    
    def execute(self, context):
        target_arm = context.active_object
        manager = context.scene.fmodel_anim_manager
        
        selected = None
        if self.target_node_id:
            for item in manager.tree_items:
                if item.node_id == self.target_node_id:
                    selected = item
                    break
        else:
            if manager.tree_items and manager.active_item_index < len(manager.tree_items):
                selected = manager.tree_items[manager.active_item_index]
        
        if not selected or selected.item_type != 'ANIM':
            return {'CANCELLED'}
        
        use_link = (manager.import_mode == 'LINK')
        action = bpy.data.actions.get(selected.action_name)
        
        try:
            if action and not use_link and action.library:
                try:
                    action.make_local()
                except Exception:
                    pass
            elif not action and selected.blend_path:
                with bpy.data.libraries.load(selected.blend_path, link=use_link) as (data_from, data_to):
                    if selected.action_name in data_from.actions:
                        data_to.actions = [selected.action_name]
                action = bpy.data.actions.get(selected.action_name)
        except Exception as e:
            self.report({'ERROR'}, f"动作引用失败: {e}")
            return {'CANCELLED'}
        
        if action:
            if not target_arm.animation_data:
                target_arm.animation_data_create()
            anim_data = target_arm.animation_data
            
            method = manager.apply_method if self.apply_method_override == 'AUTO' else self.apply_method_override

            if method == 'REPLACE':
                if anim_data.nla_tracks:
                    for t in reversed(anim_data.nla_tracks):
                        anim_data.nla_tracks.remove(t)
                anim_data.action = action
                if action.frame_range:
                    context.scene.frame_start = int(action.frame_range[0])
                    context.scene.frame_end = int(action.frame_range[1])
                self.report({'INFO'}, f"[{manager.import_mode}] 已替换播放: {selected.action_name}")
            else:
                anim_data.action = None
                duration = 1.0
                if action.frame_range:
                    duration = max(1.0, float(action.frame_range[1] - action.frame_range[0]))

                insert_mode = manager.nla_insert_mode
                insert_frame = float(context.scene.frame_current)

                if anim_data.nla_tracks:
                    target_track = anim_data.nla_tracks[-1]
                else:
                    target_track = anim_data.nla_tracks.new()
                    target_track.name = "NLA_Track"

                if insert_mode == 'END':
                    if target_track.strips:
                        insert_frame = float(target_track.strips[-1].frame_end)
                    else:
                        insert_frame = 0.0
                elif insert_mode == 'CURRENT':
                    insert_frame = float(context.scene.frame_current)
                else:  # OVERWRITE_TRACK
                    insert_frame = float(context.scene.frame_current)
                    range_end = insert_frame + duration
                    overlaps = []
                    for s in target_track.strips:
                        if float(s.frame_start) < range_end and insert_frame < float(s.frame_end):
                            if manager.nla_overwrite_scope == 'ALL_OVERLAPS' or s.name == selected.action_name:
                                overlaps.append(s)
                    for s in reversed(overlaps):
                        target_track.strips.remove(s)

                track = target_track
                if not track.name:
                    track.name = selected.action_name
                strip = track.strips.new(selected.action_name, int(insert_frame), action)
                if strip and int(strip.frame_end) > context.scene.frame_end:
                    context.scene.frame_end = int(strip.frame_end)
                if strip:
                    self._focus_new_strip(context, manager, anim_data, track, strip)
                if manager.nla_insert_mode == 'OVERWRITE_TRACK':
                    overwrite_info = "删全部重叠" if manager.nla_overwrite_scope == 'ALL_OVERLAPS' else "仅删同名重叠"
                    self.report({'INFO'}, f"[{manager.import_mode}] NLA部署: {selected.action_name} ({manager.nla_insert_mode}/{overwrite_info})")
                else:
                    self.report({'INFO'}, f"[{manager.import_mode}] NLA部署: {selected.action_name} ({manager.nla_insert_mode})")
        
        return {'FINISHED'}


class ANIM_OT_GridPagePrev(bpy.types.Operator):
    """上一页"""
    bl_idname = "fmodel.grid_page_prev"
    bl_label = "上一页"
    
    def execute(self, context):
        context.scene.fmodel_anim_manager.grid_page -= 1
        return {'FINISHED'}


class ANIM_OT_GridPageNext(bpy.types.Operator):
    """下一页"""
    bl_idname = "fmodel.grid_page_next"
    bl_label = "下一页"
    
    def execute(self, context):
        context.scene.fmodel_anim_manager.grid_page += 1
        return {'FINISHED'}


# ============================================================
# Unity动画处理操作符
# ============================================================

class ANIM_OT_ProcessUnityAnims(bpy.types.Operator):
    """处理Unity动画并生成资产库"""
    bl_idname = "fmodel.process_unity_anims"
    bl_label = "处理 Unity 动画并生成资产库"
    bl_options = {'REGISTER', 'UNDO'}
    
    @classmethod
    def poll(cls, context):
        props = getattr(context.scene, "fmodel_assets", None)
        return props and props.source_dir
    
    def execute(self, context):
        from ...Assets.Utils import utils_asset
        
        props = context.scene.fmodel_assets
        source_dir = bpy.path.abspath(props.source_dir)
        out_dir = bpy.path.abspath(props.asset_out_dir)
        
        if not source_dir or not os.path.exists(source_dir):
            self.report({'ERROR'}, t("请先选择有效的 Unity 动画源文件夹！"))
            return {'CANCELLED'}
        
        if not out_dir:
            out_dir = os.path.join(os.path.dirname(source_dir), "Unity_Anim_Library")
            props.asset_out_dir = out_dir
        
        if not ensure_dir(out_dir):
            self.report({'ERROR'}, t("创建输出目录失败"))
            return {'CANCELLED'}
        
        # 创建安全副本
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        base_name = os.path.basename(source_dir.rstrip('/\\'))
        copied_dir = os.path.join(out_dir, f"{base_name}_Processed_{timestamp}")
        
        try:
            shutil.copytree(source_dir, copied_dir)
            self.report({'INFO'}, f"已生成安全副本: {copied_dir}")
        except Exception as e:
            self.report({'ERROR'}, f"创建副本失败: {e}")
            return {'CANCELLED'}
        
        # 处理动画文件
        manifest = DictionaryManifest(
            source_type=SourceType.UNITY_ANIM.value,
            source_path=source_dir
        )
        
        renamed_count = 0
        
        for root, dirs, files in os.walk(copied_dir):
            dirs[:] = [d for d in dirs if not d.startswith('.')]
            
            for file in files:
                if not file.lower().endswith('.anim'):
                    continue
                
                file_path = os.path.join(root, file)
                original_name = os.path.splitext(file)[0]
                
                # 跳过已处理的文件
                if re.search(r'_[a-f0-9]{8}$', original_name):
                    continue
                
                try:
                    with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                        content = f.read()
                except Exception:
                    continue
                
                content_no_name = re.sub(r'^\s*m_Name:.*$', '', content, flags=re.MULTILINE)
                content_hash = hashlib.md5(content_no_name.encode('utf-8')).hexdigest()[:8]
                hashed_name = f"{original_name}_{content_hash}"
                
                # 更新文件内容和名称
                new_content = re.sub(
                    r'(^\s*m_Name:\s*).*$', rf'\g<1>{hashed_name}',
                    content, count=1, flags=re.MULTILINE
                )
                
                new_file_path = os.path.join(root, f"{hashed_name}.anim")
                
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(new_content)
                os.rename(file_path, new_file_path)
                renamed_count += 1
                
                # 构建manifest
                rel_dir = os.path.relpath(root, copied_dir).replace('\\', '/')
                if rel_dir == '.':
                    skel_name, catalog_path = "Generic", "Uncategorized"
                else:
                    parts = rel_dir.split('/')
                    skel_name = parts[0]
                    catalog_path = "/".join(parts[1:]) if len(parts) > 1 else "Base"
                
                if skel_name not in manifest.skeletons:
                    manifest.skeletons[skel_name] = SkeletonNode(name=skel_name)
                
                folder = manifest.skeletons[skel_name].get_or_create_folder(catalog_path)
                anim_entry = AnimationEntry(
                    original_name=original_name,
                    hashed_name=hashed_name,
                    source_file=file_path,
                    content_hash=content_hash
                )
                folder.add_animation(hashed_name, anim_entry)
        
        if renamed_count == 0:
            self.report({'WARNING'}, t("未找到需要处理的Unity动画文件！"))
            return {'CANCELLED'}
        
        # 保存manifest
        manifest_path = os.path.join(out_dir, f"Unity_Anims_{timestamp}_manifest.json")
        manifest.save_to_file(manifest_path)
        
        # 动态挂载
        lib_name = props.lib_name or "Unity_Anim_Library"
        utils_asset.mount_dynamic_library(lib_name, out_dir)
        
        # 更新资产库列表
        already_linked = any(lib.name == lib_name for lib in props.project_libs)
        if not already_linked:
            new_lib = props.project_libs.add()
            new_lib.name = lib_name
            new_lib.path = out_dir
        
        # 触发扫描
        bpy.ops.fmodel.scan_anims()
        
        self.report({'INFO'}, f"处理完成！重命名了 {renamed_count} 个文件，资产库已挂载。")
        return {'FINISHED'}


# ============================================================
# 自动同步处理器
# ============================================================

@persistent
def auto_sync_active_skeleton(scene, depsgraph):
    """自动同步活动骨架"""
    try:
        context = bpy.context
        obj = context.active_object
        if not obj or obj.type != 'ARMATURE':
            return
        
        manager = getattr(scene, "fmodel_anim_manager", None)
        if not manager or not manager.skeleton_items:
            return
        
        sk_name = str(obj.get("FModel_Skeleton", obj.name))
        exists = any(item.name == sk_name for item in manager.skeleton_items)
        
        if exists and manager.active_skeleton != sk_name:
            manager.active_skeleton = sk_name
    except Exception as e:
        import traceback
        traceback.print_exc()


# ============================================================
# 资产库管理操作符
# ============================================================

class ANIM_OT_BrowseLibPath(bpy.types.Operator):
    """为选中的资产库选择目录或 blend 文件"""
    bl_idname = "fmodel.browse_lib_path"
    bl_label = "选择路径"
    bl_options = {'REGISTER', 'UNDO'}

    directory: bpy.props.StringProperty(subtype='DIR_PATH')

    @classmethod
    def poll(cls, context):
        props = context.scene.fmodel_assets
        return len(props.project_libs) > 0 and props.active_lib_index < len(props.project_libs)

    def execute(self, context):
        if not self.directory:
            return {'CANCELLED'}
        props = context.scene.fmodel_assets
        lib = props.project_libs[props.active_lib_index]
        lib.path = self.directory
        dir_name = os.path.basename(os.path.normpath(self.directory.rstrip('/\\')))
        if dir_name and (not lib.name or lib.name.startswith("Library_")):
            lib.name = os.path.splitext(dir_name)[0] if dir_name.lower().endswith('.blend') else dir_name
        return {'FINISHED'}

    def invoke(self, context, event):
        context.window_manager.fileselect_add(self)
        return {'RUNNING_MODAL'}


class ANIM_OT_MountBlendFile(bpy.types.Operator):
    """选择 .blend 文件挂载为资产库"""
    bl_idname = "fmodel.mount_blend_file"
    bl_label = "挂载 Blend 文件"
    bl_options = {'REGISTER', 'UNDO'}

    filepath: bpy.props.StringProperty(subtype='FILE_PATH')
    filter_glob: bpy.props.StringProperty(default='*.blend', options={'HIDDEN'})

    def execute(self, context):
        if not self.filepath or not os.path.exists(self.filepath):
            return {'CANCELLED'}
        props = context.scene.fmodel_assets
        abs_path = os.path.normpath(self.filepath)
        for lib in props.project_libs:
            if os.path.normpath(bpy.path.abspath(lib.path)) == abs_path:
                self.report({'INFO'}, f"已存在: {lib.name}")
                return {'CANCELLED'}
        lib_name = os.path.splitext(os.path.basename(self.filepath))[0]
        lib = props.project_libs.add()
        lib.name = lib_name
        lib.path = self.filepath
        props.active_lib_index = len(props.project_libs) - 1
        self.report({'INFO'}, f"已挂载: {lib_name}")
        return {'FINISHED'}

    def invoke(self, context, event):
        context.window_manager.fileselect_add(self)
        return {'RUNNING_MODAL'}


class ANIM_OT_MountAllLibs(bpy.types.Operator):
    """将所有资产库注册为 Blender 资产浏览器库"""
    bl_idname = "fmodel.mount_all_libs"
    bl_label = "挂载到 Blender"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        return len(context.scene.fmodel_assets.project_libs) > 0

    def execute(self, context):
        from ...Assets.Utils.utils_asset import mount_dynamic_library
        props = context.scene.fmodel_assets
        mounted = 0
        for lib in props.project_libs:
            if not lib.path:
                continue
            abs_path = bpy.path.abspath(lib.path)
            if abs_path.lower().endswith('.blend'):
                abs_path = os.path.dirname(abs_path)
            if not os.path.isdir(abs_path):
                continue
            if mount_dynamic_library(lib.name, abs_path):
                mounted += 1
        self.report({'INFO'}, f"已挂载 {mounted} 个资产库")
        return {'FINISHED'}


class ANIM_OT_UnmountAllLibs(bpy.types.Operator):
    """卸载所有本插件注册的动态资产库"""
    bl_idname = "fmodel.unmount_all_libs"
    bl_label = "卸载全部"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        from ...Assets.Utils.utils_asset import cleanup_dynamic_libraries
        cleanup_dynamic_libraries()
        self.report({'INFO'}, t("已卸载全部动态资产库"))
        return {'FINISHED'}


class ANIM_OT_OpenLibFolder(bpy.types.Operator):
    """在系统文件管理器中打开选中的资产库目录"""
    bl_idname = "fmodel.open_lib_folder"
    bl_label = "打开文件夹"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        props = context.scene.fmodel_assets
        return len(props.project_libs) > 0 and props.active_lib_index < len(props.project_libs) and bool(props.project_libs[props.active_lib_index].path)

    def execute(self, context):
        import subprocess
        import sys
        props = context.scene.fmodel_assets
        lib = props.project_libs[props.active_lib_index]
        abs_path = bpy.path.abspath(lib.path)
        if abs_path.lower().endswith('.blend'):
            abs_path = os.path.dirname(abs_path)
        if not os.path.exists(abs_path):
            self.report({'WARNING'}, f"路径不存在: {abs_path}")
            return {'CANCELLED'}
        try:
            if sys.platform == 'win32':
                os.startfile(abs_path)
            elif sys.platform == 'darwin':
                subprocess.Popen(['open', abs_path])
            else:
                subprocess.Popen(['xdg-open', abs_path])
        except Exception as e:
            self.report({'ERROR'}, f"无法打开: {e}")
        return {'FINISHED'}


# ============================================================
# 注册
# ============================================================

classes = (
    AnimTreeItem,
    SkeletonItem,
    AnimManagerProps,
    ANIM_OT_ScanAnims,
    ANIM_OT_ScanLocalAnims,
    ANIM_OT_ToggleFolder,
    ANIM_OT_SelectGridItem,
    ANIM_OT_PreviewAnim,
    ANIM_OT_ApplyAnim,
    ANIM_OT_GridPagePrev,
    ANIM_OT_GridPageNext,
    ANIM_OT_ProcessUnityAnims,
    ANIM_OT_BrowseLibPath,
    ANIM_OT_MountBlendFile,
    ANIM_OT_MountAllLibs,
    ANIM_OT_UnmountAllLibs,
    ANIM_OT_OpenLibFolder,
)


_manager_backup = None  # 跨重载持久化资产库数据


def register():
    global _manager_backup
    for cls in classes:
        bpy.utils.register_class(cls)
    
    bpy.types.Scene.fmodel_anim_manager = bpy.props.PointerProperty(type=AnimManagerProps)

    # Restore asset library data from previous session
    if _manager_backup and bpy.context.scene:
        try:
            mgr = bpy.context.scene.fmodel_anim_manager
            for sk in _manager_backup.get("skeletons", []):
                item = mgr.skeleton_items.add()
                item.name = sk
            for td in _manager_backup.get("tree", []):
                item = mgr.tree_items.add()
                for k, v in td.items():
                    setattr(item, k, v)
        except Exception:
            _manager_backup = None
    
    if auto_sync_active_skeleton not in bpy.app.handlers.depsgraph_update_post:
        bpy.app.handlers.depsgraph_update_post.append(auto_sync_active_skeleton)


def unregister():
    global _manager_backup
    clear_custom_icons()
    
    if auto_sync_active_skeleton in bpy.app.handlers.depsgraph_update_post:
        bpy.app.handlers.depsgraph_update_post.remove(auto_sync_active_skeleton)

    # Backup asset library data before destroying
    try:
        if bpy.context.scene and hasattr(bpy.context.scene, "fmodel_anim_manager"):
            mgr = bpy.context.scene.fmodel_anim_manager
            _manager_backup = {
                "skeletons": [si.name for si in mgr.skeleton_items],
                "tree": [{
                    "name": ti.name, "item_type": ti.item_type, "lib_type": ti.lib_type,
                    "node_id": ti.node_id, "parent_id": ti.parent_id, "skeleton": ti.skeleton,
                    "blend_path": ti.blend_path, "action_name": ti.action_name,
                    "thumb_path": ti.thumb_path, "depth": ti.depth, "is_expanded": ti.is_expanded,
                    "anim_count": ti.anim_count, "volume_count": ti.volume_count,
                } for ti in mgr.tree_items],
            }
    except Exception:
        _manager_backup = None
    
    del bpy.types.Scene.fmodel_anim_manager
    
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
