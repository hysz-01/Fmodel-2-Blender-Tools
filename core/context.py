# FModel_Tools/core/context.py
# 管线上下文 — PipelineContext 数据载体

import json
import uuid
import os
from dataclasses import dataclass, field, asdict
from typing import Dict, List, Optional, Any
from datetime import datetime

import bpy

from .enums import PipelineStage, StageStatus
from .types import PipelineConfig


@dataclass
class PipelineContext:
    """管线流程上下文 - 统一数据载体
    
    这是整个管线流程的核心数据结构，在四个阶段之间传递所有必要的信息。
    
    使用示例:
        context = PipelineContext()
        context.config = {"source_dir": "/path", ...}
        context.log("stage1", "info", "开始处理")
        context.save_to_file("checkpoint.json")
    """
    
    # 基本信息
    pipeline_id: str = ""
    created_at: str = ""
    current_stage: str = PipelineStage.DICTIONARY_ACQUISITION.value
    status: str = StageStatus.PENDING.value
    
    # 各阶段数据 (使用Optional和Dict以便序列化)
    dictionary_manifest: Optional[Dict] = None
    imported_assets: Optional[Dict] = None
    library_manifest: Optional[Dict] = None
    
    # 配置
    config: Dict[str, Any] = field(default_factory=dict)
    
    # 日志
    logs: List[Dict[str, str]] = field(default_factory=list)
    
    # 阶段状态追踪
    stage_status: Dict[str, str] = field(default_factory=lambda: {
        PipelineStage.DICTIONARY_ACQUISITION.value: StageStatus.PENDING.value,
        PipelineStage.FORMAT_CONVERSION.value: StageStatus.PENDING.value,
        PipelineStage.ASSET_IMPORT.value: StageStatus.PENDING.value,
        PipelineStage.LIBRARY_BUILDING.value: StageStatus.PENDING.value,
        PipelineStage.FINALIZATION.value: StageStatus.PENDING.value,
    })
    
    def __post_init__(self):
        if not self.pipeline_id:
            self.pipeline_id = str(uuid.uuid4())
        if not self.created_at:
            self.created_at = datetime.now().isoformat()
    
    # ============================================================
    # 日志方法
    # ============================================================
    
    def log(self, stage: str, level: str, message: str):
        """添加日志条目"""
        self.logs.append({
            "timestamp": datetime.now().isoformat(),
            "stage": stage,
            "level": level,
            "message": message
        })
    
    def log_info(self, stage: str, message: str):
        """添加信息日志"""
        self.log(stage, "info", message)
    
    def log_warning(self, stage: str, message: str):
        """添加警告日志"""
        self.log(stage, "warning", message)
    
    def log_error(self, stage: str, message: str):
        """添加错误日志"""
        self.log(stage, "error", message)
    
    # ============================================================
    # 阶段状态管理
    # ============================================================
    
    def set_stage_status(self, stage: str, status: str):
        """设置阶段状态"""
        self.stage_status[stage] = status
        self.current_stage = stage
        
        if status == StageStatus.COMPLETED.value:
            self.log_info(stage, f"阶段 {stage} 完成")
        elif status == StageStatus.FAILED.value:
            self.log_error(stage, f"阶段 {stage} 失败")
    
    def get_stage_status(self, stage: str) -> str:
        """获取阶段状态"""
        return self.stage_status.get(stage, StageStatus.PENDING.value)
    
    def is_stage_completed(self, stage: str) -> bool:
        """检查阶段是否完成"""
        return self.get_stage_status(stage) == StageStatus.COMPLETED.value
    
    def get_next_stage(self) -> Optional[str]:
        """获取下一个待执行阶段"""
        stages = [
            PipelineStage.DICTIONARY_ACQUISITION.value,
            PipelineStage.FORMAT_CONVERSION.value,
            PipelineStage.ASSET_IMPORT.value,
            PipelineStage.LIBRARY_BUILDING.value,
            PipelineStage.FINALIZATION.value,
        ]
        for stage in stages:
            if not self.is_stage_completed(stage):
                return stage
        return None
    
    # ============================================================
    # 配置访问
    # ============================================================
    
    def get_config(self, key: str, default: Any = None) -> Any:
        """获取配置值"""
        return self.config.get(key, default)
    
    def set_config(self, key: str, value: Any):
        """设置配置值"""
        self.config[key] = value
    
    # ============================================================
    # 序列化方法
    # ============================================================
    
    def to_dict(self) -> dict:
        """转换为可序列化的字典"""
        return {
            "pipeline_id": self.pipeline_id,
            "created_at": self.created_at,
            "current_stage": self.current_stage,
            "status": self.status,
            "dictionary_manifest": self.dictionary_manifest,
            "imported_assets": self.imported_assets,
            "library_manifest": self.library_manifest,
            "config": self.config,
            "logs": self.logs,
            "stage_status": self.stage_status
        }
    
    def to_json(self, indent: int = 4) -> str:
        """转换为JSON字符串"""
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=indent)
    
    def save_to_file(self, filepath: str):
        """保存到文件"""
        os.makedirs(os.path.dirname(filepath) or '.', exist_ok=True)
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(self.to_dict(), f, ensure_ascii=False, indent=4)
    
    @classmethod
    def from_dict(cls, data: dict) -> 'PipelineContext':
        """从字典创建实例"""
        return cls(**data)
    
    @classmethod
    def from_json(cls, json_str: str) -> 'PipelineContext':
        """从JSON字符串创建实例"""
        return cls.from_dict(json.loads(json_str))
    
    @classmethod
    def load_from_file(cls, filepath: str) -> 'PipelineContext':
        """从文件加载"""
        with open(filepath, 'r', encoding='utf-8') as f:
            return cls.from_dict(json.load(f))
    
    # ============================================================
    # Blender文本块操作 (便于调试)
    # ============================================================
    
    def save_to_blender_text(self, text_name: str = "PipelineContext"):
        """保存到Blender内部文本块"""
        if text_name in bpy.data.texts:
            text_block = bpy.data.texts[text_name]
            text_block.clear()
        else:
            text_block = bpy.data.texts.new(text_name)
        text_block.write(self.to_json())
    
    @classmethod
    def load_from_blender_text(cls, text_name: str = "PipelineContext") -> Optional['PipelineContext']:
        """从Blender内部文本块加载"""
        if text_name not in bpy.data.texts:
            return None
        try:
            return cls.from_json(bpy.data.texts[text_name].as_string())
        except Exception:
            return None
    
    @classmethod
    def clear_blender_text(cls, text_name: str = "PipelineContext"):
        """清除Blender内部文本块"""
        if text_name in bpy.data.texts:
            bpy.data.texts.remove(bpy.data.texts[text_name])


# ============================================================
# 注册
# ============================================================

def register():
    """Core context不需要注册Blender类"""
    pass

def unregister():
    """Core context不需要注册Blender类"""
    pass
