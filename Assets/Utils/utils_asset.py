# FModel_Tools/Assets/Utils/utils_asset.py
# 核心工具 — 缩略图生成、骨架名解析、资产库挂载
import os
import json
import uuid
import bpy
import re
from ...core.utils import (
    get_or_create_catalog_uuid as core_get_or_create_catalog_uuid,
    mount_dynamic_library as core_mount_dynamic_library,
    cleanup_dynamic_libraries as core_cleanup_dynamic_libraries,
)

def get_skeleton_name_from_json(json_path):
    if not json_path or not os.path.exists(json_path): return ""
    try:
        with open(json_path, 'r', encoding='utf-8-sig', errors='ignore') as f:
            raw_data = json.load(f)
            if not isinstance(raw_data, list): return ""

            target_item = None
            for item in raw_data:
                if not isinstance(item, dict): continue
                if item.get("Type", "") in ["AnimSequence", "SkeletalMesh", "Skeleton"]:
                    target_item = item
                    break
            
            items_to_scan = [target_item] if target_item else raw_data
            for item in items_to_scan:
                if not isinstance(item, dict): continue
                if item.get("Type") == "Skeleton": return item.get("Name", "")
                skeleton_info = item.get("Skeleton", {}) or item.get("Properties", {}).get("Skeleton", {})
                if isinstance(skeleton_info, dict):
                    obj_name = skeleton_info.get("ObjectName", "")
                    if obj_name:
                        match = re.search(r"'(.*?)'", obj_name)
                        return match.group(1) if match else obj_name
                elif isinstance(skeleton_info, str):
                    match = re.search(r"'(.*?)'", skeleton_info)
                    return match.group(1) if match else skeleton_info
    except (json.JSONDecodeError, IOError, ValueError) as e:
        # JSON解析或文件访问失败，返回空字符串
        pass
    return ""

def validate_skeleton_match(json_path, filter_name):
    if not filter_name or not os.path.exists(json_path): return True 
    sk_name = get_skeleton_name_from_json(json_path)
    if sk_name:
        return filter_name.lower() in sk_name.lower() or sk_name.lower() in filter_name.lower()
    return True

def parse_ueanim_path_from_json(json_path):
    if not os.path.exists(json_path): return ""
    try:
        with open(json_path, 'r', encoding='utf-8-sig', errors='ignore') as f:
            raw_data = json.load(f)
            if isinstance(raw_data, list):
                for item in raw_data:
                    if not isinstance(item, dict): continue
                    obj_path = item.get("Outer", {}).get("ObjectPath", "") or item.get("ObjectPath", "")
                    if obj_path and "/Game/" in obj_path:
                        clean_path = obj_path.split('.')[0].replace('\\', '/')
                        dir_path = os.path.dirname(clean_path)
                        return dir_path[1:] if dir_path.startswith('/') else dir_path
    except (json.JSONDecodeError, KeyError, ValueError, IndexError) as e:
        # JSON解析或字典访问失败，返回空字符串
        pass
    return ""

def get_or_create_catalog_uuid(asset_dir, ue_path, sk_name=""):
    return core_get_or_create_catalog_uuid(asset_dir, ue_path, sk_name)


def mount_dynamic_library(lib_name, lib_path):
    return core_mount_dynamic_library(lib_name, lib_path)


def cleanup_dynamic_libraries():
    return core_cleanup_dynamic_libraries()

def bake_thumbnail_opengl(target_arm, action, out_dir, sk_name, resolution='256', quality='OPENGL', isolate=True):
    cam_obj = None
    cam_data = None
    orig_cam = bpy.context.scene.camera
    space = None
    orig_type, orig_color, orig_wire = None, None, False
    
    try:
        res_val = int(resolution)
        if not target_arm.animation_data: target_arm.animation_data_create()
        target_arm.animation_data.action = action
        
        frame_to_bake = min(10, int(action.frame_range[1])) if action.frame_range else 10
        bpy.context.scene.frame_set(frame_to_bake)
        bpy.context.view_layer.update()

        thumb_dir = os.path.join(out_dir, ".thumbnails", sk_name)
        os.makedirs(thumb_dir, exist_ok=True)
        
        safe_name = "".join([c for c in action.name if c.isalpha() or c.isdigit() or c in (' ', '-', '_')]).rstrip()
        # Deterministic hash from action name + frame range — same action always same thumbnail
        hash_input = f"{action.name}_{int(action.frame_range[0])}_{int(action.frame_range[1])}"
        unique_suffix = uuid.uuid5(uuid.NAMESPACE_OID, hash_input).hex[:8] 
        
        final_img_name = f"{safe_name}_{unique_suffix}.webp"
        tmp_prefix = os.path.join(thumb_dir, f"{safe_name}_{unique_suffix}_tmp_")
        final_img_path = os.path.join(thumb_dir, final_img_name)

        area = next((a for a in bpy.context.screen.areas if a.type == 'VIEW_3D'), None)
        if not area:
            return ""
            
        region = next((r for r in area.regions if r.type == 'WINDOW'), None)
        space = area.spaces.active

        orig_type = space.shading.type
        orig_color = space.shading.color_type
        try:
            orig_wire = space.overlay.show_wireframes
            space.overlay.show_wireframes = True
        except (AttributeError, TypeError):
            # 视图区域属性访问失败，不影响主要功能
            pass

        space.shading.type = 'SOLID'
        space.shading.color_type = 'RANDOM'

        bpy.ops.object.select_all(action='DESELECT')
        has_mesh = False
        for c in target_arm.children:
            if c.type == 'MESH': 
                c.select_set(True)
                has_mesh = True
                
        if not has_mesh: target_arm.select_set(True)
            
        bpy.context.view_layer.objects.active = target_arm

        cam_data = bpy.data.cameras.new("FModel_ThumbCam")
        cam_obj = bpy.data.objects.new("FModel_ThumbCam", cam_data)
        bpy.context.scene.collection.objects.link(cam_obj)
        bpy.context.scene.camera = cam_obj

        override = {'window': bpy.context.window, 'screen': bpy.context.screen, 'area': area, 'region': region}

        with bpy.context.temp_override(**override):
            bpy.ops.view3d.view_selected() 
            bpy.ops.view3d.camera_to_view()

        # Render settings (outside override, shared by both modes)
        orig_x = bpy.context.scene.render.resolution_x
        orig_y = bpy.context.scene.render.resolution_y
        orig_path = bpy.context.scene.render.filepath
        orig_fmt = bpy.context.scene.render.image_settings.file_format
        orig_quality = bpy.context.scene.render.image_settings.quality
        orig_color_mode = bpy.context.scene.render.image_settings.color_mode

        bpy.context.scene.render.resolution_x = res_val
        bpy.context.scene.render.resolution_y = res_val
        bpy.context.scene.render.image_settings.file_format = 'WEBP'
        bpy.context.scene.render.image_settings.quality = 90
        bpy.context.scene.render.image_settings.color_mode = 'RGBA'
        bpy.context.scene.render.filepath = tmp_prefix

        # Collect child mesh objects for isolate mode
        child_objects = set()
        if isolate:
            for c in target_arm.children_recursive:
                if c.type == 'MESH':
                    child_objects.add(c)

        # Hide non-child objects if isolating
        hidden = {}
        if isolate and child_objects:
            for obj in bpy.context.scene.objects:
                if obj.type == 'MESH' and obj not in child_objects:
                    hidden[obj] = obj.hide_render
                    obj.hide_render = True

        if quality == 'RENDER':
            bpy.ops.render.render(write_still=True)
        else:
            bpy.ops.render.opengl(write_still=True, view_context=False)

        bpy.context.scene.render.resolution_x = orig_x
        bpy.context.scene.render.resolution_y = orig_y
        bpy.context.scene.render.filepath = orig_path
        bpy.context.scene.render.image_settings.file_format = orig_fmt
        bpy.context.scene.render.image_settings.quality = orig_quality
        bpy.context.scene.render.image_settings.color_mode = orig_color_mode

        # Restore hidden objects
        for obj, orig_hidden in hidden.items():
            obj.hide_render = orig_hidden

        # 防弹机制：模糊匹配查找 _tmp_ 文件
        saved_file = None
        for f in os.listdir(thumb_dir):
            if f.startswith(f"{safe_name}_{unique_suffix}_tmp_"):
                saved_file = f
                break
                
        if saved_file:
            tmp_file_path = os.path.join(thumb_dir, saved_file)
            if os.path.exists(final_img_path): os.remove(final_img_path)
            os.rename(tmp_file_path, final_img_path)
            return os.path.relpath(final_img_path, out_dir).replace('\\', '/')
        else:
            return ""
            
    except Exception as e:
        import traceback
        traceback.print_exc()
        return ""
    finally:
        if cam_obj: bpy.data.objects.remove(cam_obj, do_unlink=True)
        if cam_data: bpy.data.cameras.remove(cam_data, do_unlink=True)
        bpy.context.scene.camera = orig_cam
        
        if space:
            space.shading.type = orig_type
            space.shading.color_type = orig_color
            try:
                space.overlay.show_wireframes = orig_wire
            except (AttributeError, TypeError):
                # 视图区域属性访问失败，不影响主要功能
                pass
