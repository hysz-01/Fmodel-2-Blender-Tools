# FModel_Tools/Assets/ui_assets.py
# 资产 UI — UIList 组件（资产库树、动画树、文件夹、网格）

import bpy
import os
from .Anims.anim_manager import get_custom_icon
from .Anims import ui_custom_grid


# ============================================================
# 资产库树状 UIList（供资产库设置面板使用）
# ============================================================

class ASSETS_UL_LibraryTree(bpy.types.UIList):
    """资产库树状列表 — 显示 LIBRARY、ANIM_LIB、VOLUME、MODEL"""
    def filter_items(self, context, data, propname):
        items = getattr(data, propname)
        flt_flags = []
        flt_neworder = []

        # 收集被折叠的 LIBRARY 节点
        collapsed = set()
        for item in items:
            if item.item_type == 'LIBRARY' and not item.is_expanded:
                collapsed.add(item.node_id)

        # 收集被折叠的 ANIM_LIB 节点
        collapsed_anims = set()
        for item in items:
            if item.item_type == 'ANIM_LIB' and not item.is_expanded and item.volume_count > 1:
                collapsed_anims.add(item.node_id)

        for item in items:
            flag = 0
            if item.item_type == 'LIBRARY':
                flag = self.bitflag_filter_item
            elif item.item_type == 'ANIM_LIB':
                if item.parent_id not in collapsed:
                    flag = self.bitflag_filter_item
            elif item.item_type == 'MODEL':
                if item.parent_id not in collapsed:
                    flag = self.bitflag_filter_item
            elif item.depth == 2 and item.item_type not in ('FOLDER',):
                # VOLUME 条目
                if item.parent_id not in collapsed and item.parent_id not in collapsed_anims:
                    flag = self.bitflag_filter_item
            flt_flags.append(flag)
        return flt_flags, flt_neworder

    def draw_item(self, context, layout, data, item, icon, active_data, active_propname):
        row = layout.row(align=True)
        for _ in range(item.depth):
            row.separator(factor=1.0)

        if item.item_type == 'LIBRARY':
            expanded = item.is_expanded
            toggle_icon = 'DISCLOSURE_TRI_DOWN' if expanded else 'DISCLOSURE_TRI_RIGHT'
            op = row.operator("fmodel.toggle_folder", text="", icon=toggle_icon, emboss=False)
            op.node_id = item.node_id

            if item.lib_type == 'DIRECTORY':
                row.label(text=item.name, icon='FILE_FOLDER')
            else:
                row.label(text=item.name, icon='FILE_BLEND')

            info = row.row(align=True)
            info.alignment = 'RIGHT'
            if item.anim_count > 0:
                info.label(text=f"{item.anim_count}动画")

        elif item.item_type == 'ANIM_LIB':
            is_multi = item.volume_count > 1
            if is_multi:
                expanded = item.is_expanded
                toggle_icon = 'DISCLOSURE_TRI_DOWN' if expanded else 'DISCLOSURE_TRI_RIGHT'
                op = row.operator("fmodel.toggle_folder", text="", icon=toggle_icon, emboss=False)
                op.node_id = item.node_id
            else:
                row.separator(factor=0.6)

            label = item.name
            if item.anim_count > 0:
                label += f" ({item.anim_count}动作)"
            row.label(text=label, icon='ANIM_DATA')

            if is_multi:
                info = row.row(align=True)
                info.alignment = 'RIGHT'
                info.label(text=f"{item.volume_count}卷")

        elif item.depth == 2 and item.item_type not in ('FOLDER', 'ANIM'):
            row.separator(factor=0.6)
            row.label(text=item.name, icon='FILE_BLEND')

        elif item.item_type == 'MODEL':
            row.separator(factor=0.6)
            row.label(text=item.name, icon='OUTLINER_OB_MESH')


# ============================================================
# 动画树状 UIList（仅显示 FOLDER + ANIM）
# ============================================================

class ASSETS_UL_AnimTree(bpy.types.UIList):
    """动画树状列表 — 仅显示 FOLDER 和 ANIM，过滤 LIBRARY/MODEL/ANIM_LIB"""
    def filter_items(self, context, data, propname):
        items = getattr(data, propname)
        manager = context.scene.fmodel_anim_manager
        active_skel = manager.active_skeleton
        search_str = manager.search_filter.lower().strip()

        flt_flags = []
        flt_neworder = []

        # 收集被折叠的 ANIM_LIB 和 FOLDER
        collapsed = set()
        for item in items:
            if (item.item_type == 'ANIM_LIB' and not item.is_expanded and item.volume_count > 1) or \
               (item.item_type == 'FOLDER' and not item.is_expanded):
                collapsed.add(item.node_id)

        # 收集被折叠的父节点ID
        hidden_parents = set()
        for item in items:
            if item.item_type in ('LIBRARY',) and not item.is_expanded:
                hidden_parents.add(item.node_id)

        current_hidden = 9999

        for item in items:
            flag = 0

            # 跳过 LIBRARY/MODEL/ANIM_LIB（库设置用）
            if item.item_type in ('LIBRARY', 'MODEL', 'ANIM_LIB'):
                flag = 0
                if item.item_type == 'LIBRARY' and not item.is_expanded:
                    current_hidden = 0  # 隐藏该库下所有子内容
                elif item.item_type == 'LIBRARY' and item.is_expanded:
                    current_hidden = 9999

            elif item.item_type == 'FOLDER':
                if active_skel in ("ALL", "NONE") or item.skeleton == active_skel:
                    if item.parent_id in hidden_parents:
                        flag = 0
                    elif item.depth <= current_hidden:
                        flag = self.bitflag_filter_item
                        if not item.is_expanded:
                            current_hidden = item.depth

            elif item.item_type == 'ANIM':
                # depth 2+ 的 ANIM 是实际动画条目
                if item.depth >= 2:
                    if item.parent_id in hidden_parents or item.parent_id in collapsed:
                        flag = 0
                    elif active_skel in ("ALL", "NONE") or item.skeleton == active_skel:
                        if search_str:
                            if search_str in item.name.lower():
                                flag = self.bitflag_filter_item
                        elif item.depth <= current_hidden:
                            flag = self.bitflag_filter_item

            flt_flags.append(flag)
        return flt_flags, flt_neworder

    def draw_item(self, context, layout, data, item, icon, active_data, active_propname):
        row = layout.row(align=True)
        for _ in range(item.depth):
            row.separator(factor=1.2)

        if item.item_type == 'FOLDER':
            icon_toggle = 'DISCLOSURE_TRI_DOWN' if item.is_expanded else 'DISCLOSURE_TRI_RIGHT'
            op = row.operator("fmodel.toggle_folder", text="", icon=icon_toggle, emboss=False)
            op.node_id = item.node_id
            row.label(text=item.name, icon='FILE_FOLDER')
        else:
            row.separator(factor=0.6)
            icon_id = get_custom_icon(item.thumb_path, item.blend_path)
            if icon_id != 0:
                row.label(text=item.name, icon_value=icon_id)
            else:
                row.label(text=item.name, icon='ANIM_DATA')

            row_ops = row.row(align=True)
            op_preview = row_ops.operator("fmodel.preview_anim", text="", icon='RESTRICT_VIEW_OFF', emboss=False)
            op_preview.target_node_id = item.node_id
            op_apply = row_ops.operator("fmodel.apply_anim", text="", icon='IMPORT', emboss=False)
            op_apply.target_node_id = item.node_id
            op_apply.apply_method_override = 'REPLACE'
            op_nla = row_ops.operator("fmodel.apply_anim", text="", icon='NLA', emboss=False)
            op_nla.target_node_id = item.node_id
            op_nla.apply_method_override = 'APPEND_NLA'


class ASSETS_UL_FolderTree(bpy.types.UIList):
    def filter_items(self, context, data, propname):
        items = getattr(data, propname)
        manager = context.scene.fmodel_anim_manager
        active_skel = manager.active_skeleton
        search_str = manager.search_filter.lower().strip()
        
        valid_folders = set()
        if search_str:
            for item in items:
                if active_skel in ("ALL", "NONE") or item.skeleton == active_skel:
                    if search_str in item.name.lower():
                        if item.item_type == 'FOLDER':
                            valid_folders.add(f"{item.skeleton}||{item.node_id}")
                        curr = item.parent_id
                        while curr:
                            valid_folders.add(f"{item.skeleton}||{curr}")
                            curr = curr.rsplit('/', 1)[0] if '/' in curr else ""

        flt_flags = []
        flt_neworder = []
        current_hidden_depth = 9999 

        for item in items:
            flag = 0
            if item.item_type == 'FOLDER': 
                if active_skel in ("ALL", "NONE") or item.skeleton == active_skel:
                    if search_str:
                        if f"{item.skeleton}||{item.node_id}" in valid_folders:
                            flag = self.bitflag_filter_item
                    else:
                        if item.depth <= current_hidden_depth:
                            current_hidden_depth = 9999
                            flag = self.bitflag_filter_item
                            if not item.is_expanded:
                                current_hidden_depth = item.depth
            flt_flags.append(flag)
        return flt_flags, flt_neworder

    def draw_item(self, context, layout, data, item, icon, active_data, active_propname):
        row = layout.row(align=True)
        if item.depth > 0:
            for _ in range(item.depth): row.separator(factor=1.2)
            
        icon_toggle = 'TRIA_DOWN' if item.is_expanded else 'TRIA_RIGHT'
        op = row.operator("fmodel.toggle_folder", text="", icon=icon_toggle, emboss=False)
        op.node_id = item.node_id
        row.label(text=item.name, icon='FILE_FOLDER')


class ASSETS_UL_AnimGrid(bpy.types.UIList):
    def filter_items(self, context, data, propname):
        items = getattr(data, propname)
        manager = context.scene.fmodel_anim_manager
        search_str = manager.search_filter.lower().strip()
        active_folder_id = ""
        active_skel = ""
        
        if manager.tree_items and manager.active_folder_index < len(manager.tree_items):
            sel_item = manager.tree_items[manager.active_folder_index]
            if sel_item.item_type == 'FOLDER':
                active_folder_id = sel_item.node_id
                active_skel = sel_item.skeleton

        flt_flags = []
        flt_neworder = []
        for item in items:
            flag = 0
            if item.item_type == 'ANIM': 
                if item.parent_id == active_folder_id and item.skeleton == active_skel:
                    if not search_str or search_str in item.name.lower():
                        flag = self.bitflag_filter_item
            flt_flags.append(flag)
        return flt_flags, flt_neworder

    def draw_item(self, context, layout, data, item, icon, active_data, active_propname):
        row = layout.row(align=True)
        icon_id = get_custom_icon(item.thumb_path, item.blend_path)
        if icon_id != 0: row.label(text=item.name, icon_value=icon_id)
        else: row.label(text=item.name, icon='ANIM_DATA')
        
        row_ops = row.row(align=True)
        op_preview = row_ops.operator("fmodel.preview_anim", text="", icon='RESTRICT_VIEW_OFF', emboss=False)
        op_preview.target_node_id = item.node_id
        op_apply = row_ops.operator("fmodel.apply_anim", text="", icon='IMPORT', emboss=False)
        op_apply.target_node_id = item.node_id
        op_apply.apply_method_override = 'REPLACE'
        op_nla = row_ops.operator("fmodel.apply_anim", text="", icon='NLA', emboss=False)
        op_nla.target_node_id = item.node_id
        op_nla.apply_method_override = 'APPEND_NLA'


# ============================================================
# 注册（面板已集成到 FModel 主面板 ui.py）
# ============================================================

def register():
    bpy.utils.register_class(ASSETS_UL_LibraryTree)
    bpy.utils.register_class(ASSETS_UL_AnimTree)
    bpy.utils.register_class(ASSETS_UL_FolderTree)
    bpy.utils.register_class(ASSETS_UL_AnimGrid)

def unregister():
    bpy.utils.unregister_class(ASSETS_UL_AnimGrid)
    bpy.utils.unregister_class(ASSETS_UL_FolderTree)
    bpy.utils.unregister_class(ASSETS_UL_AnimTree)
    bpy.utils.unregister_class(ASSETS_UL_LibraryTree)
