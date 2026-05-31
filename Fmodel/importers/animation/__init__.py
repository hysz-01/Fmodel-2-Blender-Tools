# FModel_Tools/Fmodel/importers/animation/__init__.py
# 动画导入器 — UEFormat 动画、PSA 动画

import bpy
import importlib
from . import operator_anim_ueformat
from . import operator_anim_psa

if "bpy" in locals():
    importlib.reload(operator_anim_ueformat)
    importlib.reload(operator_anim_psa)


def register():
    operator_anim_ueformat.register()
    operator_anim_psa.register()


def unregister():
    operator_anim_psa.unregister()
    operator_anim_ueformat.unregister()
