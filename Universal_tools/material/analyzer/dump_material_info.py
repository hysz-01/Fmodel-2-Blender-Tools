# FModel_Tools/Universal_tools/material/analyzer/dump_material_info.py
# 辅助工具：导出材质结构摘要供 LLM 阅读
#
# 用法（在 Blender Python 控制台中运行）:
#   import sys
#   sys.path.append(r"路径到addons目录")
#   from Universal_tools.material.analyzer.dump_material_info import dump
#   dump()  # 导出当前场景所有材质信息
#
# 或作为独立脚本:
#   blender --background --python dump_material_info.py

import json
import os
from collections import Counter


def dump(tex_dir: str = "", output_path: str = "") -> str:
    """导出当前场景的材质和贴图结构摘要。

    返回可用于发送给 LLM 的文本摘要。

    Args:
        tex_dir: 贴图目录（可选，用于统计文件后缀）
        output_path: 输出 JSON 路径（可选）

    Returns:
        可读的文本摘要字符串
    """
    import bpy

    lines = []
    lines.append("=" * 60)
    lines.append("FModel 材质结构摘要")
    lines.append("=" * 60)

    # ── 收集材质 ──
    materials = set()
    for obj in bpy.context.scene.objects:
        if obj.type != "MESH":
            continue
        for slot in obj.material_slots:
            if slot.material:
                materials.add(slot.material)

    lines.append(f"\n## 场景材质数量: {len(materials)}")
    lines.append("")

    for mat in sorted(materials, key=lambda m: m.name):
        lines.append(f"### 材质: {mat.name}")
        if mat.use_nodes:
            node_count = len(mat.node_tree.nodes)
            lines.append(f"  节点图: 已启用 ({node_count} 个节点)")
            # 列出贴图节点
            for node in mat.node_tree.nodes:
                if node.type == "TEX_IMAGE" and node.image:
                    lines.append(f"  - 贴图: {node.image.name} -> {node.image.filepath}")
        else:
            lines.append(f"  节点图: 未启用")
        lines.append("")

    # ── 统计贴图目录后缀 ──
    if tex_dir and os.path.isdir(tex_dir):
        suffixes = Counter()
        for f in os.listdir(tex_dir):
            name = os.path.splitext(f)[0].lower()
            for ext in (".png", ".jpg", ".tga", ".exr"):
                if f.lower().endswith(ext):
                    # 提取后缀（最后一个下划线之后的部分）
                    parts = name.rsplit("_", 1)
                    if len(parts) == 2:
                        suffixes[f"_{parts[1]}"] += 1
                    break

        lines.append(f"\n## 贴图目录统计: {tex_dir}")
        lines.append(f"总贴图数: {sum(suffixes.values())}")
        lines.append("### 后缀分布:")
        for suffix, count in suffixes.most_common(30):
            lines.append(f"  {suffix}: {count}")

    text = "\n".join(lines)

    # ── 可选 JSON 输出 ──
    if output_path:
        data = {
            "material_count": len(materials),
            "materials": [
                {
                    "name": mat.name,
                    "has_nodes": mat.use_nodes,
                    "textures": [
                        {"name": node.image.name, "path": node.image.filepath}
                        for node in mat.node_tree.nodes
                        if mat.use_nodes and node.type == "TEX_IMAGE" and node.image
                    ],
                }
                for mat in sorted(materials, key=lambda m: m.name)
            ],
        }
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    return text


def dump_from_file(tex_dir: str, mat_json_path: str = "", output_path: str = "") -> str:
    """从外部文件导出摘要（不依赖 Blender 场景）。

    Args:
        tex_dir: 贴图目录
        mat_json_path: FModel 导出的材质 JSON 目录或文件路径
        output_path: 输出路径

    Returns:
        文本摘要
    """
    lines = []
    lines.append("=" * 60)
    lines.append("FModel 材质结构摘要（基于文件分析）")
    lines.append("=" * 60)

    # ── 贴图目录分析 ──
    if tex_dir and os.path.isdir(tex_dir):
        suffixes = Counter()
        all_files = []
        for root, dirs, files in os.walk(tex_dir):
            dirs[:] = [d for d in dirs if not d.startswith(".")]
            for f in files:
                low = f.lower()
                if low.endswith((".png", ".jpg", ".jpeg", ".tga", ".tiff", ".exr", ".bmp")):
                    all_files.append(f)
                    stem = os.path.splitext(low)[0]
                    parts = stem.rsplit("_", 1)
                    if len(parts) == 2 and len(parts[1]) <= 20:
                        suffixes[f"_{parts[1]}"] += 1

        lines.append(f"\n## 贴图目录: {tex_dir}")
        lines.append(f"总贴图数: {len(all_files)}")
        lines.append("\n### 后缀分布（前 30）:")
        for suffix, count in suffixes.most_common(30):
            lines.append(f"  {suffix}: {count}")

        lines.append("\n### 完整文件列表（前 50）:")
        for f in sorted(all_files)[:50]:
            lines.append(f"  {f}")
        if len(all_files) > 50:
            lines.append(f"  ... 还有 {len(all_files) - 50} 个文件")

    # ── 材质 JSON 分析 ──
    if mat_json_path and os.path.exists(mat_json_path):
        lines.append(f"\n## 材质定义: {mat_json_path}")
        if os.path.isfile(mat_json_path):
            try:
                with open(mat_json_path, "r", encoding="utf-8") as f:
                    lines.append(f.read()[:5000])
            except Exception:
                lines.append("  (无法读取)")
        elif os.path.isdir(mat_json_path):
            json_files = [f for f in os.listdir(mat_json_path) if f.endswith(".json")]
            lines.append(f"  JSON 文件数: {len(json_files)}")
            for jf in sorted(json_files)[:10]:
                lines.append(f"  - {jf}")

    text = "\n".join(lines)
    return text


# ============================================================
# 独立运行
# ============================================================
if __name__ == "__main__":
    import sys
    tex = sys.argv[1] if len(sys.argv) > 1 else ""
    mat = sys.argv[2] if len(sys.argv) > 2 else ""
    out = sys.argv[3] if len(sys.argv) > 3 else ""
    print(dump_from_file(tex, mat, out))
