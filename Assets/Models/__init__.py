# FModel_Tools/Assets/Models/__init__.py
# 角色模型资产模块 — 保存、预览、导入

import bpy
import importlib
from . import operators
from . import ui

if "bpy" in locals():
    importlib.reload(operators)
    importlib.reload(ui)


def register():
    operators.register()
    ui.register()


def unregister():
    ui.unregister()
    operators.unregister()
