# FModel_Tools/Fmodel/Pipeline/__init__.py
# 管线模块 — 字典扫描、格式转换、资产库构建

import bpy
import importlib
from . import stages
from . import manager
from . import steps

if "bpy" in locals():
    importlib.reload(stages)
    importlib.reload(manager)
    importlib.reload(steps)

def register():
    stages.register()
    manager.register()
    steps.register()

def unregister():
    steps.unregister()
    manager.unregister()
    stages.unregister()