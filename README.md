# FModel 2 Blender Tools

专为 **UE/FModel** 设计的 Blender 5.0 全流程资产管线工具集。

---

## 功能模块概览

### 1. 资产管线（Asset Pipeline）

4 步引导式导入流程，一键完成动画导入 → 资产库打包 → 缩略图生成。

| 步骤 | 功能 |
|------|------|
| 流程 | 选择 FModel 流程 |
| 项目 | 配置项目目录、输出目录、骨架过滤（支持滴管拾取骨架名） |
| 扫描 | 扫描 `.ueanim` 动画字典，自动发现骨架和动作 |
| 导入/打包 | 设置导入参数 → 一键导入动画 → 构建资产库 → 生成 WebP 缩略图 |

缩略图支持：
- OpenGL 视口快照（快速）和 Render 渲染（高质量）两种模式
- 仅渲染骨架子级（排除场景其他物体）
- 确定性 Hash 命名——同动作重烘焙自动覆盖旧缩略图
- 完成后可单独"重新生成缩略图"，无需重新导入

---

### 2. 材质工具（Material Tools）

自动解析 UE JSON 材质数据，构建 PBR/NPR 着色器节点图。

**Phase 1 — 资产发现**  
解析 FModel 导出的模型 JSON 和材质实例 JSON，提取贴图路径和标量/向量参数。

**Phase 2 — 通道解析**  
UE 参数名 → 标准通道映射，支持：
- GameProfile 精确匹配
- CUE4Parse 材质参数字典（200+ 条目）
- 内置关键词匹配
- ORM 贴图自动检测（`_ORM`/`_ARM`/`_MRAO` 后缀 → 自动分流至 AO/Roughness/Metallic）

**Phase 3 — 节点构建**  
自动创建 Blender 材质节点图：贴图 → 工具节点链 → 着色器组连接，支持 NormalMap / Invert / ORM Decode 等工具节点。

**手动模式**：支持材质解析 / 应用 / 报告导出等手动操作。

---

### 3. 着色器管理器（Shader Manager）

- **模板导入**：从 `Shaders/shaders.blend` 一键导入 PBR Standard / NPR Toon 等预设着色器
- **自定义着色器**：保存场景节点组为模板，支持跨文件复用
- **接口映射**：自动识别节点组接口，一键映射到标准通道（Base Color / Normal / Roughness 等）
- **预设系统**：支持 JSON 格式预设导出/加载，材质工具面板直接调用

---

### 4. 资产库（Asset Library）

**动画资产**  
- 树/列表/卡片三种视图模式
- 骨架过滤 + 名称搜索
- 缩略图预览 + 详情面板（帧数/时长/骨架/源文件）
- 一键预览/应用动画到骨架
- NLA 部署模式（替换/追加/覆盖）

**模型资产**  
- 保存角色模型到资产库（带预览图）
- 卡片网格浏览，预览图直显
- 一键导入模型到场景

---

### 5. 拓展工具（Extension Tools）

| 工具 | 功能 |
|------|------|
| 网格工具 | 清理空白形态键 / 按材质分离 |
| 骨架/姿态 | 整理骨骼层级 / 批量重命名 / UE标准命名 / 骨骼映射 / 姿态镜像 |
| 动画工具 | 清理动作关键帧 / 批量清理 |

---

### 6. GameProfile 管理器

在着色器编辑器中管理 GameProfile 预设（JSON），支持：
- 创建/删除/编辑预设
- UE 参数名 → 标准通道的映射配置
- 自动保存至 `Shaders/GameProfiles/`

---

## FModel 导出建议

为保障材质解析和动画导入的完整性，**请在 FModel 导出时确保以下 JSON 文件存在**：

### 模型导出
```
✅ 模型文件 (.uemodel)
✅ 模型 JSON (同名的 .json，包含 SkeletalMesh / MaterialInterface 数据)
✅ 材质实例 JSON (MaterialInstanceConstant，包含 TextureParameterValues)
```

### 贴图导出
```
✅ 全部贴图 (.png / .tga / .dds 等)
✅ 保持目录结构 (Content/Textures/...)
```

### 动画导出
```
✅ 动画文件 (.ueanim)
✅ 动画 JSON (包含 AnimSequence 结构)
✅ 字典清单 JSON (带 Skeleton 引用和文件夹层级)
```

### 推荐 FModel 设置
- 导出模式：**单一文件 + JSON**
- 贴图格式：PNG（保留 Alpha 通道用于 WebP 缩略图）
- 材质导出：**保留 MaterialInstanceConstant 的纹理参数值**
- 目录结构：**保留 UE4 原始层级**（不放平）

---

## 安装

将 `FModel_Tools/` 文件夹放入 Blender addons 目录：

```
%APPDATA%\Blender Foundation\Blender\5.0\scripts\addons\
```

在 Blender 偏好设置中启用 **FModel Tools** 插件。

---

## 需求

- Blender 5.0+
- 内置 Vendor 依赖：`io_scene_ueformat` / `io_scene_psk_psa`（自动检测用户安装版本）

---

## 国际化

- 默认中文界面
- 在 Blender 偏好设置中切换语言为 English 后，所有面板、按钮、描述自动切换英文（309 条翻译）
