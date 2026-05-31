# FModel_Tools/Assets/Anims/ui_custom_grid.py
# 翻页网格 — 卡片布局与分页渲染（操作符由 anim_manager.py 注册）

import math


class FModelCustomGrid:
    @staticmethod
    def draw(layout, context, manager, valid_indices, draw_callback, empty_callback):
        cols = manager.grid_columns
        rows = manager.grid_row_count
        items_per_page = cols * rows

        total_items = len(valid_indices)
        total_pages = max(1, math.ceil(total_items / max(1, items_per_page)))

        safe_page = manager.grid_page
        if safe_page > total_pages: safe_page = total_pages
        if safe_page < 1: safe_page = 1

        main_box = layout.box()

        # 顶部导航
        head_row = main_box.row(align=True)
        head_row.label(text=f" {total_items} 个", icon='ASSET_MANAGER')

        if total_pages > 1:
            nav = head_row.row(align=True)
            nav.operator("fmodel.grid_page_prev", text="", icon='TRIA_LEFT')
            nav.label(text=f" {safe_page}/{total_pages} ")
            nav.operator("fmodel.grid_page_next", text="", icon='TRIA_RIGHT')

        main_box.separator()

        if total_items == 0:
            main_box.label(text="当前目录没有匹配的动画", icon='INFO')
            return

        grid_col = main_box.column(align=True)
        start_idx = (safe_page - 1) * items_per_page
        end_idx = start_idx + items_per_page

        current_row = None
        for i in range(start_idx, end_idx):
            if (i - start_idx) % cols == 0:
                current_row = grid_col.row(align=True)

            cell = current_row.column(align=True)
            if i < total_items:
                item_idx = valid_indices[i]
                item = manager.tree_items[item_idx]
                is_active = (manager.active_item_index == item_idx)
                draw_callback(context, cell, item, item_idx, is_active, manager)
            else:
                empty_callback(context, cell, manager)


def register():
    pass  # 操作符由 anim_manager.py 统一注册


def unregister():
    pass
