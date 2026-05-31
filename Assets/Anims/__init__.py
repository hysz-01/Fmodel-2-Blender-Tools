# FModel_Tools/Assets/Anims/__init__.py
# 动画资产子模块 — 管理器、操作符、翻页网格

import bpy
import importlib
from . import operators_asset
from . import anim_manager
from . import ui_custom_grid

if "bpy" in locals():
    importlib.reload(operators_asset)
    importlib.reload(anim_manager)
    importlib.reload(ui_custom_grid)


def register():
    operators_asset.register()
    anim_manager.register()
    ui_custom_grid.register()


def unregister():
    ui_custom_grid.unregister()
    anim_manager.unregister()
    operators_asset.unregister()
