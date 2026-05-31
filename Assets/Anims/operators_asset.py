# FModel_Tools/Assets/Anims/operators_asset.py
# 资产操作符 — 生成字典、挂载/卸载资产库、搜索重定向
import bpy
import os
from ...Fmodel.Pipeline.manager import PipelineManager
from ...core import (
    PipelineConfig, PipelineContext, PipelineStage,
    SourceType, ImportMode,
)

class FMODEL_ProjectAssetLib(bpy.types.PropertyGroup):
    name: bpy.props.StringProperty(name="库名称") # type: ignore
    path: bpy.props.StringProperty(name="目录路径") # type: ignore

class FMODEL_AssetProperties(bpy.types.PropertyGroup):
    source_dir: bpy.props.StringProperty(name="源目录", subtype='DIR_PATH', default="") # type: ignore
    asset_out_dir: bpy.props.StringProperty(name="输出目录", subtype='DIR_PATH', default="") # type: ignore
    lib_name: bpy.props.StringProperty(name="资产库名称", default="FModel_Anims") # type: ignore
    
    skeleton_filter: bpy.props.StringProperty(name="骨架校验匹配", default="") # type: ignore
    import_scale: bpy.props.FloatProperty(name="全局动画缩放", default=0.01, min=0.0001, precision=4, description="打包此资产库时的统一缩放比例") # type: ignore
    rotation_only: bpy.props.BoolProperty(name="仅导入旋转", default=False) # type: ignore
    import_curves: bpy.props.BoolProperty(name="导入 Curve 辅助曲线", default=False) # type: ignore
    
    # ⭐ 极简回归：统一管控开关
    generate_thumbnails: bpy.props.BoolProperty(name="生成缩略图", default=True, description="后台渲染缩略图，打包进原生资产库并保留在目录中供极速加载") # type: ignore
    thumb_resolution: bpy.props.EnumProperty(
        name="分辨率",
        items=[('128', "128 x 128", ""), ('256', "256 x 256", ""), ('512', "512 x 512", "")],
        default='256'
    ) # type: ignore

    chunk_size: bpy.props.IntProperty(name="分卷大小", default=500, min=50, max=5000, description="单个库文件最多包含的动作数量，超过将自动分卷存入 Vol_2, Vol_3...") # type: ignore
    force_rebuild: bpy.props.BoolProperty(name="强制重建", default=False, description="无视增量更新，删除该骨架的旧库文件并全量重新打包") # type: ignore
    
    project_libs: bpy.props.CollectionProperty(type=FMODEL_ProjectAssetLib) # type: ignore
    active_lib_index: bpy.props.IntProperty(default=0) # type: ignore

class FMODEL_OT_build_anim_library(bpy.types.Operator):
    bl_idname = "fmodel.build_anim_library"
    bl_label = "确认导入并构建资产库"
    bl_options = {'REGISTER', 'UNDO'}

    auto_save: bpy.props.BoolProperty(
        name="执行前自动保存",
        description="未保存的工程会在执行前自动保存",
        default=True
    ) # type: ignore

    import_batch_size: bpy.props.IntProperty(
        name="导入批次",
        default=200,
        min=20,
        max=2000,
        description="每批导入动作数量"
    ) # type: ignore
    import_large_threshold: bpy.props.IntProperty(
        name="巨量阈值",
        default=2000,
        min=200,
        max=50000,
        description="超过该数量自动降批次"
    ) # type: ignore
    import_max_cycles: bpy.props.IntProperty(
        name="最大循环",
        default=500,
        min=10,
        max=50000,
        description="导入任务循环上限"
    ) # type: ignore
    import_max_consecutive_failures: bpy.props.IntProperty(
        name="连续失败阈值",
        default=120,
        min=10,
        max=5000,
        description="连续失败后提前中止"
    ) # type: ignore
    import_resume_enabled: bpy.props.BoolProperty(
        name="启用断点恢复",
        default=True,
        description="导入中断后可从上次位置继续"
    ) # type: ignore

    @classmethod
    def poll(cls, context):
        obj = context.active_object
        return obj is not None and obj.type == 'ARMATURE'

    def invoke(self, context, event):
        props = context.scene.fmodel_assets
        active_obj = context.active_object
        ue_sk_name = active_obj.get("FModel_Skeleton", "")
        
        if ue_sk_name: props.skeleton_filter = str(ue_sk_name)
        elif not props.skeleton_filter: props.skeleton_filter = active_obj.name
            
        return context.window_manager.invoke_props_dialog(self, width=450)

    def draw(self, context):
        layout = self.layout
        props = context.scene.fmodel_assets
        
        # 未保存工程提示
        if not bpy.data.filepath:
            box_warn = layout.box()
            box_warn.label(text="⚠ 工程尚未保存", icon='ERROR')
            box_warn.prop(self, "auto_save")
            layout.separator()
        
        box_dir = layout.box()
        box_dir.label(text="1. 资产路径配置", icon='FILE_FOLDER')
        col_dir = box_dir.column(align=True)
        col_dir.prop(props, "source_dir")
        col_dir.prop(props, "asset_out_dir")
        col_dir.prop(props, "lib_name")
        layout.separator()
        
        box_flt = layout.box()
        box_flt.label(text="2. 安全与匹配机制", icon='FILTER')
        box_flt.prop(props, "skeleton_filter", icon='BONE_DATA')
        layout.separator()
        
        box_anim = layout.box()
        box_anim.label(text="3. 底层导入参数", icon='OPTIONS')
        
        box_anim.prop(props, "import_scale", icon='OBJECT_ORIGIN')
        box_anim.prop(props, "rotation_only")
        box_anim.prop(props, "import_curves")

        box_task = layout.box()
        box_task.label(text="任务分配与稳定性", icon='TIME')
        col_task = box_task.column(align=True)
        col_task.prop(self, "import_batch_size")
        col_task.prop(self, "import_large_threshold")
        col_task.prop(self, "import_max_cycles")
        col_task.prop(self, "import_max_consecutive_failures")
        col_task.prop(self, "import_resume_enabled")
        layout.separator()

        box_store = layout.box()
        box_store.label(text="4. 存储与分卷机制 (智能增量)", icon='PACKAGE')
        row = box_store.row()
        row.prop(props, "chunk_size")
        row.prop(props, "force_rebuild", toggle=True, icon='TRASH')
        
        layout.separator()
        
        box_thumb = layout.box()
        box_thumb.label(text="5. 缩略图生成与存储", icon='RENDER_STILL')
        row_thumb = box_thumb.row(align=True)
        row_thumb.prop(props, "generate_thumbnails")
        if props.generate_thumbnails:
            row_thumb.prop(props, "thumb_resolution", text="")

    def execute(self, context):
        from ...core import log_info
        log_info("FMODEL_Asset", "打包程序启动")
        
        # 未保存工程自动保存
        if not bpy.data.filepath:
            if self.auto_save:
                # 尝试保存到临时目录
                import tempfile
                temp_dir = tempfile.gettempdir()
                temp_path = os.path.join(temp_dir, "FModel_TempProject.blend")
                try:
                    bpy.ops.wm.save_as_mainfile(filepath=temp_path, copy=False)
                    self.report({'INFO'}, f"工程已自动保存到: {temp_path}")
                except Exception as e:
                    self.report({'ERROR'}, f"自动保存失败: {e}")
                    return {'CANCELLED'}
            else:
                self.report({'WARNING'}, "工程未保存，部分功能可能受限")
        
        target_arm = context.active_object
        props = context.scene.fmodel_assets 
        
        src_dir = bpy.path.abspath(props.source_dir)
        out_dir = bpy.path.abspath(props.asset_out_dir)
        
        if not src_dir or not out_dir or not os.path.exists(src_dir) or not os.path.exists(out_dir):
            self.report({'ERROR'}, "源目录或输出目录无效！")
            return {'CANCELLED'}

        cfg = PipelineConfig(
            source_dir=props.source_dir,
            output_dir=props.asset_out_dir,
            library_name=props.lib_name,
            skeleton_filter=props.skeleton_filter,
            source_type=SourceType.FMODEL_UEANIM.value,
            import_mode=ImportMode.UEANIM_DIRECT.value,
            import_scale=props.import_scale,
            rotation_only=props.rotation_only,
            import_curves=props.import_curves,
            generate_thumbnails=props.generate_thumbnails,
            thumb_resolution=props.thumb_resolution,
            chunk_size=props.chunk_size,
            force_rebuild=props.force_rebuild,
            target_armature=target_arm.name,
            import_batch_size=self.import_batch_size,
            max_import_cycles=self.import_max_cycles,
            large_import_threshold=self.import_large_threshold,
            max_consecutive_failures=self.import_max_consecutive_failures,
            import_resume_enabled=self.import_resume_enabled,
        ).to_dict()

        manager = PipelineManager()
        pipeline_context = PipelineContext.load_from_blender_text() or PipelineContext(config=cfg)
        pipeline_context.config.update(cfg)

        for stage_name in (
            PipelineStage.DICTIONARY_ACQUISITION.value,
            PipelineStage.FORMAT_CONVERSION.value,
            PipelineStage.ASSET_IMPORT.value,
            PipelineStage.LIBRARY_BUILDING.value,
            PipelineStage.FINALIZATION.value,
        ):
            if not manager.run_stage(pipeline_context, stage_name):
                pipeline_context.save_to_blender_text()
                self.report({'ERROR'}, f"阶段失败: {stage_name}")
                return {'CANCELLED'}

        pipeline_context.save_to_blender_text()

        try:
            rel_out_dir = bpy.path.relpath(out_dir)
        except ValueError:
            rel_out_dir = out_dir

        already_linked = False
        for lib in props.project_libs:
            if lib.name == props.lib_name:
                lib.path = rel_out_dir or out_dir
                already_linked = True
                break

        if not already_linked:
            new_lib = props.project_libs.add()
            new_lib.name = props.lib_name
            new_lib.path = rel_out_dir or out_dir

        bpy.ops.fmodel.scan_anims()
        self.report({'INFO'}, "构建完毕（统一管线）")
        return {'FINISHED'}

def register():
    bpy.utils.register_class(FMODEL_ProjectAssetLib)
    bpy.utils.register_class(FMODEL_AssetProperties)
    bpy.types.Scene.fmodel_assets = bpy.props.PointerProperty(type=FMODEL_AssetProperties)
    bpy.utils.register_class(FMODEL_OT_build_anim_library)

def unregister():
    bpy.utils.unregister_class(FMODEL_OT_build_anim_library)
    del bpy.types.Scene.fmodel_assets
    bpy.utils.unregister_class(FMODEL_AssetProperties)
    bpy.utils.unregister_class(FMODEL_ProjectAssetLib)
