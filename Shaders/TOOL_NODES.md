# FModel Tools — 工具节点组接口定义

> **输入统一命名**: Texture Input / Alpha Input / Roughness Input / Metallic Input / AO Input
> **输出统一命名**: Texture Output / Alpha Output（单通道）; R / G / B / A（打包拆分）; Normal Output（法线向量）

---

## 法线处理

### NormalMapToNormal (法线完整处理)
将法线贴图完整转为 Blender 可用的法线向量，内置强度调节。

| Socket 名 | 方向 | 类型 |
|-----------|------|------|
| Texture Input | IN | NodeSocketColor |
| Strength | IN | NodeSocketFloat (0-10, 默认 1.0) |
| Normal Output | OUT | NodeSocketVector |

### FlipNormalY
仅做 Y 轴（G 通道）取反，不包含 NormalMap 转换。

| Socket 名 | 方向 | 类型 |
|-----------|------|------|
| Texture Input | IN | NodeSocketColor |
| Texture Output | OUT | NodeSocketColor |

内部: `Vector Math Multiply: Color * (1, -1, 1)`

### FlipNormalX
仅做 X 轴（R 通道）取反。

| Socket 名 | 方向 | 类型 |
|-----------|------|------|
| Texture Input | IN | NodeSocketColor |
| Texture Output | OUT | NodeSocketColor |

内部: `Vector Math Multiply: Color * (-1, 1, 1)`

### DecodeBC5
BC5/DXT5 压缩法线解码（R=X, G=Y, 重建 Z）。

| Socket 名 | 方向 | 类型 |
|-----------|------|------|
| Texture Input | IN | NodeSocketColor |
| Texture Output | OUT | NodeSocketColor |

内部: `R→X, G→Y, Z=sqrt(1-X²-Y²)` via Vector Math 节点

### DecodeDXT5 (DXT5压缩法线解码)
Unity 常用粉红色法线贴图格式。R 通道存储在 Alpha 中以提高精度，G 通道为 Y 分量，B 通道通过勾股定理重建。

| Socket 名 | 方向 | 类型 |
|-----------|------|------|
| Texture Input | IN | NodeSocketColor |
| Alpha Input | IN | NodeSocketFloat |
| Texture Output | OUT | NodeSocketColor |

内部: `Alpha Input→X, Green通道→Y, Z=sqrt(1-X²-Y²); X/Y/Z 重映射到 [0,1] → CombineColor`。与 DecodeBC5 共享三角函数计算子节点组。

### BumpToNormal (高度→法线)
将灰度高度/凹凸贴图通过 Blender Bump 节点转为切线空间法线扰动。支持 Normal Input 接入法线贴图结果以实现 Bump+Normal 共存。

| Socket 名 | 方向 | 类型 |
|-----------|------|------|
| Texture Input | IN | NodeSocketColor |
| Strength | IN | NodeSocketFloat (0-1, 默认 1.0) |
| Normal Input | IN | NodeSocketVector |
| Normal Output | OUT | NodeSocketVector |

内部: `Texture Input → Bump.Height; Strength → Bump.Distance; Normal Input → Bump.Normal; Bump.Normal → Normal Output`

---

## 打包贴图提取

### ExtractPackedChannels
将一张打包贴图的 RGB 通道拆分为独立浮点数输出。

| Socket 名 | 方向 | 类型 |
|-----------|------|------|
| Texture Input | IN | NodeSocketColor |
| Alpha Input | IN | NodeSocketFloat |
| R | OUT | NodeSocketFloat |
| G | OUT | NodeSocketFloat |
| B | OUT | NodeSocketFloat |
| A | OUT | NodeSocketFloat |

内部: `Texture Input → SeparateRGB → R, G, B; Alpha Input → A`

### DecodeORM (UE 风格)
ORM 贴图的 R=遮蔽(AO), G=粗糙度, B=金属度。

| Socket 名 | 方向 | 类型 |
|-----------|------|------|
| Texture Input | IN | NodeSocketColor |
| Alpha Input | IN | NodeSocketFloat |
| R (AO) | OUT | NodeSocketFloat |
| G (Roughness) | OUT | NodeSocketFloat |
| B (Metallic) | OUT | NodeSocketFloat |
| A | OUT | NodeSocketFloat |

内部: `ExtractPackedChannels → R→标 AO, G→标 Roughness, B→标 Metallic, A 直通`

### DecodeARM (Unity HDRP 风格)
ARM 贴图的 R=金属度, G=遮蔽(AO), B=粗糙度。

| Socket 名 | 方向 | 类型 |
|-----------|------|------|
| Texture Input | IN | NodeSocketColor |
| Alpha Input | IN | NodeSocketFloat |
| R (Metallic) | OUT | NodeSocketFloat |
| G (AO) | OUT | NodeSocketFloat |
| B (Roughness) | OUT | NodeSocketFloat |
| A | OUT | NodeSocketFloat |

内部: `ExtractPackedChannels → 通道重排后输出`

### DecodeMRAO
MRAO 贴图的 R=金属度, G=粗糙度, B=遮蔽(AO)。

| Socket 名 | 方向 | 类型 |
|-----------|------|------|
| Texture Input | IN | NodeSocketColor |
| Alpha Input | IN | NodeSocketFloat |
| R (Metallic) | OUT | NodeSocketFloat |
| G (Roughness) | OUT | NodeSocketFloat |
| B (AO) | OUT | NodeSocketFloat |
| A | OUT | NodeSocketFloat |

内部: `ExtractPackedChannels → 通道重排后输出`

---

## 值转换

### InvertChannel
单通道取反: `1 - x`。同时覆盖「粗糙度→光滑度」「光滑度→粗糙度」等所有值反转场景。

| Socket 名 | 方向 | 类型 |
|-----------|------|------|
| Texture Input | IN | NodeSocketFloat |
| Texture Output | OUT | NodeSocketFloat |

内部: `Math Subtract: 1.0 - Texture Input`

## 汇总清单

| # | 节点组名 | 分类 | 输入 | 输出 |
|---|---------|------|------|------|
| 1 | `NormalMapToNormal` | 法线 | Texture Input, Strength | Normal Output |
| 2 | `FlipNormalY` | 法线 | Texture Input | Texture Output |
| 3 | `FlipNormalX` | 法线 | Texture Input | Texture Output |
| 4 | `DecodeBC5` | 法线解码 | Texture Input | Texture Output |
| 5 | `DecodeDXT5` | 法线解码 | Texture Input, Alpha Input | Texture Output |
| 6 | `BumpToNormal` | 法线 | Texture Input, Strength, Normal Input | Normal Output |
| 7 | `ExtractPackedChannels` | 贴图解码 | Texture Input, Alpha Input | R, G, B, A |
| 8 | `DecodeORM` | 贴图解码 | Texture Input, Alpha Input | R(AO), G(Rough), B(Metal), A |
| 9 | `DecodeARM` | 贴图解码 | Texture Input, Alpha Input | R(Metal), G(AO), B(Rough), A |
| 10 | `DecodeMRAO` | 贴图解码 | Texture Input, Alpha Input | R(Metal), G(Rough), B(AO), A |
| 11 | `InvertChannel` | 值转换 | Texture Input | Texture Output |
