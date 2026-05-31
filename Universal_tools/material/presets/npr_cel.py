# FModel_Tools/Universal_tools/material/presets/npr_cel.py
# NPR Cel Shading 预设 — 赛璐璐风格（Shader to RGB + Color Ramp）

import bpy

from .base import MaterialPreset
from .processors import TextureProcessor, ProcessorOutput
from .processors import _load_image_safe, _set_colorspace, _tex_node


class NPRCelPreset(MaterialPreset):
    """NPR Cel Shading 预设 — 日式赛璐璐风格

    使用 Shader to RGB + Color Ramp 实现非物理渲染：
    - 基于光照的硬边缘着色（3段渐变：阴影/中间/高光）
    - 支持法线贴图
    - 支持渐变遮罩调整阴影色调
    - 支持轮廓线贴图（可选）
    """

    PRESET_ID = "npr_cel"
    PRESET_LABEL = "Cel Shading"
    PRESET_DESC = "赛璐璐风格：Shader-to-RGB + ColorRamp三阶渐变，支持法线和阴影色调"
    PRESET_CATEGORY = "NPR"

    # ── 可配置参数 ──
    shadow_color: tuple = (0.15, 0.15, 0.25, 1.0)   # RGBA 阴影色
    mid_color: tuple = (0.6, 0.6, 0.7, 1.0)          # 中间调
    highlight_color: tuple = (1.0, 1.0, 1.0, 1.0)    # 高光色
    ramp_interpolation: str = "CONSTANT"              # ColorRamp 插值模式
    use_outline: bool = False                         # 是否使用轮廓线

    texture_processors = {
        "base_color": TextureProcessor(
            name="base_color",
            type="direct",
            match=["_d", "_diffuse", "_albedo", "_bc", "_basecolor"],
            colorspace="sRGB",
            required=True,
            outputs={"default": ProcessorOutput(socket="Base Color")},
        ),
        "normal": TextureProcessor(
            name="normal",
            type="normal_map",
            match=["_n", "_normal", "_nm"],
            colorspace="Non-Color",
            outputs={"default": ProcessorOutput(socket="Normal", via="NormalMap")},
        ),
        "ramp_mask": TextureProcessor(
            name="ramp_mask",
            type="direct",
            match=["_ramp", "_toon", "_mask", "_shadow"],
            colorspace="Non-Color",
            outputs={"default": ProcessorOutput(socket=None, note="渐变遮罩，控制阴影区域")},
        ),
        "outline": TextureProcessor(
            name="outline",
            type="direct",
            match=["_outline", "_edge", "_contour", "_line"],
            colorspace="Non-Color",
            outputs={"default": ProcessorOutput(socket=None, note="轮廓线贴图（可选）")},
        ),
    }

    # ============================================================
    # 节点图构建
    # ============================================================

    def build_material_graph(self, material, resolved_textures):
        """构建 Cel Shading 节点图"""
        props = getattr(bpy.context.scene, "fmodel_material", None)
        if props:
            self.shadow_color = tuple(props.npr_shadow_color)
            self.highlight_color = tuple(getattr(props, "npr_highlight_color", (1.0, 1.0, 1.0, 1.0)))
            self.ramp_interpolation = getattr(props, "npr_ramp_interpolation", "CONSTANT")
            self.use_outline = getattr(props, "npr_use_outline", False)
        material.use_nodes = True
        nodes = material.node_tree.nodes
        links = material.node_tree.links
        nodes.clear()

        # ── 输出 ──
        output = nodes.new("ShaderNodeOutputMaterial")
        output.location = (600, 0)

        # ── Diffuse BSDF（替代 PBR 的 Principled BSDF）──
        diffuse = nodes.new("ShaderNodeBsdfDiffuse")
        diffuse.location = (300, 0)
        links.new(diffuse.outputs["BSDF"], output.inputs["Surface"])

        y = 0

        # ── Base Color → ShaderToRGB → ColorRamp → Diffuse.Color ──
        if "base_color" in resolved_textures:
            img = _load_image_safe(resolved_textures["base_color"])
            if img:
                _set_colorspace(img, "sRGB")
                tex = _tex_node(nodes, img, (-600, y))

                shader_to_rgb = nodes.new("ShaderNodeShaderToRGB")
                shader_to_rgb.location = (-350, y)

                ramp = nodes.new("ShaderNodeValToRGB")
                ramp.location = (-100, y)
                ramp.color_ramp.interpolation = self.ramp_interpolation
                self._setup_ramp(ramp)

                # 连接: Tex → ShaderToRGB → ColorRamp → Diffuse
                links.new(tex.outputs["Color"], shader_to_rgb.inputs["Color"])
                links.new(shader_to_rgb.outputs["Color"], ramp.inputs["Fac"])
                links.new(ramp.outputs["Color"], diffuse.inputs["Color"])
                y -= 240

        # ── Ramp Mask（阴影/高光遮罩）──
        if "ramp_mask" in resolved_textures:
            img = _load_image_safe(resolved_textures["ramp_mask"])
            if img:
                _set_colorspace(img, "Non-Color")
                mask_tex = _tex_node(nodes, img, (-600, y))
                # 简单混合：用遮罩的亮度控制阴影色调
                # 将遮罩乘以阴影色，加到 Diffuse 颜色上
                try:
                    mix = nodes.new("ShaderNodeMix")
                    mix.data_type = "RGBA"
                    mix.blend_type = "MULTIPLY"
                    mix.inputs["B"].default_value = self.shadow_color
                    links.new(mask_tex.outputs["Color"], mix.inputs["Factor"])
                except RuntimeError:
                    mix = nodes.new("ShaderNodeMixRGB")
                    mix.blend_type = "MULTIPLY"
                    mix.inputs[1].default_value = self.shadow_color
                    links.new(mask_tex.outputs["Color"], mix.inputs["Fac"])
                # 不直接连接——在完整实现中通过 Mix 混合到主颜色管线
                y -= 240

        # ── Normal ──
        if "normal" in resolved_textures:
            img = _load_image_safe(resolved_textures["normal"])
            if img:
                _set_colorspace(img, "Non-Color")
                n_tex = _tex_node(nodes, img, (-600, y))
                nrm = nodes.new("ShaderNodeNormalMap")
                nrm.location = (-350, y)
                links.new(n_tex.outputs["Color"], nrm.inputs["Color"])
                links.new(nrm.outputs["Normal"], diffuse.inputs["Normal"])
                y -= 240

        # ── Outline（轮廓线，可选）──
        if "outline" in resolved_textures and self.use_outline:
            img = _load_image_safe(resolved_textures["outline"])
            if img:
                _set_colorspace(img, "Non-Color")
                o_tex = _tex_node(nodes, img, (-600, y))
                # 简单地用 Multiply 混合轮廓线
                # 插入到 Diffuse → Output 之间
                for link in list(links):
                    if link.to_socket == output.inputs["Surface"]:
                        links.remove(link)
                        try:
                            mix = nodes.new("ShaderNodeMix")
                            mix.data_type = "RGBA"
                            mix.location = (50, y)
                            mix.blend_type = "MULTIPLY"
                            mix.inputs["Factor"].default_value = 1.0
                            links.new(diffuse.outputs["BSDF"], mix.inputs["A"])
                            links.new(o_tex.outputs["Color"], mix.inputs["B"])
                            links.new(mix.outputs["Result"], output.inputs["Surface"])
                        except RuntimeError:
                            mix = nodes.new("ShaderNodeMixRGB")
                            mix.location = (50, y)
                            mix.blend_type = "MULTIPLY"
                            mix.inputs[0].default_value = 1.0
                            links.new(diffuse.outputs["BSDF"], mix.inputs[1])
                            links.new(o_tex.outputs["Color"], mix.inputs[2])
                            links.new(mix.outputs["Image"], output.inputs["Surface"])
                        break

    def _setup_ramp(self, ramp_node):
        """设置 ColorRamp 的三阶渐变"""
        elements = ramp_node.color_ramp.elements
        # 清除默认元素，创建3个
        while len(elements) > 2:
            elements.remove(elements[1])
        # Stop 0: 阴影
        elements[0].position = 0.0
        elements[0].color = self.shadow_color
        # Stop 1: 中间 (新建)
        mid = elements.new(0.5)
        mid.color = self.mid_color
        # Stop 2: 高光
        elements[1].position = 1.0
        elements[1].color = self.highlight_color

    # ============================================================
    # UI
    # ============================================================

    def draw_options(self, layout: bpy.types.UILayout, props) -> None:
        """绘制 Cel Shading 专属选项"""
        col = layout.column(align=True)
        col.label(text="Ramp 颜色", icon='COLOR')
        row = col.row(align=True)
        row.prop(props, "npr_shadow_color", text="阴影")
        row.prop(props, "npr_highlight_color", text="高光")

        col.prop(props, "npr_ramp_interpolation", text="插值")

        row_outline = col.row(align=True)
        row_outline.prop(props, "npr_use_outline", text="轮廓线")
