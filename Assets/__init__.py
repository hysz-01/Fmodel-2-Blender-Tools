# FModel_Tools/Assets/__init__.py
# 资产模块 — 动画资产管理、角色模型资产与 UI

import bpy
import importlib
from . import Anims
from . import Models
from . import ui_assets

if "bpy" in locals():
    importlib.reload(Anims)
    importlib.reload(Models)
    importlib.reload(ui_assets)


def register():
    Anims.register()
    Models.register()
    ui_assets.register()


def unregister():
    ui_assets.unregister()
    Models.unregister()
    Anims.unregister()
