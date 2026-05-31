# FModel_Tools/auto_handlers.py
# 自动处理器 — 文件加载时自动挂载资产库 + vendor依赖注册

import bpy
import os
import time
import threading
from bpy.app.handlers import persistent

# ============================================================
# 防抖机制
# ============================================================

_last_scan_time = 0
_scan_cooldown = 2.0
_pending_scan = False
_scan_lock = threading.RLock()


def _debounced_scan():
    global _last_scan_time, _pending_scan
    current_time = time.time()
    with _scan_lock:
        if current_time - _last_scan_time < _scan_cooldown:
            if not _pending_scan:
                _pending_scan = True
                remaining = _scan_cooldown - (current_time - _last_scan_time)
                bpy.app.timers.register(_delayed_scan, first_interval=remaining)
            return
        _execute_scan()


def _delayed_scan():
    global _pending_scan
    _pending_scan = False
    _execute_scan()
    return None


def _execute_scan():
    global _last_scan_time
    _last_scan_time = time.time()
    try:
        if hasattr(bpy.context.scene, "fmodel_anim_manager"):
            bpy.ops.fmodel.scan_anims()
            print("[FModel Auto] 资产树已自动刷新")
    except Exception as e:
        print(f"[FModel Auto] 自动扫描失败: {e}")


# ============================================================
# 文件加载处理器
# ============================================================

@persistent
def on_file_load_post(dummy):
    def init_environment():
        try:
            from .core.utils import cleanup_dynamic_libraries, mount_dynamic_library
            print("[FModel Auto] 工程加载，开始初始化...")
            cleanup_dynamic_libraries()
            if hasattr(bpy.context.scene, "fmodel_assets"):
                for lib in bpy.context.scene.fmodel_assets.project_libs:
                    if lib.path:
                        mount_dynamic_library(lib.name, lib.path)
            if hasattr(bpy.context.scene, "fmodel_anim_manager"):
                bpy.ops.fmodel.scan_anims()
                print("[FModel Auto] 资产库已自动挂载并扫描")
        except Exception as e:
            print(f"[FModel Auto] 环境初始化失败: {e}")
        return None
    bpy.app.timers.register(init_environment, first_interval=0.8)


# ============================================================
# 场景更新处理器
# ============================================================

_imported_objects_cache = set()
_first_run = True
_scene_update_lock = threading.RLock()


def _update_object_cache():
    global _imported_objects_cache
    _imported_objects_cache = {obj.name for obj in bpy.data.objects}


@persistent
def on_depsgraph_update_post(scene, depsgraph):
    global _first_run, _imported_objects_cache
    with _scene_update_lock:
        if _first_run:
            _first_run = False
            _update_object_cache()
            return

    current_objects = {obj.name for obj in bpy.data.objects}
    new_objects = current_objects - _imported_objects_cache

    if new_objects:
        has_relevant_import = False
        for obj_name in new_objects:
            obj = bpy.data.objects.get(obj_name)
            if obj and obj.type in ('MESH', 'ARMATURE'):
                if any(key.startswith('gltf_import_path') or key.startswith('FModel')
                       for key in obj.keys()):
                    has_relevant_import = True
                    break
        with _scene_update_lock:
            _imported_objects_cache = current_objects
        if has_relevant_import:
            print(f"[FModel Auto] 检测到新导入对象: {new_objects}")
            _debounced_scan()


# ============================================================
# 注册管理
# ============================================================

_handlers_registered = False
_timers_active = True
_vendor_registered = set()
_added_paths = set()


def register_handlers():
    global _handlers_registered, _first_run, _timers_active
    if _handlers_registered:
        return

    if on_file_load_post not in bpy.app.handlers.load_post:
        bpy.app.handlers.load_post.append(on_file_load_post)
    if on_depsgraph_update_post not in bpy.app.handlers.depsgraph_update_post:
        bpy.app.handlers.depsgraph_update_post.append(on_depsgraph_update_post)

    with _scene_update_lock:
        _first_run = True
    _handlers_registered = True
    _timers_active = True
    print("[FModel Auto] 自动触发器已注册")
    bpy.app.timers.register(_ensure_dependency_addons, first_interval=5.0)


def _ensure_dependency_addons():
    global _timers_active
    if not _timers_active:
        return None

    import sys
    prefs = bpy.context.preferences
    if prefs is None:
        print("[FModel] 无法获取用户偏好，跳过依赖检查")
        return None
    addons = prefs.addons

    bundled = {
        "io_scene_ueformat": os.path.join(os.path.dirname(__file__), "vendor", "io_scene_ueformat"),
        "io_scene_psk_psa": os.path.join(os.path.dirname(__file__), "vendor", "io_scene_psk_psa"),
    }

    for module_id, bundle_path in bundled.items():
        if module_id in addons:
            print(f"[FModel] {module_id} 已由用户安装，跳过")
            continue
        if module_id in _vendor_registered:
            print(f"[FModel] {module_id} 已通过内置副本注册，跳过")
            continue
        if not os.path.isdir(bundle_path):
            continue
        try:
            parent = os.path.dirname(bundle_path)
            if parent not in sys.path:
                sys.path.insert(0, parent)
                _added_paths.add(parent)

            _install_vendor_wheels(bundle_path)

            # 检测是否已有类残留 (Blender 启动文件缓存等)
            mod = __import__(module_id)
            if hasattr(mod, "register"):
                pre_check = _vendor_already_in_registry(mod)
                if pre_check:
                    print(f"[FModel] {module_id} 类已存在 (启动缓存), 跳过重复注册")
                    _vendor_registered.add(module_id)
                    continue
                mod.register()
            _vendor_registered.add(module_id)
            print(f"[FModel] {module_id} 内置副本已注册")
        except Exception as e:
            print(f"[FModel] {module_id} 内置注册失败: {e}")

    return None


_KNOWN_VENDOR_CLASSES = {
    "io_scene_psk_psa": ["PSK_OT_import", "PSA_OT_export"],
    "io_scene_ueformat": ["UFImportUEModel", "UFImportUEAnim", "UFImportUEPose"],
}


def _vendor_already_in_registry(mod) -> bool:
    """检查 vendor addon 的已知类是否已在 Blender 类型表中 (防止重复注册噪音)"""
    for module_id, class_names in _KNOWN_VENDOR_CLASSES.items():
        if mod.__name__ == module_id:
            return any(hasattr(bpy.types, cn) for cn in class_names)
    return False


def _install_vendor_wheels(bundle_path):
    import sys, zipfile, tempfile
    wheels_dir = os.path.join(bundle_path, "wheels")
    if not os.path.isdir(wheels_dir):
        return
    cache_dir = os.path.join(tempfile.gettempdir(), "fmodel_wheel_cache")
    for entry in sorted(os.listdir(wheels_dir)):
        if not entry.endswith(".whl"):
            continue
        wheel_path = os.path.join(wheels_dir, entry)
        wheel_name = entry.rsplit(".", 1)[0]
        extract_dir = os.path.join(cache_dir, wheel_name)
        if not os.path.isdir(extract_dir):
            os.makedirs(extract_dir, exist_ok=True)
            with zipfile.ZipFile(wheel_path, 'r') as zf:
                zf.extractall(extract_dir)
        if extract_dir not in sys.path:
            sys.path.insert(0, extract_dir)
            _added_paths.add(extract_dir)


def unregister_handlers():
    global _handlers_registered, _timers_active
    _timers_active = False

    if on_file_load_post in bpy.app.handlers.load_post:
        bpy.app.handlers.load_post.remove(on_file_load_post)
    if on_depsgraph_update_post in bpy.app.handlers.depsgraph_update_post:
        bpy.app.handlers.depsgraph_update_post.remove(on_depsgraph_update_post)

    _unregister_vendor_addons()

    import sys
    for path in sorted(_added_paths, reverse=True):
        if path in sys.path:
            sys.path.remove(path)
    _added_paths.clear()
    _vendor_registered.clear()

    with _scene_update_lock:
        _handlers_registered = False
    print("[FModel Auto] 自动触发器已注销")


def _unregister_vendor_addons():
    global _vendor_registered
    for module_id in sorted(_vendor_registered):
        try:
            mod = __import__(module_id)
            if hasattr(mod, "unregister"):
                mod.unregister()
            print(f"[FModel] {module_id} 内置副本已注销")
        except Exception as e:
            print(f"[FModel] {module_id} 内置副本注销失败: {e}")
