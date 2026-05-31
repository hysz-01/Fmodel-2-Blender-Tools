# FModel_Tools/core/logger.py
# 日志系统 — 分级日志、自动备份、会话导出

import bpy
import os
import json
import shutil
import datetime
from pathlib import Path
from typing import Optional, Dict, Any, List
from enum import Enum


class LogLevel(Enum):
    """日志级别"""
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


class OperationType(Enum):
    """操作类型"""
    IMPORT_MODEL = "IMPORT_MODEL"
    IMPORT_ANIM = "IMPORT_ANIM"
    EXPORT = "EXPORT"
    ASSET_LIBRARY = "ASSET_LIBRARY"
    MATERIAL = "MATERIAL"
    SKELETON = "SKELETON"
    PIPELINE = "PIPELINE"
    BACKUP = "BACKUP"
    SYSTEM = "SYSTEM"


class FModelLogger:
    """FModel 统一日志管理器"""
    
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        self._initialized = True
        
        self.log_entries: List[Dict[str, Any]] = []
        self.log_dir: str = ""
        self.backup_dir: str = ""
        self.session_id: str = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        self.enable_file_logging: bool = True
        self.enable_backup: bool = True
        self.max_backup_count: int = 50
        
    def initialize(self, base_path: Optional[str] = None):
        """初始化日志系统
        
        Args:
            base_path: 基础路径，默认使用当前blend文件目录
        """
        if base_path is None:
            if bpy.data.filepath:
                base_path = os.path.dirname(bpy.data.filepath)
            else:
                base_path = os.path.expanduser("~/FModel_Tools_Logs")
        
        self.log_dir = os.path.join(base_path, "FModel_Logs")
        self.backup_dir = os.path.join(base_path, "FModel_Backups")
        
        os.makedirs(self.log_dir, exist_ok=True)
        os.makedirs(self.backup_dir, exist_ok=True)
        
        self.log(
            LogLevel.INFO,
            OperationType.SYSTEM,
            "日志系统初始化完成",
            {"log_dir": self.log_dir, "backup_dir": self.backup_dir}
        )
    
    def log(
        self,
        level: LogLevel,
        operation: OperationType,
        message: str,
        details: Optional[Dict[str, Any]] = None,
        context_objects: Optional[List[str]] = None
    ):
        """记录日志
        
        Args:
            level: 日志级别
            operation: 操作类型
            message: 日志消息
            details: 详细信息
            context_objects: 相关对象名称列表
        """
        timestamp = datetime.datetime.now().isoformat()
        
        try:
            blend_path = bpy.data.filepath or "未保存"
        except AttributeError:
            blend_path = "未保存"

        entry = {
            "timestamp": timestamp,
            "session_id": self.session_id,
            "level": level.value,
            "operation": operation.value if hasattr(operation, 'value') else str(operation),
            "message": message,
            "details": details or {},
            "context_objects": context_objects or [],
            "blend_file": blend_path
        }
        
        self.log_entries.append(entry)
        
        # 控制台输出
        prefix = f"[FModel {level.value}]"
        op_str = operation.value if hasattr(operation, 'value') else str(operation)
        print(f"{prefix} [{op_str}] {message}")
        
        # 写入文件
        if self.enable_file_logging and self.log_dir:
            self._write_to_file(entry)
    
    def _write_to_file(self, entry: Dict[str, Any]):
        """将日志条目写入文件"""
        try:
            # 按日期分文件
            date_str = datetime.datetime.now().strftime("%Y%m%d")
            log_file = os.path.join(self.log_dir, f"fmodel_log_{date_str}.json")
            
            # 读取现有日志
            existing_logs = []
            if os.path.exists(log_file):
                with open(log_file, 'r', encoding='utf-8') as f:
                    try:
                        existing_logs = json.load(f)
                    except json.JSONDecodeError:
                        existing_logs = []
            
            # 添加新条目
            existing_logs.append(entry)
            
            # 写入文件
            with open(log_file, 'w', encoding='utf-8') as f:
                json.dump(existing_logs, f, ensure_ascii=False, indent=2)
                
        except Exception as e:
            print(f"[FModel Logger] 写入日志文件失败: {e}")
    
    def create_backup(
        self,
        backup_type: str,
        files_to_backup: List[str],
        description: str = "",
        metadata: Optional[Dict[str, Any]] = None
    ) -> Optional[str]:
        """创建备份
        
        Args:
            backup_type: 备份类型标识
            files_to_backup: 要备份的文件路径列表
            description: 备份描述
            metadata: 额外元数据
            
        Returns:
            备份文件夹路径，失败返回None
        """
        if not self.enable_backup or not self.backup_dir:
            return None
        
        try:
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_name = f"{backup_type}_{timestamp}"
            backup_path = os.path.join(self.backup_dir, backup_name)
            
            os.makedirs(backup_path, exist_ok=True)
            
            backed_up_files = []
            
            for file_path in files_to_backup:
                if not file_path or not os.path.exists(file_path):
                    continue
                
                try:
                    file_name = os.path.basename(file_path)
                    dest_path = os.path.join(backup_path, file_name)
                    
                    if os.path.isfile(file_path):
                        shutil.copy2(file_path, dest_path)
                        backed_up_files.append(file_path)
                    elif os.path.isdir(file_path):
                        shutil.copytree(file_path, os.path.join(backup_path, file_name))
                        backed_up_files.append(file_path)
                        
                except Exception as e:
                    self.log(
                        LogLevel.WARNING,
                        OperationType.BACKUP,
                        f"备份文件失败: {file_path}",
                        {"error": str(e)}
                    )
            
            # 保存备份元数据
            meta_info = {
                "backup_type": backup_type,
                "timestamp": timestamp,
                "description": description,
                "backed_up_files": backed_up_files,
                "original_blend": bpy.data.filepath,
                "custom_metadata": metadata or {}
            }
            
            meta_file = os.path.join(backup_path, "_backup_info.json")
            with open(meta_file, 'w', encoding='utf-8') as f:
                json.dump(meta_info, f, ensure_ascii=False, indent=2)
            
            self.log(
                LogLevel.INFO,
                OperationType.BACKUP,
                f"创建备份成功: {backup_name}",
                {
                    "backup_path": backup_path,
                    "files_count": len(backed_up_files),
                    "description": description
                }
            )
            
            # 清理旧备份
            self._cleanup_old_backups(backup_type)
            
            return backup_path
            
        except Exception as e:
            self.log(
                LogLevel.ERROR,
                OperationType.BACKUP,
                f"创建备份失败",
                {"error": str(e)}
            )
            return None
    
    def _cleanup_old_backups(self, backup_type: str):
        """清理旧的备份，保留最新的N个"""
        try:
            backups = []
            for item in os.listdir(self.backup_dir):
                if item.startswith(backup_type + "_") and os.path.isdir(os.path.join(self.backup_dir, item)):
                    backups.append(item)
            
            backups.sort(reverse=True)
            
            for old_backup in backups[self.max_backup_count:]:
                old_path = os.path.join(self.backup_dir, old_backup)
                shutil.rmtree(old_path)
                self.log(
                    LogLevel.DEBUG,
                    OperationType.BACKUP,
                    f"清理旧备份: {old_backup}"
                )
                
        except Exception as e:
            self.log(
                LogLevel.WARNING,
                OperationType.BACKUP,
                "清理旧备份失败",
                {"error": str(e)}
            )
    
    def backup_blend_file(self, description: str = "") -> Optional[str]:
        """备份当前blend文件
        
        Args:
            description: 备份描述
            
        Returns:
            备份文件路径
        """
        if not bpy.data.filepath:
            self.log(
                LogLevel.WARNING,
                OperationType.BACKUP,
                "无法备份：当前工程未保存"
            )
            return None
        
        backup_path = self.create_backup(
            "BLEND",
            [bpy.data.filepath],
            description,
            {"scene_objects": [obj.name for obj in bpy.context.scene.objects]}
        )
        
        return backup_path
    
    def backup_before_operation(
        self,
        operation_name: str,
        additional_files: Optional[List[str]] = None
    ) -> Optional[str]:
        """在重大操作前自动备份
        
        Args:
            operation_name: 操作名称
            additional_files: 额外要备份的文件
            
        Returns:
            备份路径
        """
        files_to_backup = []
        
        if bpy.data.filepath:
            files_to_backup.append(bpy.data.filepath)
        
        if additional_files:
            files_to_backup.extend(additional_files)
        
        return self.create_backup(
            "PRE_OP",
            files_to_backup,
            f"操作前备份: {operation_name}",
            {"operation": operation_name}
        )
    
    def get_recent_logs(self, count: int = 50) -> List[Dict[str, Any]]:
        """获取最近的日志条目
        
        Args:
            count: 返回的条目数量
            
        Returns:
            日志条目列表
        """
        return self.log_entries[-count:]
    
    def get_operation_summary(self) -> Dict[str, Any]:
        """获取操作摘要统计
        
        Returns:
            统计信息字典
        """
        summary = {
            "total_operations": len(self.log_entries),
            "by_level": {},
            "by_operation": {},
            "errors": []
        }
        
        for entry in self.log_entries:
            level = entry["level"]
            operation = entry["operation"]
            
            summary["by_level"][level] = summary["by_level"].get(level, 0) + 1
            summary["by_operation"][operation] = summary["by_operation"].get(operation, 0) + 1
            
            if level in ["ERROR", "CRITICAL"]:
                summary["errors"].append({
                    "timestamp": entry["timestamp"],
                    "message": entry["message"],
                    "details": entry.get("details", {})
                })
        
        return summary
    
    def export_session_log(self, output_path: Optional[str] = None) -> str:
        """导出当前会话的完整日志
        
        Args:
            output_path: 输出文件路径
            
        Returns:
            导出文件路径
        """
        if output_path is None:
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            output_path = os.path.join(self.log_dir, f"session_log_{timestamp}.json")
        
        session_data = {
            "session_id": self.session_id,
            "export_time": datetime.datetime.now().isoformat(),
            "blend_file": bpy.data.filepath,
            "entries": self.log_entries,
            "summary": self.get_operation_summary()
        }
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(session_data, f, ensure_ascii=False, indent=2)
        
        return output_path


# 全局日志器实例
_logger = FModelLogger()


def get_logger() -> FModelLogger:
    """获取全局日志器实例"""
    return _logger


def initialize_logging(base_path: Optional[str] = None):
    """初始化日志系统"""
    _logger.initialize(base_path)


# 便捷函数
def log_info(operation: OperationType, message: str, details: Optional[Dict] = None):
    _logger.log(LogLevel.INFO, operation, message, details)


def log_warning(operation: OperationType, message: str, details: Optional[Dict] = None):
    _logger.log(LogLevel.WARNING, operation, message, details)


def log_error(operation: OperationType, message: str, details: Optional[Dict] = None):
    _logger.log(LogLevel.ERROR, operation, message, details)


def log_success(operation: OperationType, message: str, details: Optional[Dict] = None):
    _logger.log(LogLevel.INFO, operation, f"✅ {message}", details)


def backup_before(operation_name: str, additional_files: Optional[List[str]] = None) -> Optional[str]:
    """操作前备份的便捷函数"""
    return _logger.backup_before_operation(operation_name, additional_files)


def register():
    """Core logger不需要注册Blender类"""
    pass


def unregister():
    """Core logger不需要注册Blender类"""
    pass