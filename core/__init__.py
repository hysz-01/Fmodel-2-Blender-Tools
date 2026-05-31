# FModel_Tools/core/__init__.py
# 核心共享模块 — 枚举、类型、工具函数、管线上下文

from . import enums
from . import types
from . import context
from . import utils
from . import logger
from . import i18n

# 重新导出常用内容
from .enums import (
    PipelineStage, StageStatus, SourceType, ImportMode,
    ItemType, ApplyMethod
)

from .types import (
    AnimationEntry, FolderNode, SkeletonNode,
    DictionaryManifest, ImportedAction, ImportedAssetCollection,
    CatalogEntry, LibraryAsset, AssetLibraryManifest,
    PipelineConfig, PipelineLog
)

from .context import PipelineContext

from .utils import (
    get_or_create_catalog_uuid,
    ensure_dir,
    safe_relpath,
    normalize_path,
    get_ueformat_api
)

from .logger import (
    FModelLogger, LogLevel, OperationType,
    get_logger, initialize_logging,
    log_info, log_warning, log_error, log_success,
    backup_before
)


def register():
    enums.register()
    types.register()
    context.register()
    utils.register()
    logger.register()
    i18n.register()


def unregister():
    i18n.unregister()
    logger.unregister()
    utils.unregister()
    context.unregister()
    types.unregister()
    enums.unregister()