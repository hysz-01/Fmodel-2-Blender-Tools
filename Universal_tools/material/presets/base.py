# FModel_Tools/Universal_tools/material/presets/base.py
# MaterialPreset 抽象基类 — 定义材质预设的统一接口

from typing import Optional, ClassVar

import bpy

from .processors import (
    TextureProcessor,
    build_processor_graph,
    _load_image_safe,
    _set_colorspace,
)


class MaterialPreset:
    """材质预设抽象基类

    每个预设子类必须定义 PRESET_ID, PRESET_LABEL, PRESET_DESC, PRESET_CATEGORY
    和 texture_processors 字典。build_material_graph() 有默认实现，可覆盖。

    使用示例:
        class MyPBRPreset(MaterialPreset):
            PRESET_ID = "my_pbr"
            PRESET_LABEL = "My PBR"
            PRESET_DESC = "Custom PBR preset"
            PRESET_CATEGORY = "PBR"
            texture_processors = { ... }

        preset = MyPBRPreset()
        preset.build_material_graph(material, {"base_color": "/path/to/tex.png"})
    """

    # ============================================================
    # 元数据（子类必须覆盖）
    # ============================================================
    PRESET_ID: ClassVar[str] = ""
    PRESET_LABEL: ClassVar[str] = ""
    PRESET_DESC: ClassVar[str] = ""
    PRESET_CATEGORY: ClassVar[str] = ""  # "PBR" | "NPR" | "Hybrid"

    # ============================================================
    # 核心：贴图处理器定义（子类必须覆盖）
    # ============================================================
    texture_processors: dict[str, TextureProcessor] = {}
    # key = 处理器名（如 "base_color", "normal", "orm"）
    # value = TextureProcessor 实例

    # ============================================================
    # 可选：额外配置
    # ============================================================
    merge_strategy: dict = {}        # 贴图合并策略
    node_group_source: Optional[str] = None  # 外部 .blend 节点组路径
    ai_metadata: dict = {}           # AI 分析元数据

    # ============================================================
    # 派生属性
    # ============================================================

    @property
    def match_patterns(self) -> dict[str, list[str]]:
        """所有处理器的 match 模式汇总。

        Returns:
            {processor_name: [match_suffixes]} 如 {"base_color": ["_d", "_diffuse"], ...}
        """
        return {
            name: proc.match
            for name, proc in self.texture_processors.items()
            if proc.match and proc.type != "ignored"
        }

    @property
    def required_processors(self) -> set[str]:
        """标记为 required 的处理器名集合"""
        return {
            name
            for name, proc in self.texture_processors.items()
            if proc.required
        }

    @property
    def processor_names(self) -> tuple[str, ...]:
        """所有处理器名称（排除 ignored）"""
        return tuple(
            name for name, proc in self.texture_processors.items()
            if proc.type != "ignored"
        )

    # ============================================================
    # 节点组管理
    # ============================================================

    _node_group_cache: ClassVar[dict[str, bpy.types.NodeGroup]] = {}

    def get_or_create_node_group(self) -> Optional[bpy.types.NodeGroup]:
        """获取或创建此预设的共享节点组。

        首次调用时从 node_group_source 加载或返回 None（程序化构建）。
        后续调用返回缓存引用。

        Returns:
            NodeGroup 实例，或 None（表示使用程序化构建）
        """
        cache_key = self.PRESET_ID
        if cache_key in self._node_group_cache:
            ng = self._node_group_cache[cache_key]
            # 验证缓存仍然有效
            if ng and ng.name in bpy.data.node_groups:
                return ng
            del self._node_group_cache[cache_key]

        if not self.node_group_source:
            return None

        ng = self._load_node_group_from_blend(self.node_group_source)
        if ng:
            self._node_group_cache[cache_key] = ng
        return ng

    @staticmethod
    def _load_node_group_from_blend(source: str) -> Optional[bpy.types.NodeGroup]:
        """从 .blend 文件加载节点组。

        Args:
            source: 格式 "path/to/file.blend\\NodeTree\\GroupName"

        Returns:
            NodeGroup 实例或 None
        """
        if not source or "\\" not in source:
            return None

        parts = source.rsplit("\\", 1)
        if len(parts) != 2:
            return None
        blend_path, node_tree_name = parts

        if not blend_path.endswith(".blend"):
            return None

        try:
            with bpy.data.libraries.load(blend_path, link=False) as (data_from, data_to):
                data_to.node_groups = [
                    n for n in data_from.node_groups if n == node_tree_name
                ]
            if data_to.node_groups:
                return data_to.node_groups[0]
        except Exception as e:
            print(f"[FModel Preset] 加载节点组失败: {source} — {e}")
        return None

    @classmethod
    def invalidate_node_group_cache(cls, preset_id: Optional[str] = None):
        """清除节点组缓存。

        Args:
            preset_id: 指定预设 ID 或 None（清除全部）
        """
        if preset_id:
            cls._node_group_cache.pop(preset_id, None)
        else:
            cls._node_group_cache.clear()

    # ============================================================
    # 材质图构建
    # ============================================================

    def build_material_graph(
        self,
        material: bpy.types.Material,
        resolved_textures: dict[str, str],
    ) -> None:
        """构建材质的节点图。

        默认实现：遍历 resolved_textures，为每个找到对应 TextureProcessor 的贴图
        调用 build_processor_graph() 构建节点子图。

        子类可覆盖以实现特殊逻辑（如 NPR 的 ShaderToRGB 管线）。

        Args:
            material: 目标 Blender 材质
            resolved_textures: {processor_name: texture_file_path}
        """
        material.use_nodes = True
        nodes = material.node_tree.nodes
        links = material.node_tree.links
        nodes.clear()

        # 创建输出节点
        output = nodes.new("ShaderNodeOutputMaterial")
        output.location = (500, 0)

        # 获取或创建核心 BSDF / 节点组
        ng = self.get_or_create_node_group()
        if ng:
            bsdf = nodes.new("ShaderNodeGroup")
            bsdf.node_tree = ng
            bsdf.location = (200, 0)
        else:
            bsdf = nodes.new("ShaderNodeBsdfPrincipled")
            bsdf.location = (200, 0)

        try:
            links.new(bsdf.outputs["BSDF"], output.inputs["Surface"])
        except (KeyError, TypeError):
            # 自定义节点组可能有不同的输出名
            for socket in bsdf.outputs:
                if socket.type == "SHADER":
                    try:
                        links.new(socket, output.inputs["Surface"])
                    except (KeyError, TypeError):
                        pass
                    break

        # 按优先级排序处理器（高优先级先处理，如 ORM > 独立通道）
        sorted_processors = sorted(
            self.texture_processors.items(),
            key=lambda item: item[1].priority,
            reverse=True,
        )

        # 跟踪已处理的处理器名（ORM 处理后跳过独立通道）
        processed_names: set[str] = set()

        y = 260
        for proc_name, processor in sorted_processors:
            if proc_name in processed_names:
                continue
            if processor.type == "ignored":
                continue

            if proc_name in resolved_textures:
                tex_path = resolved_textures[proc_name]
                y = build_processor_graph(
                    material, processor, tex_path, bsdf, nodes, links, y,
                )
                processed_names.add(proc_name)
            elif processor.fallback_value is not None:
                # 应用 fallback 值
                self._apply_fallback(bsdf, processor)

    def _apply_fallback(self, bsdf: bpy.types.Node, processor: TextureProcessor) -> None:
        """将 fallback_value 应用到 BSDF 的对应输入"""
        if processor.fallback_value is None:
            return
        for out_name, out in processor.outputs.items():
            if out.socket:
                try:
                    bsdf.inputs[out.socket].default_value = processor.fallback_value
                except (KeyError, TypeError, AttributeError):
                    pass

    # ============================================================
    # UI（可选覆盖）
    # ============================================================

    def draw_options(self, layout: bpy.types.UILayout, props) -> None:
        """绘制预设专属 UI 选项。子类可覆盖。

        Args:
            layout: Blender UILayout
            props: 当前 MaterialProperties 属性组
        """
        pass

    # ============================================================
    # 序列化
    # ============================================================

    def to_dict(self) -> dict:
        """导出为字典（用于 JSON 序列化）"""
        processors_dict = {}
        for name, proc in self.texture_processors.items():
            proc_dict = {
                "type": proc.type,
                "match": proc.match,
                "colorspace": proc.colorspace,
                "required": proc.required,
                "priority": proc.priority,
            }
            if proc.fallback_value is not None:
                proc_dict["fallback_value"] = proc.fallback_value
            proc_dict["outputs"] = {}
            for out_name, out in proc.outputs.items():
                proc_dict["outputs"][out_name] = {
                    "socket": out.socket,
                    "via": out.via,
                    "label": out.label,
                    "note": out.note,
                }
            processors_dict[name] = proc_dict

        result = {
            "preset_id": self.PRESET_ID,
            "preset_label": self.PRESET_LABEL,
            "preset_desc": self.PRESET_DESC,
            "preset_category": self.PRESET_CATEGORY,
            "texture_processors": processors_dict,
        }
        if self.merge_strategy:
            result["merge_strategy"] = self.merge_strategy
        if self.node_group_source:
            result["node_group_source"] = self.node_group_source
        if self.ai_metadata:
            result["ai_metadata"] = self.ai_metadata
        return result
