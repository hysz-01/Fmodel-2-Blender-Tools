# FModel_Tools/Fmodel/importers/__init__.py
# 导入器模块 — 模型、动画、导出

import bpy
import importlib
from . import model
from . import animation
from . import export

if "bpy" in locals():
    importlib.reload(model)
    importlib.reload(animation)
    importlib.reload(export)


def register():
    model.register()
    animation.register()
    export.register()


def unregister():
    export.unregister()
    animation.unregister()
    model.unregister()
