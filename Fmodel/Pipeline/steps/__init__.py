# FModel_Tools/Fmodel/Pipeline/steps/__init__.py
# 向导步骤子模块 — 4 步引导式资产库构建流程

import bpy
import importlib

from . import state
from . import step1_flow
from . import step2_directory
from . import step3_scan
from . import step4_import
from . import navigate
from . import runner

if "bpy" in locals():
    importlib.reload(state)
    importlib.reload(step1_flow)
    importlib.reload(step2_directory)
    importlib.reload(step3_scan)
    importlib.reload(step4_import)
    importlib.reload(navigate)
    importlib.reload(runner)

from .state import WizardState


def register():
    state.register()
    step1_flow.register()
    step2_directory.register()
    step3_scan.register()
    step4_import.register()
    navigate.register()
    bpy.types.Scene.pipeline_wizard = bpy.props.PointerProperty(type=WizardState)


def unregister():
    del bpy.types.Scene.pipeline_wizard
    navigate.unregister()
    step4_import.unregister()
    step3_scan.unregister()
    step2_directory.unregister()
    step1_flow.unregister()
    state.unregister()
