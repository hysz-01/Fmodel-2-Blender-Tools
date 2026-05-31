# FModel_Tools/Fmodel/importers/model/__init__.py
# 模型导入器 — glTF、PSK、UEFormat

import bpy
import importlib
from . import operator_model_gltf
from . import operator_model_ueformat
from . import operator_model_psk

if "bpy" in locals():
    importlib.reload(operator_model_gltf)
    importlib.reload(operator_model_ueformat)
    importlib.reload(operator_model_psk)


def register():
    operator_model_gltf.register()
    operator_model_ueformat.register()
    operator_model_psk.register()


def unregister():
    operator_model_psk.unregister()
    operator_model_ueformat.unregister()
    operator_model_gltf.unregister()
