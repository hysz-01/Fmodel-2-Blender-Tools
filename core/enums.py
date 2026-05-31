# FModel_Tools/core/enums.py
# 枚举定义 — PipelineStage、SourceType、ImportMode

from enum import Enum


class PipelineStage(Enum):
    """管线阶段枚举"""
    DICTIONARY_ACQUISITION = "dictionary_acquisition"
    FORMAT_CONVERSION = "format_conversion"  # 新增：格式中转阶段
    ASSET_IMPORT = "asset_import"
    LIBRARY_BUILDING = "library_building"
    FINALIZATION = "finalization"


class StageStatus(Enum):
    """阶段状态枚举"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


class SourceType(Enum):
    """数据源类型枚举"""
    UNITY_ANIM = "unity_anim"
    FMODEL_UEANIM = "fmodel_ueanim"
    FBX_BATCH = "fbx_batch"
    CUSTOM = "custom"


class ImportMode(Enum):
    """导入模式枚举"""
    FBX_MATCH = "fbx_match"
    UEANIM_DIRECT = "ueanim_direct"
    LINK_EXISTING = "link_existing"


class ItemType(Enum):
    """树形项目类型"""
    FOLDER = "FOLDER"
    ANIM = "ANIM"


class ApplyMethod(Enum):
    """动画应用模式"""
    REPLACE = "REPLACE"
    APPEND_NLA = "APPEND_NLA"


class DisplayMode(Enum):
    """显示模式"""
    TREE = "TREE"
    DETAIL_H = "DETAIL_H"
    DETAIL_V = "DETAIL_V"


# 枚举到Blender EnumProperty的转换辅助
def enum_to_items(enum_class):
    """将枚举类转换为Blender EnumProperty的items格式"""
    return [(e.value, e.name.replace('_', ' ').title(), e.value) for e in enum_class]


def register():
    """Core enums不需要注册Blender类"""
    pass

def unregister():
    """Core enums不需要注册Blender类"""
    pass