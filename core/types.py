# FModel_Tools/core/types.py
# 数据类型 — PipelineConfig、DictionaryManifest 等

import json
import os
from dataclasses import dataclass, field, asdict
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime

from .enums import SourceType, ImportMode


# ============================================================
# 动画条目
# ============================================================

@dataclass
class AnimationEntry:
    """动画条目 - 最小化的动画信息单元"""
    original_name: str = ""
    hashed_name: str = ""
    source_file: str = ""
    content_hash: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> dict:
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: dict) -> 'AnimationEntry':
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


# ============================================================
# 文件夹节点
# ============================================================

@dataclass
class FolderNode:
    """文件夹节点 - 树形结构的基本单元"""
    path: str = ""
    animations: Dict[str, AnimationEntry] = field(default_factory=dict)
    subfolders: Dict[str, 'FolderNode'] = field(default_factory=dict)
    
    def add_animation(self, name: str, entry: AnimationEntry):
        self.animations[name] = entry
    
    def get_or_create_subfolder(self, name: str) -> 'FolderNode':
        if name not in self.subfolders:
            self.subfolders[name] = FolderNode(path=name)
        return self.subfolders[name]


# ============================================================
# 骨架节点
# ============================================================

@dataclass
class SkeletonNode:
    """骨架节点 - 代表一个骨架及其所有动画"""
    name: str = ""
    folders: Dict[str, FolderNode] = field(default_factory=dict)
    
    def get_or_create_folder(self, path: str) -> FolderNode:
        """获取或创建文件夹路径"""
        if not path or path == ".":
            if "" not in self.folders:
                self.folders[""] = FolderNode(path="")
            return self.folders[""]
        
        parts = path.split('/')
        current = self.folders
        for part in parts:
            if part not in current:
                current[part] = FolderNode(path=part)
            folder = current[part]
            current = folder.subfolders
        return folder
    
    def collect_all_animations(self, parent_path: str = "") -> List[Tuple[str, str, AnimationEntry]]:
        """收集所有动画条目 [(folder_path, anim_name, entry), ...]"""
        result = []
        for folder_name, folder in self.folders.items():
            current_path = f"{parent_path}/{folder_name}" if parent_path else folder_name
            for anim_name, entry in folder.animations.items():
                result.append((current_path, anim_name, entry))
            result.extend(self._collect_subfolder(folder, current_path))
        return result
    
    def _collect_subfolder(self, folder: FolderNode, parent_path: str) -> List[Tuple[str, str, AnimationEntry]]:
        result = []
        for sub_name, sub_folder in folder.subfolders.items():
            current_path = f"{parent_path}/{sub_name}"
            for anim_name, entry in sub_folder.animations.items():
                result.append((current_path, anim_name, entry))
            result.extend(self._collect_subfolder(sub_folder, current_path))
        return result


# ============================================================
# 字典清单
# ============================================================

@dataclass
class DictionaryManifest:
    """字典清单 - 阶段1的输出"""
    version: str = "1.0"
    source_type: str = SourceType.UNITY_ANIM.value
    source_path: str = ""
    created_at: str = ""
    skeletons: Dict[str, SkeletonNode] = field(default_factory=dict)
    
    def __post_init__(self):
        if not self.created_at:
            self.created_at = datetime.now().isoformat()
    
    def get_all_animations(self) -> List[Tuple[str, str, str, AnimationEntry]]:
        """获取所有动画 [(skeleton, folder_path, anim_name, entry), ...]"""
        result = []
        for skel_name, skel_node in self.skeletons.items():
            for folder_path, anim_name, entry in skel_node.collect_all_animations():
                result.append((skel_name, folder_path, anim_name, entry))
        return result
    
    def to_dict(self) -> dict:
        """转换为可序列化的字典"""
        return {
            "version": self.version,
            "source_type": self.source_type,
            "source_path": self.source_path,
            "created_at": self.created_at,
            "skeletons": {
                name: self._skeleton_to_dict(skel) 
                for name, skel in self.skeletons.items()
            }
        }
    
    def _skeleton_to_dict(self, skel: SkeletonNode) -> dict:
        return {name: self._folder_to_dict(f) for name, f in skel.folders.items()}
    
    def _folder_to_dict(self, folder: FolderNode) -> dict:
        result = {}
        if folder.animations:
            result["__animations__"] = {n: e.to_dict() for n, e in folder.animations.items()}
        for sub_name, sub_folder in folder.subfolders.items():
            result[sub_name] = self._folder_to_dict(sub_folder)
        return result
    
    def save_to_file(self, filepath: str):
        """保存到JSON文件"""
        os.makedirs(os.path.dirname(filepath) or '.', exist_ok=True)
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(self.to_dict(), f, ensure_ascii=False, indent=4)
    
    @classmethod
    def from_dict(cls, data: dict) -> 'DictionaryManifest':
        """从字典创建实例"""
        manifest = cls(
            version=data.get("version", "1.0"),
            source_type=data.get("source_type", SourceType.UNITY_ANIM.value),
            source_path=data.get("source_path", ""),
            created_at=data.get("created_at", "")
        )
        for skel_name, skel_data in data.get("skeletons", {}).items():
            skel = SkeletonNode(name=skel_name)
            skel.folders = cls._dict_to_folders(skel_data)
            manifest.skeletons[skel_name] = skel
        return manifest
    
    @classmethod
    def _dict_to_folders(cls, data: dict) -> Dict[str, FolderNode]:
        folders = {}
        for key, value in data.items():
            if isinstance(value, dict):
                folder = FolderNode(path=key)
                if "__animations__" in value:
                    for anim_name, anim_data in value["__animations__"].items():
                        folder.animations[anim_name] = AnimationEntry.from_dict(anim_data)
                subfolders = {k: v for k, v in value.items() if k != "__animations__"}
                folder.subfolders = cls._dict_to_folders(subfolders)
                folders[key] = folder
        return folders
    
    @classmethod
    def load_from_file(cls, filepath: str) -> 'DictionaryManifest':
        """从JSON文件加载"""
        with open(filepath, 'r', encoding='utf-8') as f:
            return cls.from_dict(json.load(f))


# ============================================================
# 导入动作
# ============================================================

@dataclass
class ImportedAction:
    """导入的动作"""
    action_name: str = ""
    source_manifest_ref: str = ""
    source_file: str = ""
    staged_blend: str = ""
    import_status: str = "success"
    frame_range: Tuple[int, int] = (0, 0)
    error_message: str = ""


# ============================================================
# 导入资产集合
# ============================================================

@dataclass
class ImportedAssetCollection:
    """导入资产集合 - 阶段2的输出"""
    version: str = "1.0"
    import_mode: str = ImportMode.FBX_MATCH.value
    imported_actions: List[ImportedAction] = field(default_factory=list)
    failed_imports: List[Dict[str, str]] = field(default_factory=list)
    
    @property
    def success_count(self) -> int:
        return len(self.imported_actions)
    
    @property
    def failed_count(self) -> int:
        return len(self.failed_imports)
    
    def to_dict(self) -> dict:
        return {
            "version": self.version,
            "import_mode": self.import_mode,
            "imported_actions": [asdict(a) for a in self.imported_actions],
            "failed_imports": self.failed_imports
        }

    @classmethod
    def from_dict(cls, data: dict) -> 'ImportedAssetCollection':
        col = cls(
            version=data.get("version", "1.0"),
            import_mode=data.get("import_mode", ImportMode.FBX_MATCH.value),
            failed_imports=list(data.get("failed_imports", [])),
        )
        imported = []
        for item in data.get("imported_actions", []):
            try:
                imported.append(ImportedAction(**item))
            except TypeError:
                imported.append(ImportedAction(
                    action_name=item.get("action_name", ""),
                    source_manifest_ref=item.get("source_manifest_ref", ""),
                    source_file=item.get("source_file", ""),
                    staged_blend=item.get("staged_blend", ""),
                    import_status=item.get("import_status", "success"),
                    frame_range=tuple(item.get("frame_range", (0, 0))),
                    error_message=item.get("error_message", ""),
                ))
        col.imported_actions = imported
        return col


# ============================================================
# 目录条目
# ============================================================

@dataclass
class CatalogEntry:
    """目录条目"""
    uuid: str = ""
    path: str = ""
    action_count: int = 0


# ============================================================
# 资产库资产
# ============================================================

@dataclass
class LibraryAsset:
    """资产库中的资产"""
    action_name: str = ""
    catalog_id: str = ""
    blend_file: str = ""
    thumbnail_path: str = ""


# ============================================================
# 资产库清单
# ============================================================

@dataclass
class AssetLibraryManifest:
    """资产库清单 - 阶段3的输出"""
    version: str = "1.0"
    library_name: str = ""
    library_path: str = ""
    blend_files: List[str] = field(default_factory=list)
    catalog_entries: List[CatalogEntry] = field(default_factory=list)
    assets: List[LibraryAsset] = field(default_factory=list)
    
    @property
    def total_assets(self) -> int:
        return len(self.assets)
    
    def to_dict(self) -> dict:
        return {
            "version": self.version,
            "library_name": self.library_name,
            "library_path": self.library_path,
            "blend_files": self.blend_files,
            "catalog_entries": [asdict(c) for c in self.catalog_entries],
            "assets": [asdict(a) for a in self.assets]
        }
    
    def save_to_file(self, filepath: str):
        """保存到JSON文件"""
        os.makedirs(os.path.dirname(filepath) or '.', exist_ok=True)
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(self.to_dict(), f, ensure_ascii=False, indent=4)


# ============================================================
# 管线配置
# ============================================================

@dataclass
class PipelineConfig:
    """管线配置"""
    source_dir: str = ""
    output_dir: str = ""
    library_name: str = "Asset_Library"
    source_type: str = SourceType.UNITY_ANIM.value
    import_mode: str = ImportMode.FBX_MATCH.value
    
    # Unity动画特有配置
    unity_skip_processed: bool = True
    
    # 导入选项
    import_scale: float = 0.01
    rotation_only: bool = False
    import_curves: bool = False
    target_armature: str = ""
    skeleton_filter: str = ""
    import_batch_size: int = 300
    max_import_cycles: int = 200
    large_import_threshold: int = 2000
    max_consecutive_failures: int = 120
    import_resume_enabled: bool = True
    
    # 资产库选项
    chunk_size: int = 500
    force_rebuild: bool = False
    generate_thumbnails: bool = True
    thumb_resolution: str = "256"
    thumb_quality: str = "OPENGL"
    thumb_isolate: bool = True
    
    def to_dict(self) -> dict:
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: dict) -> 'PipelineConfig':
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


# ============================================================
# 管线日志
# ============================================================

@dataclass
class PipelineLog:
    """管线日志"""
    timestamp: str = ""
    stage: str = ""
    level: str = "info"
    message: str = ""
    
    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = datetime.now().isoformat()


# ============================================================
# 注册
# ============================================================

def register():
    """Core types不需要注册Blender类"""
    pass

def unregister():
    """Core types不需要注册Blender类"""
    pass
