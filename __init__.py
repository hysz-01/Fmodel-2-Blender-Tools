# FModel_Tools/__init__.py
# 插件入口 — 模块注册与 Scheme 注入
bl_info = {
    "name": "FModel Tools",
    "author": "Your Name",
    "version": (7, 3, 0),
    "blender": (3, 0, 0),
    "location": "View3D > Sidebar > FModel",
    "description": "专为 UE/FModel 设计的完整资产管线工具集",
    "category": "Import-Export",
}

import bpy
import importlib

from . import core
from . import ui
from . import Fmodel
from . import Assets
from . import Universal_tools
from . import auto_handlers

if "bpy" in locals():
    importlib.reload(core)
    importlib.reload(ui)
    importlib.reload(Fmodel)
    importlib.reload(Assets)
    importlib.reload(Universal_tools)
    importlib.reload(auto_handlers)

# 从新位置导入 Schemes
from .Universal_tools.skeleton import scheme_auto, scheme_copy
from .Universal_tools.mesh import scheme_morph_merge, scheme_psk_auto, scheme_psk_mesh_fix

REGISTERED_SCHEMES = [
    scheme_auto, scheme_copy, scheme_morph_merge,
    scheme_psk_auto, scheme_psk_mesh_fix
]


def register():
    # 1. 动态注入 Scheme 属性
    if not hasattr(ui.FMODEL_CoreProperties, "__annotations__"):
        ui.FMODEL_CoreProperties.__annotations__ = {}
    enum_items = []
    for i, scheme in enumerate(REGISTERED_SCHEMES):
        bpy.utils.register_class(scheme.SCHEME_PROPS)
        enum_items.append((scheme.SCHEME_ID, scheme.SCHEME_LABEL, scheme.SCHEME_DESC, scheme.SCHEME_ICON, i))
        ui.FMODEL_CoreProperties.__annotations__[f"props_{scheme.SCHEME_ID.lower()}"] = bpy.props.PointerProperty(type=scheme.SCHEME_PROPS)
    ui.FMODEL_CoreProperties.__annotations__['fix_scheme'] = bpy.props.EnumProperty(items=enum_items, default=REGISTERED_SCHEMES[0].SCHEME_ID)

    # 2. 模块化注册
    core.register()
    ui.register()
    Fmodel.register()
    Assets.register()
    Universal_tools.register()

    # 3. 注册自动触发器
    auto_handlers.register_handlers()


def unregister():
    auto_handlers.unregister_handlers()

    Universal_tools.unregister()
    Assets.unregister()
    Fmodel.unregister()
    ui.unregister()
    core.unregister()

    for scheme in reversed(REGISTERED_SCHEMES):
        bpy.utils.unregister_class(scheme.SCHEME_PROPS)


if __name__ == "__main__":
    register()
