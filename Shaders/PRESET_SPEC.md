# FModel Material Preset Specification

> **目标读者**: LLM（大语言模型）和人类开发者
> **用途**: 根据游戏材质文件和贴图目录，生成合法的 FModel 材质预设方案 JSON
> **版本**: 2.0 | 更新: 2026-05-26

---

## 1. 概述

FModel Tools 是一个 Blender 插件，用于自动化 UE/FModel 导出的材质重建。

**本规范的作用**：当你（LLM）收到一个游戏的材质定义文件（JSON格式）和贴图文件列表后，按照本文档的规则生成两类配置：
1. **game-profile.json**（UE 参数→通道映射）—— 控制每种游戏的贴图参数如何映射到 PBR 通道
2. **preset.json**（贴图匹配规则）—— 文件后缀如何匹配到通道

**当前架构**（v3.0）：
```
模型 .uemodel 导入
  → Phase 1: 解析模型JSON + 材质实例JSON → MaterialManifest
  → Phase 2: GameProfile 驱动 UE参数→通道映射 + 纹理文件查找 → ChannelAssignment
  → Phase 3: 使用 shaders.json 节点组模板 + shaders.blend 构建材质节点图
```

**工作流**：
```
游戏材质文件 (.json)  +  贴图目录文件列表
        ↓
    你 (LLM) 阅读本文档
        ↓
    生成 game-profile.json (UE参数映射)
        ↓
  放在 Shaders/GameProfiles/ 下
        ↓
  导入模型时自动解析材质
```

---

## 2. JSON Schema

### 2.1 顶层结构

```json
{
  "preset_id": "string (必需，唯一标识)",
  "preset_label": "string (必需，UI显示名，中文或英文)",
  "preset_desc": "string (可选，描述)",
  "preset_category": "string (必需，PBR | NPR | Hybrid)",
  "version": "2.0",
  "texture_processors": { /* 必需，见 2.2 */ },
  "merge_strategy": { /* 可选，见 2.3 */ },
  "node_group_source": "string | null (可选，见 2.4)",
  "ai_metadata": { /* 可选，AI分析记录 */ }
}
```

### 2.2 texture_processors

`texture_processors` 是一个字典，key 是处理器名（自定义，如 `"base_color"`, `"normal"`, `"orm"`, `"ilm"`），value 是处理器定义对象。

```json
{
  "处理器名": {
    "type": "direct | normal_map | rgb_split | custom_node_group | ignored",
    "match": ["_d", "_diffuse"],      // string[] 必需，文件名后缀匹配列表
    "colorspace": "sRGB",              // string 可选，默认为 "sRGB"
    "tool_groups": [                   // object[] 可选，预处理工具节点组链
      {"name": "FlipNormalY", "source": "tools.blend", "description": "UE法线Y轴反转"}
    ],
    "required": false,                 // bool 可选，严格模式下是否必须
    "fallback_value": 0.5,            // float | null 可选，贴图缺失时的默认值
    "priority": 0,                     // int 可选，匹配优先级
    "outputs": {                       // object 必需，输出映射
      "输出名": {
        "socket": "Base Color",        // string | null，目标套接字名
        "via": "NormalMap",            // string | null，中间节点
        "label": "Roughness",          // string 可选，UI标签
        "note": "来自G通道"            // string 可选，注释
      }
    }
  }
}
```

### 2.3 merge_strategy（可选）

贴图合并策略，用于处理同一通道有多种贴图来源的情况。

```json
{
  "orm_priority": "separate_only | override",
  // "separate_only": ORM 贴图存在时，独立的 roughness/metallic/ao 仍然可用
  // "override": ORM 贴图存在时，忽略独立的 roughness/metallic/ao

  "comment": "任意说明文字"
}
```

### 2.4 node_group_source（可选）

外部 `.blend` 文件中预制的着色器节点组路径。

- `null`: 使用程序化构建（Principled BSDF 或预设内置逻辑）
- 字符串: `"路径/到/文件.blend\\NodeTree\\节点组名"`（Windows 风格路径，双反斜杠）

### 2.5 ai_metadata（可选）

AI 分析记录，用于追溯和调试。

```json
{
  "source_game": "Genshin Impact v3.x",
  "analysis_date": "2026-05-26",
  "texture_sample_count": 4521,
  "confirmed_by_user": true,
  "notes": "通过分析 ... 推断 ..."
}
```

---

## 3. 处理器类型 (type)

### 3.1 `direct` — 直接贴图连接

贴图文件 → BSDF/节点组输入套接字。最常见的类型。

```json
"base_color": {
  "type": "direct",
  "match": ["_d", "_diffuse", "_albedo", "_bc"],
  "colorspace": "sRGB",
  "outputs": {
    "default": { "socket": "Base Color" }
  }
}
```

**节点链**: `TexImage.Color → BSDF.Base Color`

### 3.2 `normal_map` — 法线贴图

贴图 → NormalMap 节点 → Normal 套接字。自动使用 Non-Color 色彩空间。

```json
"normal": {
  "type": "normal_map",
  "match": ["_n", "_normal", "_nm"],
  "colorspace": "Non-Color",
  "outputs": {
    "default": { "socket": "Normal", "via": "NormalMap" }
  }
}
```

**节点链**: `TexImage.Color → NormalMap.Color → NormalMap.Normal → BSDF.Normal`

### 3.3 `rgb_split` — RGB 通道分离

一张贴图的 R/G/B 通道分别连接到不同的套接字。常用于 ORM 打包贴图。

```json
"orm": {
  "type": "rgb_split",
  "match": ["_orm", "_arm"],
  "colorspace": "Non-Color",
  "outputs": {
    "R": { "socket": null,    "label": "AO",         "note": "Ambient Occlusion" },
    "G": { "socket": "Roughness", "label": "Roughness" },
    "B": { "socket": "Metallic",  "label": "Metallic"  }
  }
}
```

**节点链**: `TexImage.Color → SeparateRGB → R→AO / G→Roughness / B→Metallic`

**重要**: `outputs` 的 key 必须是 `"R"`, `"G"`, `"B"` 大写字母。每个通道的 `socket` 完全可配置——不同游戏的 ORM 惯例不同：
- UE 风格: R=AO, G=Roughness, B=Metallic
- Unity 风格: R=Metallic, G=AO, B=(unused)
- 自定义: R、G、B 可以映射到任意有效的 BSDF 套接字名

### 3.4 `custom_node_group` — 外部节点组

贴图连接到从 `.blend` 加载的自定义着色器节点组。需要同时设置 `node_group_source`。

```json
"ilm": {
  "type": "custom_node_group",
  "match": ["_ilm", "_lightmap"],
  "colorspace": "sRGB",
  "outputs": {
    "default": { "socket": "ILM Map", "note": "连接到CelShader的ILM输入" }
  }
}
```

### 3.5 工具节点组链 (tool_groups) — 预处理管线

工具节点组链允许在贴图和最终 socket 之间插入任意序列的**工具/预处理节点组**。这些节点组从 `.blend` 文件加载，只负责数据转换，不包含贴图匹配逻辑。

**用途**：
- UE 法线贴图 Y 通道反转 → 插入 `FlipNormalY` 工具节点组
- DXT5/BC5 编码法线解码 → 插入 `DecodeBC5` 工具节点组
- Roughness→Glossiness 转换 → 插入 `RoughToGloss` 节点组
- 任意自定义编码贴图的解码器

**声明**：在 `texture_processors` 的处理器中添加 `tool_groups` 字段：

```json
"normal": {
  "type": "normal_map",
  "match": ["_n", "_normal", "_nm"],
  "colorspace": "Non-Color",
  "tool_groups": [
    {"name": "FlipNormalY", "source": "tools.blend"},
    {"name": "DecodeBC5",  "source": null}
  ],
  "outputs": {
    "default": { "socket": "Normal", "via": "NormalMap" }
  }
}
```

**字段说明**：

| 字段 | 类型 | 说明 |
|------|------|------|
| `name` | string | 工具节点组名称（在 `.blend` 中的 NodeTree 名） |
| `source` | string\|null | 节点组来源 `.blend` 文件路径。`null` 表示使用当前场景已有的节点组 |
| `description` | string\|null | 可选说明（如 "UE 法线 Y 通道取反"），供 AI 和人类理解用途 |

**执行顺序**：

```
贴图文件
  → tool_groups[0] (Texture input → output)
  → tool_groups[1] (如果存在)
  → ...
  → via 节点（如 NormalMap, SeparateRGB）或直接
  → 目标 socket
```

**AI 询问规范**：当检测到以下情况时，AI **必须**在 Step 3（提问阶段）询问是否需要工具节点组：
- 贴图命名中出现 `_flip`、`_inverted` 等暗示需要变换的词
- 用户提到某游戏使用了非标准编码（如 BC5 法线、翻转 Y 轴）
- 材质 JSON 中出现了插件不直接支持的贴图参数名

**内置工具节点组推荐**：建议在 `Shaders/` 目录下维护一个 `tools.blend`，存放以下工具节点组。AI 生成预设时可按需引用。完整接口定义见 `Shaders/TOOL_NODES.md`。

### 3.5.1 工具节点组清单

完整接口定义见 `Shaders/TOOL_NODES.md`。

**法线处理**

| 节点组名 | 功能 | 输入 | 输出 |
|---------|------|------|------|
| `NormalMapToNormal` | 法线完整处理 | Texture Input, Strength | Normal Output |
| `FlipNormalY` | 仅Y轴取反 | Texture Input | Texture Output |
| `FlipNormalX` | 仅X轴取反 | Texture Input | Texture Output |
| `DecodeBC5` | BC5压缩法线解码 | Texture Input | Texture Output |
| `DecodeDXT5` | DXT5压缩法线解码（Unity粉红法线） | Texture Input, Alpha Input | Texture Output |
| `BumpToNormal` | 高度/凹凸→法线 | Texture Input, Strength | Normal Output |

**打包贴图提取**

| 节点组名 | 功能 | 输入 | 输出 |
|---------|------|------|------|
| `ExtractPackedChannels` | 通用RGBA拆分 | Texture Input, Alpha Input | R, G, B, A |
| `DecodeORM` | UE风格 (R=AO,G=Rough,B=Metallic) | Texture Input, Alpha Input | R(AO), G(Rough), B(Metal), A |
| `DecodeARM` | Unity HDRP风格 (R=Metallic,G=AO,B=Rough) | Texture Input, Alpha Input | R(Metal), G(AO), B(Rough), A |
| `DecodeMRAO` | MRAO风格 (R=Metallic,G=Rough,B=AO) | Texture Input, Alpha Input | R(Metal), G(Rough), B(AO), A |

**值转换**

| 节点组名 | 功能 | 输入 | 输出 |
|---------|------|------|------|
| `InvertChannel` | 单通道取反 (1-x)，覆盖粗糙/光滑互转 | Texture Input | Texture Output |
| `Remap01` | 值域重映射 | Texture Input, OldMin/Max, NewMin/Max | Texture Output |

**输入命名规范**: Texture Input / Alpha Input / Roughness Input / Metallic Input / AO Input
**输出命名规范**: Texture Output / Alpha Output / Normal Output / R / G / B / A

### 3.5.3 使用示例

在 preset JSON 中引用工具节点组：

```json
"normal": {
  "type": "normal_map",
  "match": ["_n", "_normal", "_nm"],
  "colorspace": "Non-Color",
  "tool_groups": [
    {"name": "FlipNormalY", "source": "Shaders/tools.blend", "description": "UE法线Y轴反转"}
  ],
  "outputs": {
    "default": { "socket": "Normal", "via": "NormalMap" }
  }
}
```

### 3.6 `ignored` — 明确忽略

标记某些贴图类型应被跳过（如缩略图、mipmap、调试贴图）。AI 确认后使用。

```json
"thumbnail": {
  "type": "ignored",
  "match": ["_thumb", "_preview"],
  "outputs": {}
}
```

---

## 4. 贴图后缀识别规则

### 4.1 标准后缀映射

| 贴图用途 | 常见后缀 | 处理器类型 | 色彩空间 |
|---------|---------|-----------|---------|
| 基础颜色/漫反射 | `_d`, `_diffuse`, `_albedo`, `_bc`, `_basecolor`, `_color` | `direct` | sRGB |
| 法线 | `_n`, `_normal`, `_nm`, `_norm` | `normal_map` | Non-Color |
| 粗糙度 | `_r`, `_roughness`, `_rough` | `direct` | Non-Color |
| 金属度 | `_m`, `_metallic`, `_metal` | `direct` | Non-Color |
| AO/环境光遮蔽 | `_ao`, `_occlusion`, `_ambient` | `direct` | Non-Color |
| 自发光 | `_e`, `_emissive`, `_emission`, `_glow` | `direct` | sRGB |
| 不透明度/遮罩 | `_alpha`, `_opacity`, `_mask`, `_trans` | `direct` | Non-Color |
| ORM 打包 | `_orm`, `_arm`, `_occlusionroughnessmetallic` | `rgb_split` | Non-Color |
| ILM 光照贴图 | `_ilm`, `_lightmap` | `direct` 或 `custom_node_group` | sRGB |
| 渐变/Toon | `_ramp`, `_toon`, `_lut`, `_gradient` | `direct` | Non-Color |
| 金属遮罩 | `_metal`, `_metalmask`, `_metallic` | `direct` | Non-Color |
| 轮廓线 | `_outline`, `_edge`, `_contour`, `_line` | `direct` | Non-Color |

### 4.2 匹配规则

处理器使用 `match` 字段中的后缀列表来识别贴图。匹配逻辑：
1. 取贴图文件名（不含扩展名）的小写形式
2. 逐一检查 `match` 列表中的每个后缀
3. **后缀完全匹配** `file.endswith(suffix)` → 得分最高
4. **部分匹配** `suffix in filename` → 得分次之
5. 优先级越高的处理器优先匹配（ORM > 独立通道）

### 4.3 游戏特例

不同游戏可能有自己的命名约定。分析贴图目录时应：
1. 统计高频后缀模式
2. 对照材质定义 JSON 验证推断
3. 将游戏特有的后缀加入对应处理器的 `match` 列表

---

## 5. 色彩空间规则

| 贴图类型 | 色彩空间 | 原因 |
|---------|---------|------|
| 基础颜色/漫反射/自发光/ILM | `sRGB` | 这些贴图存储颜色信息，需要 sRGB→线性转换 |
| 法线/粗糙度/金属度/AO/ORM/遮罩/渐变/轮廓线 | `Non-Color` | 这些贴图存储数据（非颜色），不应进行色彩空间转换 |

---

## 6. 完整示例

### 6.1 PBR Standard（标准 PBR）

```json
{
  "preset_id": "my_pbr",
  "preset_label": "Standard PBR",
  "preset_category": "PBR",
  "version": "2.0",
  "texture_processors": {
    "base_color": {
      "type": "direct",
      "match": ["_d", "_diffuse", "_albedo", "_bc", "_basecolor"],
      "colorspace": "sRGB",
      "required": true,
      "outputs": { "default": { "socket": "Base Color" } }
    },
    "normal": {
      "type": "normal_map",
      "match": ["_n", "_normal", "_nm"],
      "colorspace": "Non-Color",
      "required": true,
      "outputs": { "default": { "socket": "Normal", "via": "NormalMap" } }
    },
    "roughness": {
      "type": "direct",
      "match": ["_r", "_roughness", "_rough"],
      "colorspace": "Non-Color",
      "fallback_value": 0.5,
      "outputs": { "default": { "socket": "Roughness" } }
    },
    "metallic": {
      "type": "direct",
      "match": ["_m", "_metallic", "_metal"],
      "colorspace": "Non-Color",
      "fallback_value": 0.0,
      "outputs": { "default": { "socket": "Metallic" } }
    },
    "ao": {
      "type": "direct",
      "match": ["_ao", "_occlusion"],
      "colorspace": "Non-Color",
      "fallback_value": 1.0,
      "outputs": { "default": { "socket": null, "note": "独立AO贴图，可选连接" } }
    },
    "emissive": {
      "type": "direct",
      "match": ["_e", "_emissive", "_emission"],
      "colorspace": "sRGB",
      "outputs": { "default": { "socket": "Emission Color" } }
    },
    "opacity": {
      "type": "direct",
      "match": ["_alpha", "_opacity", "_mask"],
      "colorspace": "Non-Color",
      "outputs": { "default": { "socket": "Alpha" } }
    },
    "orm": {
      "type": "rgb_split",
      "match": ["_orm", "_arm"],
      "colorspace": "Non-Color",
      "priority": 10,
      "outputs": {
        "G": { "socket": "Roughness", "label": "Roughness" },
        "B": { "socket": "Metallic", "label": "Metallic" }
      }
    }
  },
  "merge_strategy": { "orm_priority": "separate_only" },
  "node_group_source": null
}
```

### 6.2 PBR + ORM（ORM 优先）

```json
{
  "preset_id": "my_pbr_orm",
  "preset_label": "PBR + ORM",
  "preset_category": "PBR",
  "version": "2.0",
  "texture_processors": {
    "base_color": {
      "type": "direct",
      "match": ["_d", "_diffuse", "_albedo"],
      "colorspace": "sRGB",
      "required": true,
      "outputs": { "default": { "socket": "Base Color" } }
    },
    "normal": {
      "type": "normal_map",
      "match": ["_n", "_normal"],
      "colorspace": "Non-Color",
      "required": true,
      "outputs": { "default": { "socket": "Normal", "via": "NormalMap" } }
    },
    "orm": {
      "type": "rgb_split",
      "match": ["_orm", "_arm"],
      "colorspace": "Non-Color",
      "priority": 10,
      "outputs": {
        "R": { "socket": null,        "label": "AO" },
        "G": { "socket": "Roughness", "label": "Roughness" },
        "B": { "socket": "Metallic",  "label": "Metallic" }
      }
    },
    "roughness": {
      "type": "direct",
      "match": ["_roughness", "_rough", "_r"],
      "colorspace": "Non-Color",
      "priority": -10,
      "fallback_value": 0.5,
      "outputs": { "default": { "socket": "Roughness" } }
    },
    "metallic": {
      "type": "direct",
      "match": ["_metallic", "_metal", "_m"],
      "colorspace": "Non-Color",
      "priority": -10,
      "fallback_value": 0.0,
      "outputs": { "default": { "socket": "Metallic" } }
    },
    "emissive": {
      "type": "direct",
      "match": ["_e", "_emissive"],
      "colorspace": "sRGB",
      "outputs": { "default": { "socket": "Emission Color" } }
    },
    "opacity": {
      "type": "direct",
      "match": ["_alpha", "_opacity"],
      "colorspace": "Non-Color",
      "outputs": { "default": { "socket": "Alpha" } }
    }
  },
  "merge_strategy": { "orm_priority": "override" },
  "node_group_source": null
}
```

### 6.3 Genshin Impact 风格 NPR（使用自定义节点组）

```json
{
  "preset_id": "genshin_npr",
  "preset_label": "Genshin Impact NPR",
  "preset_category": "NPR",
  "version": "2.0",
  "texture_processors": {
    "diffuse": {
      "type": "direct",
      "match": ["_diffuse", "_d", "_albedo"],
      "colorspace": "sRGB",
      "required": true,
      "outputs": { "default": { "socket": "Base Color" } }
    },
    "lightmap": {
      "type": "custom_node_group",
      "match": ["_lightmap", "_ilm"],
      "colorspace": "sRGB",
      "required": true,
      "outputs": { "default": { "socket": "ILM Map", "note": "光照贴图连接到CelShader节点组的ILM输入" } }
    },
    "ramp": {
      "type": "direct",
      "match": ["_ramp", "_toon", "_lut"],
      "colorspace": "Non-Color",
      "outputs": { "default": { "socket": "Ramp Texture", "note": "渐变贴图用于ColorRamp查找" } }
    },
    "metal_mask": {
      "type": "direct",
      "match": ["_metal", "_metallic", "_mask"],
      "colorspace": "Non-Color",
      "outputs": { "default": { "socket": "Metal Mask", "note": "金属遮罩控制高光" } }
    },
    "normal": {
      "type": "normal_map",
      "match": ["_normal", "_n", "_nm"],
      "colorspace": "Non-Color",
      "outputs": { "default": { "socket": "Normal", "via": "NormalMap" } }
    }
  },
  "node_group_source": "presets/nodes/genshin_cel.blend\\NodeTree\\GenshinCelShader",
  "ai_metadata": {
    "source_game": "Genshin Impact v3.x",
    "analysis_date": "2026-05-26",
    "texture_sample_count": 4521,
    "confirmed_by_user": true,
    "notes": "通过分析 Exports/Materials 目录的 JSON 材质定义和 Textures 目录的贴图文件推断。"
  }
}
```

### 6.4 使用内置 Toon Ramp 节点组

```json
{
  "preset_id": "my_toon",
  "preset_label": "My Toon",
  "preset_category": "NPR",
  "version": "2.0",
  "texture_processors": {
    "base_color": {
      "type": "direct",
      "match": ["_d", "_diffuse", "_color"],
      "colorspace": "sRGB",
      "required": true,
      "outputs": { "default": { "socket": "Base Color" } }
    },
    "normal": {
      "type": "normal_map",
      "match": ["_n", "_normal"],
      "colorspace": "Non-Color",
      "outputs": { "default": { "socket": "Normal", "via": "NormalMap" } }
    }
  },
  "node_group_source": null
}
```

> 此方案使用内置的 `npr_toon_ramp` 程序化节点组，无需外部 `.blend`。

---

## 7. 常见游戏的贴图命名惯例

| 游戏/引擎 | 贴图命名特点 |
|----------|-------------|
| UE 通用 | `T_Character_D`, `T_Character_N`, `T_Character_ORM` |
| Unity 标准 | `Character_Albedo`, `Character_Normal`, `Character_MetallicSmoothness` |
| Genshin Impact | `Char_Diffuse`, `Char_LightMap`, `Char_NormalMap`, `Char_MetalMap` |
| Honkai Star Rail | `Char_Body_Diffuse`, `Char_Body_LightMap`, `Char_Hair_Ramp` |
| 米哈游通用 | ILM 贴图 (R=阴影, G=高光强度, B=高光颜色), Ramp 渐变贴图 |
| Source Engine | `texture_d`, `texture_n`, `texture_mrao` |
| Unity HDRP | `_BaseMap`, `_MaskMap`, `_NormalMap` |

---

## 8. 生成预设方案的步骤指南（给 LLM）

当用户发送材质文件和贴图列表时，**你必须主动询问不确定的问题**。按以下步骤生成预设 JSON：

### Step 1: 分析贴图目录

列出所有贴图文件名，提取后缀模式。统计出现频率。

例如输入：
```
Textures/
  char_body_d.png
  char_body_n.png
  char_body_lightmap.png
  char_body_ramp.png
  char_body_metal.png
  char_hair_d.png
  char_hair_n.png
  char_hair_ramp.png
  char_face_d.png
  char_face_n.png
  char_face_lightmap.png
  char_thumb.png
```

### Step 2: 分析材质定义 JSON

如果用户提供了 FModel 导出的材质 JSON，查看其中引用的贴图参数名，推断每个贴图的用途。

### Step 3: 识别不确定项并提问 ⚠️ 必须执行

**这是最关键的一步。在输出任何 JSON 之前，你必须向用户逐项确认以下问题：**

#### 3.1 未知后缀的贴图

统计结果中如果出现了下表之外的任何后缀，**必须逐一提问**：

> 我发现以下贴图后缀无法从命名规律直接确定用途，请逐一说明：
> - `_ILM`（共 N 张）：这是什么贴图？常见可能是光照贴图/阴影遮罩。它的 R/G/B/A 各通道分别代表什么？（例如：R=阴影强度, G=高光强度, B=高光颜色）
> - `_MetalMap`（共 N 张）：这是一张独立的金属度贴图还是金属遮罩？是否有 Alpha 通道存了额外信息？

#### 3.2 Alpha 通道用途

对每一类贴图，**必须询问其 Alpha 通道是否有特殊用途**。游戏优化经常把额外数据存在 Alpha 通道：

> 请确认以下贴图的 Alpha 通道用途：
> - `_d` (Base Color) → Alpha 是透明度还是存了其他信息（如光滑度、遮罩）？
> - `_lightmap` → Alpha 通道是否存了额外数据？
> - 任何其他贴图 → Alpha 是否有特殊用途？

#### 3.3 RGB 通道含义（ORM/打包贴图优先）

如果存在 `_ORM`、`_ARM`、`_MRA`、`_MRAO` 等打包贴图，**必须确认各通道含义**：

> 检测到 ORM 打包贴图。请确认 R/G/B 各通道的含义。常见惯例：
> - UE 风格（如原神、星铁）: R=AO, G=Roughness, B=Metallic
> - Unity HDRP 风格: R=Metallic, G=AO, B=Roughness
> - 你的游戏是哪种？

#### 3.4 工具节点组需求

参照 §3.5.1 工具节点组清单，**询问用户是否需要为某些贴图类型插入预处理节点组**：

> 根据你的材质数据，我建议以下处理管线：
> - 法线贴图 `_n` → 是否需要 `FlipNormalY`（UE→Blender Y轴反转）？
> - 粗糙度贴图 `_r` → 数据是粗糙度还是光滑度？如果是光滑度，需要 `GlossinessToRoughness` 转换
> - 其他特殊编码贴图 → 是否有需要解码的？

#### 3.5 确认处理器列表

在所有不确定项都确认之后，**汇总一份处理器清单请用户确认**，再输出 JSON：

> 根据你的确认，我计划生成以下处理器：
> - base_color: `_d` → Base Color, sRGB (direct)
> - normal: `_n` → Normal, Non-Color (normal_map)
> - orm: `_orm` → R=AO(不连), G=Roughness, B=Metallic, Non-Color (rgb_split)
> - lightmap: `_lightmap` → ILM Map, sRGB (custom_node_group, R=阴影强度, G=高光强度, B=高光颜色, A=未使用)
> - 忽略: `_thumb` (ignored)
> 请确认，或指出需要修改的地方。

### Step 4: 确定合并策略

检查是否存在 ORM 打包贴图。如果有：
- ORM 存在 + 独立 roughness/metallic 也存在 → `"separate_only"`
- 只有 ORM 没有独立贴图 → `"override"`

### Step 5: 填充 JSON 模板

按照第 2 节的 Schema 填写完整的 preset.json。**此步骤必须在用户确认 Step 3.4 的处理器清单之后才能执行。**

### Step 6: 验证

检查：
- [ ] `preset_id` 唯一且不含空格
- [ ] 每个处理器都有 `type` 和 `match`
- [ ] `rgb_split` 的 outputs key 是大写 `"R"`, `"G"`, `"B"`
- [ ] 色彩空间选择正确（颜色贴图=sRGB, 数据贴图=Non-Color）
- [ ] `required: true` 的处理器确实必要（如 base_color, normal）
- [ ] 如果有 `custom_node_group` 类型的处理器，`node_group_source` 不为 null

---

## 9. LLM 提示词模板

用户可将以下模板发送给 LLM（附上下文）：

```
你是一个 Blender 材质预设方案生成器。请严格按照 PRESET_SPEC.md 规范，
根据以下游戏材质文件和贴图列表，生成一个合法的 FModel 材质预设 JSON。

## 贴图文件列表
[粘贴文件列表，如 dir Textures /s 的输出]

## 材质定义 JSON（如果有）
[粘贴 .json 材质定义内容，如果没有则说"无"]

## 额外要求
- 预设名称: [填写]
- 风格: [PBR / NPR / Hybrid]
- 节点组来源: [如果有预制的 .blend 着色器节点组，填写路径；否则留空]

请输出完整的 preset.json。
```

---

## 10. 验证清单

生成 JSON 后，用户可通过以下方式验证：

1. **Blender 内验证**: "加载自定义预设" → 选择 JSON → 检查是否成功注册
2. **预设下拉菜单**: 检查新预设是否出现在下拉菜单中
3. **应用测试**: 选择预设 → 应用到一个测试材质 → 检查节点图是否正确
4. **报告导出**: 导出分析报告 → 检查贴图匹配结果
