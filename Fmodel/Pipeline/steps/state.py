
# FModel_Tools/Fmodel/Pipeline/steps/state.py
# 向导状态

import bpy


# ============================================================
# 步骤状态管理
# ============================================================

class WizardState(bpy.types.PropertyGroup):
    """向导状态"""
    current_step: bpy.props.IntProperty(name="当前步骤", default=1, min=1, max=4)

    # Step 1: 流程选择
    flow_type: bpy.props.EnumProperty(
        name="流程类型",
        items=[
            ('FMODEL', "FModel 流程", "处理 FModel 导出的 .ueanim 文件"),
            ('UNITY', "Unity 流程", "处理 Unity 导出的 .anim 文件"),
        ],
        default='FMODEL'
    )

    # Step 2: 项目选择
    source_dir: bpy.props.StringProperty(name="项目目录", subtype='DIR_PATH')
    output_dir: bpy.props.StringProperty(name="输出目录", subtype='DIR_PATH')
    library_name: bpy.props.StringProperty(name="资产库名称", default="AnimLibrary")
    skeleton_filter: bpy.props.StringProperty(name="骨架过滤", default="")

    # Step 3: 扫描结果
    scan_completed: bpy.props.BoolProperty(default=False)
    scan_skeleton_count: bpy.props.IntProperty(default=0)
    scan_anim_count: bpy.props.IntProperty(default=0)
    scan_new_count: bpy.props.IntProperty(default=0)
    scan_existing_count: bpy.props.IntProperty(default=0)

    # Step 4: 导入状态
    import_target_skeleton: bpy.props.StringProperty(name="目标骨架")
    import_completed: bpy.props.BoolProperty(default=False)

    # Step 4: 导入参数（从Operator移到PropertyGroup）
    import_scale: bpy.props.FloatProperty(
        name="缩放",
        default=0.01,
        min=0.0001,
        max=100.0,
        precision=4
    )
    rotation_only: bpy.props.BoolProperty(
        name="仅导入旋转",
        default=False
    )
    import_curves: bpy.props.BoolProperty(
        name="导入曲线",
        default=True
    )

    # 大批量导入任务切片参数
    import_batch_size: bpy.props.IntProperty(
        name="导入批次",
        default=200,
        min=20,
        max=2000,
        description="每批导入动作数量，越小越稳，越大越快"
    )
    import_large_threshold: bpy.props.IntProperty(
        name="巨量阈值",
        default=2000,
        min=200,
        max=50000,
        description="超过该数量自动强制降批次以防崩溃"
    )
    import_max_cycles: bpy.props.IntProperty(
        name="最大循环",
        default=500,
        min=10,
        max=50000,
        description="导入批次循环上限"
    )
    import_max_consecutive_failures: bpy.props.IntProperty(
        name="连续失败阈值",
        default=120,
        min=10,
        max=5000,
        description="连续失败达到阈值后提前中止任务"
    )
    import_resume_enabled: bpy.props.BoolProperty(
        name="启用断点恢复",
        default=True,
        description="导入中断后可从上次批次位置继续"
    )

    # 导入后清理选项
    clean_after_import: bpy.props.BoolProperty(
        name="导入后清理动作",
        default=False,
        description="导入完成后自动清理冗余关键帧（适用于动捕/烘焙动作）"
    )
    clean_threshold: bpy.props.FloatProperty(
        name="精简阈值",
        default=0.001,
        min=0.0,
        max=1.0,
        precision=4
    )
    clean_flat_channels: bpy.props.BoolProperty(
        name="精简平坦通道",
        default=True
    )

    # Step 5: 资产库
    lib_generate_thumbnails: bpy.props.BoolProperty(name="生成缩略图", default=True)
    lib_thumb_resolution: bpy.props.EnumProperty(
        name="缩略图分辨率",
        items=[('128', "128", ""), ('256', "256", ""), ('512', "512", ""), ('1024', "1024", "")],
        default='256'
    )
    lib_thumb_quality: bpy.props.EnumProperty(
        name="渲染质量",
        items=[
            ('OPENGL', "OpenGL (快)", "视口快照, 速度快"),
            ('RENDER', "Render (高质量)", "使用场景渲染引擎, 速度慢但质量高"),
        ],
        default='OPENGL'
    )
    lib_thumb_isolate: bpy.props.BoolProperty(
        name="仅渲染骨架子级",
        description="渲染时隐藏场景其他物体，仅保留骨架及其子级网格",
        default=True
    )
    lib_chunk_size: bpy.props.IntProperty(name="分卷大小", default=500, min=50, max=5000)
    lib_force_rebuild: bpy.props.BoolProperty(name="强制重建", default=False)
    lib_save_model: bpy.props.BoolProperty(name="同时保存模型", default=False, description="打包动画后自动保存当前骨架的模型资产")
    lib_model_preview: bpy.props.BoolProperty(name="生成模型预览图", default=True)
    lib_completed: bpy.props.BoolProperty(default=False)


def register():
    bpy.utils.register_class(WizardState)


def unregister():
    bpy.utils.unregister_class(WizardState)
