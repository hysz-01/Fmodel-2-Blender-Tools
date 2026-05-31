# FModel_Tools/Universal_tools/Animations/__init__.py
# 动画工具 — 动作清理

import bpy
import importlib
from . import clean_Anim

if "bpy" in locals():
    importlib.reload(clean_Anim)


def register():
    clean_Anim.register()


def unregister():
    clean_Anim.unregister()
