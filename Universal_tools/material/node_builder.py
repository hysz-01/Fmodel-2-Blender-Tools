# FModel_Tools/Universal_tools/material/node_builder.py
# Phase 3: Blender node graph construction from resolved channels

import bpy
import os

from .channel_resolver import _BUILTIN_COLORSPACE


def _orm_channel_output(orm_node, channel: str):
    """Map a channel name to the matching output socket of an ORM decode node."""
    if not orm_node or not orm_node.outputs:
        return None
    candidates = {
        "ao": ("r(ao)", "ao", "r"),
        "roughness": ("g(rough)", "roughness", "rough", "g"),
        "metallic": ("b(metal)", "metallic", "metal", "b"),
    }
    patterns = candidates.get(channel, (channel,))
    for pat in patterns:
        for out_socket in orm_node.outputs:
            if pat in out_socket.name.lower():
                return out_socket
    return None


def build_material_from_nodegroup(mat, ng, interface_map, resolved_paths,
                                   channel_info=None, ensure_ng_func=None):
    """使用节点组模板构建材质，按 interface_map 连接贴图。
    ensure_ng_func: called to import tool node groups from shaders.blend."""
    if channel_info is None:
        channel_info = {}
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    links = mat.node_tree.links
    nodes.clear()

    output = nodes.new("ShaderNodeOutputMaterial")
    output.location = (400, 0)

    grp = nodes.new("ShaderNodeGroup")
    grp.node_tree = ng
    grp.location = (100, 0)
    if "Shader" in grp.outputs:
        links.new(grp.outputs["Shader"], output.inputs["Surface"])

    y = 200
    base_color_tex = None
    for channel, tex_path in resolved_paths.items():
        target_socket = None
        for socket_name, ch in interface_map.items():
            if ch == channel:
                target_socket = socket_name
                break
        if not target_socket:
            continue

        ch_assignment = channel_info.get(channel)

        # Engine texture → RGB node
        if tex_path.startswith("__engine__:"):
            engine_spec = tex_path.split(":", 1)[1]
            is_normal = engine_spec.endswith("__normal")
            vals = engine_spec.replace("__normal", "").split(",")
            try:
                rgba = tuple(float(v) for v in vals[:4])
                rgba = rgba + (1.0,) * (4 - len(rgba))
            except ValueError:
                continue

            rgb_node = nodes.new("ShaderNodeRGB")
            rgb_node.location = (-300, y)
            rgb_node.outputs[0].default_value = rgba

            try:
                grp_input = grp.inputs[target_socket]
            except (KeyError, TypeError):
                y -= 260
                continue
            if is_normal and getattr(grp_input, "type", "") == "VECTOR":
                nrm = nodes.new("ShaderNodeNormalMap")
                nrm.location = (-80, y)
                links.new(rgb_node.outputs[0], nrm.inputs["Color"])
                links.new(nrm.outputs["Normal"], grp_input)
            else:
                links.new(rgb_node.outputs[0], grp_input)
            y -= 260
            continue

        # Real texture → TexImage node
        try:
            img = bpy.data.images.load(tex_path, check_existing=True)
        except Exception:
            continue

        tex = nodes.new("ShaderNodeTexImage")
        tex.image = img
        tex.location = (-300, y)
        if channel == "base_color":
            base_color_tex = tex

        cs = ch_assignment.colorspace if ch_assignment else _BUILTIN_COLORSPACE.get(channel, "sRGB")
        try:
            img.colorspace_settings.name = cs
        except Exception:
            pass

        # ORM decode
        tool_groups = ch_assignment.tool_groups if ch_assignment else []
        orm_node = None
        for tg_name in tool_groups:
            if tg_name.lower() in ("decodeorm", "decodearm", "decodemrao"):
                orm_ng = bpy.data.node_groups.get(tg_name)
                if not orm_ng and ensure_ng_func:
                    orm_ng = ensure_ng_func(tg_name)
                if orm_ng:
                    orm_node = nodes.new("ShaderNodeGroup")
                    orm_node.node_tree = orm_ng
                    orm_node.location = (tex.location.x + 220, y)
                    y -= 80
                    orm_input = None
                    for inp_name in orm_node.inputs.keys():
                        if "texture" in inp_name.lower() or "input" in inp_name.lower():
                            orm_input = orm_node.inputs[inp_name]
                            break
                    if orm_input:
                        links.new(tex.outputs["Color"], orm_input)

        # Connect to group input
        try:
            grp_input = grp.inputs[target_socket]
            is_nm = ch_assignment.is_normal_map if ch_assignment else (channel == "normal")
            if is_nm and getattr(grp_input, "type", "") == "VECTOR":
                nrm = nodes.new("ShaderNodeNormalMap")
                nrm.location = (tex.location.x + 220, y)
                links.new(tex.outputs["Color"], nrm.inputs["Color"])
                links.new(nrm.outputs["Normal"], grp_input)
            elif orm_node:
                out_socket = _orm_channel_output(orm_node, channel)
                if out_socket:
                    links.new(out_socket, grp_input)
                else:
                    links.new(tex.outputs["Color"], grp_input)
            else:
                links.new(tex.outputs["Color"], grp_input)
        except (KeyError, TypeError):
            pass

        y -= 260

    # Apply scalar fallback values
    for channel, target_socket in ((ch, sn) for sn, ch in interface_map.items()):
        if channel in resolved_paths:
            continue
        ch_assignment = channel_info.get(channel)
        if ch_assignment and ch_assignment.fallback_value != 0.0:
            try:
                grp.inputs[target_socket].default_value = ch_assignment.fallback_value
            except (KeyError, TypeError, AttributeError):
                pass

    # Alpha fallback from Base Color
    if "alpha" not in resolved_paths and base_color_tex:
        for socket_name, ch in interface_map.items():
            if ch == "alpha":
                try:
                    links.new(base_color_tex.outputs["Alpha"], grp.inputs[socket_name])
                except (KeyError, TypeError):
                    pass
                break


def _trace_tool_chain(node, anchor, mat_links):
    """Trace forward from node to anchor, collecting intermediate tool nodes.
    Prefer the link path that leads toward the group node."""
    chain = []
    seen = {node}
    current = node
    while current and current != anchor:
        # Collect candidate next nodes, prefer one closer to anchor or non-texture
        candidates = []
        for out_sock in current.outputs:
            if hasattr(out_sock, 'links') and out_sock.links:
                for link in out_sock.links:
                    candidates.append(link.to_node)
        nxt = None
        # Prefer non-TEX_IMAGE, non-REROUTE target
        for c in candidates:
            if c.type not in ('TEX_IMAGE', 'REROUTE'):
                nxt = c
                break
        if nxt is None and candidates:
            nxt = candidates[0]
        if nxt in seen or nxt is None:
            break
        seen.add(nxt)
        if nxt != anchor and nxt.type != 'REROUTE':
            chain.append(nxt)
        current = nxt
    return chain


def post_process_material(mat, ch_list, resolved_paths):
    """Layout: Group ← [Layer N .. Layer 1] ← Textures, Others far left."""
    from .channel_resolver import _CHANNEL_LABELS

    nodes = mat.node_tree.nodes
    links = mat.node_tree.links

    _TOOL_TYPES = {'NORMAL_MAP', 'INVERT', 'MIX', 'MATH', 'VECT_MATH', 'RGB', 'VALTORGB',
                   'SEPARATE_COLOR', 'SEPARATE_RGB', 'COMBINE_COLOR', 'COMBINE_RGB',
                   'MIX_RGB', 'BSDF_PRINCIPLED', 'EMISSION', 'BUMP'}

    # Import any textures from resolver that weren't already created by Phase 1
    existing_images = {node.image.name for node in nodes if node.type == 'TEX_IMAGE' and node.image}
    for a in ch_list:
        if not a.texture_path or a.texture_path.startswith("__engine__"):
            continue
        img_name = os.path.basename(a.texture_path)
        if img_name in existing_images:
            continue
        try:
            img = bpy.data.images.load(a.texture_path, check_existing=True)
            img.colorspace_settings.name = a.colorspace if a.colorspace else "sRGB"
        except Exception:
            continue
        tex = nodes.new("ShaderNodeTexImage")
        tex.image = img
        tex.location = (-300, -400)

    # Find anchor (group or BSDF)
    anchor = None
    for node in nodes:
        if node.type in ('GROUP', 'BSDF_PRINCIPLED'):
            anchor = node
            break
    if not anchor:
        return

    # ── Classify nodes by tracing tool chains ──
    layer_map = {}       # node -> hop distance from texture (1=closest to tex)
    orphans = []
    for node in nodes:
        if node.type != 'TEX_IMAGE' or not node.image:
            continue
        has_link = any(hasattr(s, 'links') and s.links for s in node.outputs)
        if not has_link:
            orphans.append(node)
            continue
        chain = _trace_tool_chain(node, anchor, links)
        for hop, tn in enumerate(chain, start=1):
            if tn not in layer_map or layer_map[tn] > hop:
                layer_map[tn] = hop

    max_layers = max(layer_map.values()) if layer_map else 0

    # Rebuild: connected textures labelled by channel
    connected_tex = []
    for node in nodes:
        if node.type != 'TEX_IMAGE' or not node.image:
            continue
        has_link = any(hasattr(s, 'links') and s.links for s in node.outputs)
        if not has_link:
            continue
        label = "Other"
        for a in ch_list:
            if a.texture_path and os.path.basename(a.texture_path) == node.image.name:
                label = _CHANNEL_LABELS.get(a.channel, a.channel)
                break
        connected_tex.append((node, label))

    # Gather tool nodes per layer
    layers = {}  # {hop: [node]}
    for tn, hop in layer_map.items():
        layers.setdefault(hop, []).append(tn)

    COL_GAP = 380
    group_x = anchor.location.x
    group_y = anchor.location.y + 200

    # ── Tool layers: right to left, Layer N .. Layer 1 ──
    for hop in range(max_layers, 0, -1):
        nds = layers.get(hop, [])
        if not nds:
            continue
        col_idx = max_layers - hop + 1  # 1=closest to group
        lx = group_x - COL_GAP * col_idx
        frame = nodes.new("NodeFrame")
        frame.label = f"Layer {hop}"
        frame.use_custom_color = True
        frame.color = (0.22, 0.12, 0.22)
        frame.shrink = False
        frame.location = (lx - 30, group_y - 140 * max(0, len(nds) - 1))
        for i, nd in enumerate(nds):
            nd.location = (lx, group_y - 140 * i)
            nd.parent = frame

    # ── Connected textures: one column left of tool layers ──
    tex_x = group_x - COL_GAP * (max_layers + 1)
    if connected_tex:
        frame = nodes.new("NodeFrame")
        frame.label = "Auto Links (Mapped)"
        frame.use_custom_color = True
        frame.color = (0.15, 0.22, 0.15)
        frame.shrink = False
        frame.location = (tex_x - 30, group_y - 280 * max(0, len(connected_tex) - 1))
        for i, (nd, label) in enumerate(connected_tex):
            nd.location = (tex_x, group_y - 280 * i)
            nd.label = label
            nd.parent = frame

    # ── Others frame: further left ──
    if orphans:
        other_x = tex_x - COL_GAP
        frame = nodes.new("NodeFrame")
        frame.label = "Others (Unmapped)"
        frame.use_custom_color = True
        frame.color = (0.15, 0.15, 0.15)
        frame.shrink = False
        frame.location = (other_x - 30, group_y - 280 * max(0, len(orphans) - 1))
        for i, nd in enumerate(orphans):
            nd.location = (other_x, group_y - 280 * i)
            nd.parent = frame
