# FModel_Tools/Universal_tools/material/auto_resolve.py
# Phase 1-3: 导入后自动材质解析管线

import bpy
import os
import json
from typing import Optional

from .channel_resolver import ChannelResolver, GameProfile
from .manifest_builder import _resolve_search_root


def auto_resolve_materials_for_import(meshes, model_filepath=""):
    """导入模型后自动运行材质解析。Phase 1+2+3 新架构：JSON 驱动。"""
    props = bpy.context.scene.fmodel_material
    if not props.auto_resolve_on_import:
        return

    tex_dir = bpy.path.abspath(props.umodel_tex_dir) if props.umodel_tex_dir else ""
    mat_dir = bpy.path.abspath(props.umodel_mat_path) if props.umodel_mat_path else ""

    if model_filepath and (not tex_dir or not mat_dir):
        root = _resolve_search_root(model_filepath, props.search_depth)
        if not tex_dir:
            tex_dir = root
        if not mat_dir:
            mat_dir = os.path.join(root, "Material")

    if not props.resolver_v2_enabled:
        props.resolver_v2_enabled = True

    # Phase 1
    from .manifest_builder import ManifestBuilder
    builder = ManifestBuilder(model_filepath, search_depth=props.search_depth)
    manifests = builder.discover()
    active = [m for m in manifests if m.is_active]
    print(f"[FModel] Phase 1: {len(active)}/{len(manifests)} active material slots")

    # Phase 1b
    if not active and model_filepath:
        if not props.heuristic_fallback_enabled:
            print("[FModel] Phase 1b: 无模型JSON，猜测式匹配已关闭，跳过")
        else:
            slot_names = []
            for obj in meshes:
                for slot in obj.material_slots:
                    if slot.material and slot.name not in slot_names:
                        slot_names.append(slot.name)
            print("[FModel] Phase 1b: 猜测式匹配 (无模型JSON) — ⚠ 匹配基于文本相似度，可能将错误贴图链接到材质")
            manifests = ManifestBuilder.discover_heuristic(slot_names, tex_dir)
            active = [m for m in manifests if m.is_active]
            print(f"[FModel] Phase 1b: {len(active)}/{len(manifests)} slots matched to textures")

    if not active:
        return

    # Phase 2
    profile = _find_game_profile(mat_dir)
    if profile:
        print(f"[FModel] Phase 2: GameProfile '{profile.game_id}' ({len(profile.param_mapping)} params)")
    else:
        print("[FModel] Phase 2: 无 GameProfile, 使用内置映射规则")
    content_dir = builder.content_dir if hasattr(builder, 'content_dir') else ""
    resolver = ChannelResolver(tex_dir, profile, content_dir=content_dir)
    assignments = resolver.resolve(manifests)

    for mat_name, ch_list in assignments.items():
        tex_files = [os.path.basename(a.texture_path) for a in ch_list if a.texture_path]
        channel_counts = {}
        for a in ch_list:
            ch = a.channel
            channel_counts[ch] = channel_counts.get(ch, 0) + 1
        ch_summary = ", ".join(f"{ch}x{c}" for ch, c in sorted(channel_counts.items()))
        print(f"[FModel]   {mat_name}: {len(tex_files)} textures [{ch_summary}]")

    # Phase 3
    total_matched = 0
    total_tex = 0
    mat_map = {}
    mi_to_slot = {}
    for m in manifests:
        if m.is_active:
            mat_map[m.slot_name] = assignments.get(m.material_name, [])
            mi_to_slot[m.material_name] = m.slot_name

    ng_name = _get_default_node_group_name()
    ng = _ensure_node_group_imported(ng_name)
    if not ng:
        print("[FModel] Phase 3: 节点组模板未找到，跳过材质构建")
        return

    interface_map = _load_interface_map()
    processed_materials = set()
    for obj in meshes:
        for slot in obj.material_slots:
            if not slot.material:
                continue
            mat = slot.material
            if mat.name in processed_materials:
                continue
            actual_slot = mi_to_slot.get(slot.name, slot.name)
            ch_list = mat_map.get(actual_slot, [])
            if not ch_list:
                continue

            resolved_paths = {}
            channel_info = {}
            for a in ch_list:
                if a.channel not in channel_info or a.score > channel_info[a.channel].score:
                    channel_info[a.channel] = a
                if a.texture_path and a.channel not in resolved_paths:
                    resolved_paths[a.channel] = a.texture_path
            total_tex += len(resolved_paths)

            try:
                from .node_builder import build_material_from_nodegroup, post_process_material
                build_material_from_nodegroup(mat, ng, interface_map, resolved_paths,
                                               channel_info, ensure_ng_func=_ensure_node_group_imported)
                post_process_material(mat, ch_list, resolved_paths)
                processed_materials.add(mat.name)
                total_matched += 1
            except Exception as e:
                print(f"[FModel] 构建材质 '{mat.name}' 失败: {e}")

    print(f"[FModel] Phase 3: {total_matched} materials built, {total_tex} textures mapped")


def _find_game_profile(mat_dir: str) -> Optional[object]:
    profile_dir = os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
        "Shaders", "GameProfiles",
    )
    if os.path.isdir(profile_dir):
        for entry in sorted(os.listdir(profile_dir)):
            if entry.endswith(".json"):
                p = GameProfile.load(os.path.join(profile_dir, entry))
                if p:
                    return p
    return None


def _get_default_node_group_name() -> str:
    try:
        cfg = _load_shaders_json()
        defaults = cfg.get("defaults", {})
        if defaults:
            return next(iter(defaults.keys()))
    except Exception:
        pass
    return "FModel_PBR_Standard"


def _load_shaders_json() -> dict:
    shaders_json = os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
        "Shaders", "shaders.json",
    )
    with open(shaders_json, 'r', encoding='utf-8') as f:
        return json.load(f)


def _ensure_node_group_imported(ng_name: str):
    if not ng_name:
        return None
    ng = bpy.data.node_groups.get(ng_name)
    if ng:
        ng.use_fake_user = True
        return ng
    shaders_blend = os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
        "Shaders", "shaders.blend",
    )
    if os.path.exists(shaders_blend):
        with bpy.data.libraries.load(shaders_blend, link=False) as (data_from, data_to):
            if ng_name in data_from.node_groups:
                data_to.node_groups = [ng_name]
        ng = bpy.data.node_groups.get(ng_name)
        if ng:
            ng.use_fake_user = True
            return ng
    return None


def _load_interface_map() -> dict:
    try:
        cfg = _load_shaders_json()
        defaults = cfg.get("defaults", {})
        if not defaults:
            return {}
        first = next(iter(defaults.values()))
        interfaces = first.get("interfaces", {})
        return {sn: ch for sn, ch in interfaces.items() if ch is not None}
    except Exception:
        return {}
