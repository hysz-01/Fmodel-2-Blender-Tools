# FModel_Tools/core/utils.py
# 工具函数 — 路径处理、hash 校验、资产库挂载

import os
import uuid
import bpy


def normalize_path(path: str) -> str:
    """标准化路径（统一使用正斜杠）"""
    return path.replace('\\', '/').strip('/')


def safe_relpath(path: str, start: str) -> str:
    """安全的相对路径计算（处理跨盘符情况）"""
    try:
        return os.path.relpath(path, start).replace('\\', '/')
    except ValueError:
        return normalize_path(path)


def ensure_dir(directory: str) -> bool:
    """确保目录存在"""
    if not directory:
        return False
    try:
        os.makedirs(directory, exist_ok=True)
        return True
    except Exception:
        return False


def get_blend_dir() -> str:
    """获取当前blend文件所在目录"""
    if bpy.data.filepath:
        return os.path.dirname(bpy.data.filepath)
    return ""


def get_or_create_catalog_uuid(asset_dir: str, catalog_path: str, sk_name: str = "") -> str:
    """基于路径生成稳定的UUID并写入资产目录配置文件
    
    Args:
        asset_dir: 资产目录路径
        catalog_path: 目录路径
        sk_name: 骨架名称
    
    Returns:
        str: 目录UUID
    """
    clean_path = normalize_path(catalog_path or "Uncategorized")
    if sk_name:
        clean_path = f"{sk_name}/{clean_path}"
    
    catalog_uuid = str(uuid.uuid5(uuid.NAMESPACE_URL, clean_path))
    catalog_name = clean_path.split('/')[-1] if '/' in clean_path else clean_path
    cats_path = os.path.join(asset_dir, "blender_assets.cats.txt")
    
    existing_lines = []
    if os.path.exists(cats_path):
        with open(cats_path, 'r', encoding='utf-8') as f:
            existing_lines = f.readlines()
    
    if not any(catalog_uuid in line for line in existing_lines):
        with open(cats_path, 'a', encoding='utf-8') as f:
            if not existing_lines:
                f.write("VERSION 1\n\n")
            f.write(f"{catalog_uuid}:{clean_path}:{catalog_name}\n")
    
    return catalog_uuid


def mount_dynamic_library(lib_name: str, lib_path: str) -> bool:
    """动态挂载资产库到Blender
    
    Args:
        lib_name: 库名称
        lib_path: 库路径
    
    Returns:
        bool: 是否成功
    """
    prefs = bpy.context.preferences
    target_name = f"[FModel_Auto] {lib_name}"
    abs_target_path = os.path.normpath(bpy.path.abspath(lib_path))
    
    # 查找是否已存在
    for lib in prefs.filepaths.asset_libraries:
        if os.path.normpath(bpy.path.abspath(lib.path)) == abs_target_path or lib.name == target_name:
            lib.name = target_name
            lib.path = abs_target_path
            return True
    
    # 添加新库
    try:
        bpy.ops.preferences.asset_library_add(directory=abs_target_path)
        prefs.filepaths.asset_libraries[-1].name = target_name
        return True
    except Exception:
        return False


def cleanup_dynamic_libraries():
    """清理动态挂载的资产库"""
    prefs = bpy.context.preferences
    libs = prefs.filepaths.asset_libraries
    
    for i in range(len(libs) - 1, -1, -1):
        if libs[i].name.startswith("[FModel_Auto]"):
            try:
                bpy.ops.preferences.asset_library_remove(index=i)
            except Exception:
                pass


def deep_purge_orphans():
    """深度清理孤立数据"""
    for _ in range(3):
        for data_collections in (
            bpy.data.meshes, bpy.data.materials, bpy.data.textures,
            bpy.data.images, bpy.data.armatures, bpy.data.actions, bpy.data.node_groups
        ):
            for block in list(data_collections):
                if block.users == 0:
                    try:
                        data_collections.remove(block)
                    except Exception:
                        pass


def safe_invert_matrix(m):
    """安全的矩阵反转"""
    from mathutils import Matrix
    try:
        return m.inverted()
    except ValueError:
        return Matrix()


def get_ueformat_api():
    """获取 UEFormat 插件的 API
    
    Returns:
        tuple: (UEFormatImport, UEModelOptions, UEAnimOptions, UEPoseOptions)
               如果未找到插件，返回 (None, None, None, None)
    """
    import sys
    import importlib
    
    try:
        from io_scene_ueformat.importer.logic import UEFormatImport
        from io_scene_ueformat.options import UEModelOptions, UEAnimOptions, UEPoseOptions
        return UEFormatImport, UEModelOptions, UEAnimOptions, UEPoseOptions
    except ImportError:
        pass
        
    for mod_name in list(sys.modules.keys()):
        if mod_name.endswith(".importer.logic"):
            base_name = mod_name.split(".importer.logic")[0]
            try:
                logic_mod = importlib.import_module(f"{base_name}.importer.logic")
                options_mod = importlib.import_module(f"{base_name}.options")
                return logic_mod.UEFormatImport, options_mod.UEModelOptions, options_mod.UEAnimOptions, options_mod.UEPoseOptions
            except Exception:
                pass
                
    return None, None, None, None


def register():
    """Core utils不需要注册Blender类"""
    pass

def unregister():
    """Core utils不需要注册Blender类"""
    pass