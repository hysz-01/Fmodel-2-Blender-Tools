# FModel_Tools/Assets/Utils/incremental_preview.py
# 增量预览 — 动画资产缩略图增量生成

import bpy
import os
import json


class FMODEL_IncrementalItem(bpy.types.PropertyGroup):
    """增量项目"""
    name: bpy.props.StringProperty()
    source_path: bpy.props.StringProperty()
    status: bpy.props.EnumProperty(
        items=[
            ('NEW', "新增", "将被导入"),
            ('EXISTING', "已存在", "跳过"),
            ('UPDATED', "更新", "将被覆盖"),
            ('FILTERED', "过滤", "不匹配骨架"),
        ],
        default='NEW'
    )
    hash_value: bpy.props.StringProperty()


class FMODEL_IncrementalProperties(bpy.types.PropertyGroup):
    """增量预览属性"""
    items: bpy.props.CollectionProperty(type=FMODEL_IncrementalItem)
    active_index: bpy.props.IntProperty(default=0)
    
    new_count: bpy.props.IntProperty(default=0)
    existing_count: bpy.props.IntProperty(default=0)
    filtered_count: bpy.props.IntProperty(default=0)
    
    show_new_only: bpy.props.BoolProperty(name="仅显示新增", default=False)


class FMODEL_OT_PreviewIncremental(bpy.types.Operator):
    """预览增量更新"""
    bl_idname = "fmodel.preview_incremental"
    bl_label = "预览增量更新"
    bl_options = {'REGISTER', 'UNDO'}
    
    @classmethod
    def poll(cls, context):
        props = getattr(context.scene, "fmodel_assets", None)
        return props and props.source_dir and props.asset_out_dir
    
    def execute(self, context):
        props = context.scene.fmodel_assets
        preview = context.scene.fmodel_incremental
        
        src_dir = bpy.path.abspath(props.source_dir)
        out_dir = bpy.path.abspath(props.asset_out_dir)
        
        # 清空旧数据
        preview.items.clear()
        preview.new_count = 0
        preview.existing_count = 0
        preview.filtered_count = 0
        
        if not os.path.exists(src_dir):
            self.report({'ERROR'}, "源目录不存在")
            return {'CANCELLED'}
        
        # 获取已处理的源文件列表
        existing_sources = self.get_existing_sources(out_dir)
        
        # 扫描源目录
        target_arm = context.active_object
        sk_filter = props.skeleton_filter
        
        for root, dirs, files in os.walk(src_dir):
            dirs[:] = [d for d in dirs if not d.startswith('.')]
            
            for f in files:
                if not f.lower().endswith('.ueanim'):
                    continue
                
                file_path = os.path.join(root, f)
                rel_src = os.path.relpath(file_path, src_dir).replace('\\', '/')
                
                item = preview.items.add()
                item.name = f
                item.source_path = file_path
                
                # 检查是否已存在
                if rel_src in existing_sources:
                    item.status = 'EXISTING'
                    preview.existing_count += 1
                    continue
                
                # 检查骨架匹配
                json_path = os.path.splitext(file_path)[0] + ".json"
                if sk_filter and not self.check_skeleton_match(json_path, sk_filter):
                    item.status = 'FILTERED'
                    preview.filtered_count += 1
                    continue
                
                # 新增项目
                item.status = 'NEW'
                preview.new_count += 1
        
        # 打开预览对话框
        return context.window_manager.invoke_props_dialog(self, width=500)
    
    def draw(self, context):
        layout = self.layout
        preview = context.scene.fmodel_incremental
        
        # 统计信息
        box_stats = layout.box()
        row = box_stats.row(align=True)
        
        col_new = row.column()
        col_new.label(text=f"新增: {preview.new_count}", icon='ADD')
        
        col_existing = row.column()
        col_existing.label(text=f"已存在: {preview.existing_count}", icon='CHECKMARK')
        
        col_filtered = row.column()
        col_filtered.label(text=f"过滤: {preview.filtered_count}", icon='FILTER')
        
        layout.separator()
        
        # 过滤选项
        row_filter = layout.row()
        row_filter.prop(preview, "show_new_only", icon='FILTER')
        
        layout.separator()
        
        # 项目列表
        box_list = layout.box()
        
        if preview.new_count == 0 and preview.existing_count == 0:
            box_list.label(text="没有找到可处理的文件", icon='INFO')
            return
        
        # 显示新增项目
        new_items = [item for item in preview.items if item.status == 'NEW']
        if new_items:
            box_list.label(text=f"将要导入 ({len(new_items)} 项):", icon='IMPORT')
            col = box_list.column(align=True)
            for item in new_items[:10]:  # 最多显示10项
                row = col.row()
                row.label(text=item.name, icon='ACTION')
                row.label(text="新增", icon='ADD')
            
            if len(new_items) > 10:
                col.label(text=f"... 还有 {len(new_items) - 10} 项", icon='INFO')
        
        # 显示已存在项目（折叠）
        if not preview.show_new_only:
            existing_items = [item for item in preview.items if item.status == 'EXISTING']
            if existing_items:
                box_list.separator()
                box_list.label(text=f"将要跳过 ({len(existing_items)} 项):", icon='CHECKMARK')
                col = box_list.column(align=True)
                for item in existing_items[:5]:
                    row = col.row()
                    row.label(text=item.name, icon='ACTION')
                    row.label(text="已存在", icon='CHECKMARK')
                
                if len(existing_items) > 5:
                    col.label(text=f"... 还有 {len(existing_items) - 5} 项", icon='INFO')
            
            # 显示过滤项目
            filtered_items = [item for item in preview.items if item.status == 'FILTERED']
            if filtered_items:
                box_list.separator()
                box_list.label(text=f"骨架不匹配 ({len(filtered_items)} 项):", icon='BONE_DATA')
                col = box_list.column(align=True)
                for item in filtered_items[:5]:
                    row = col.row()
                    row.label(text=item.name, icon='ACTION')
                    row.label(text="过滤", icon='X')
                
                if len(filtered_items) > 5:
                    col.label(text=f"... 还有 {len(filtered_items) - 5} 项", icon='INFO')
    
    def get_existing_sources(self, out_dir):
        """获取已处理的源文件列表"""
        existing = set()
        
        if not os.path.exists(out_dir):
            return existing
        
        for f in os.listdir(out_dir):
            if f.endswith("_manifest.json"):
                manifest_path = os.path.join(out_dir, f)
                try:
                    with open(manifest_path, 'r', encoding='utf-8') as mf:
                        data = json.load(mf)
                        sources = data.get("__processed_sources__", [])
                        existing.update(sources)
                except (json.JSONDecodeError, IOError) as e:
                    # JSON解析失败，忽略该文件
                    pass
        
        return existing
    
    def check_skeleton_match(self, json_path, filter_name):
        """检查骨架是否匹配"""
        if not filter_name or not os.path.exists(json_path):
            return True
        
        try:
            from .utils_asset import get_skeleton_name_from_json
            sk_name = get_skeleton_name_from_json(json_path)
            if sk_name:
                return filter_name.lower() in sk_name.lower() or sk_name.lower() in filter_name.lower()
        except (OSError, IOError) as e:
            # 文件访问失败，忽略该文件
            pass
        
        return True


class FMODEL_OT_ApplyIncremental(bpy.types.Operator):
    """应用增量更新（仅导入新增）"""
    bl_idname = "fmodel.apply_incremental"
    bl_label = "执行增量更新"
    bl_options = {'REGISTER', 'UNDO'}
    
    @classmethod
    def poll(cls, context):
        preview = getattr(context.scene, "fmodel_incremental", None)
        return preview and preview.new_count > 0
    
    def execute(self, context):
        # 调用原有的资产库构建操作符
        bpy.ops.fmodel.build_anim_library('INVOKE_DEFAULT')
        return {'FINISHED'}


class FMODEL_UL_IncrementalItems(bpy.types.UIList):
    """增量项目列表"""
    
    def filter_items(self, context, data, propname):
        items = getattr(data, propname)
        preview = context.scene.fmodel_incremental
        
        flt_flags = []
        flt_neworder = []
        
        for item in items:
            if preview.show_new_only and item.status != 'NEW':
                flt_flags.append(0)
            else:
                flt_flags.append(self.bitflag_filter_item)
        
        return flt_flags, flt_neworder
    
    def draw_item(self, context, layout, data, item, icon, active_data, active_propname):
        row = layout.row(align=True)
        
        # 状态图标
        status_icons = {
            'NEW': 'ADD',
            'EXISTING': 'CHECKMARK',
            'UPDATED': 'FILE_REFRESH',
            'FILTERED': 'X'
        }
        status_texts = {
            'NEW': '新增',
            'EXISTING': '已存在',
            'UPDATED': '更新',
            'FILTERED': '过滤'
        }
        
        row.label(text=item.name, icon='ACTION')
        row.label(text=status_texts.get(item.status, ''), icon=status_icons.get(item.status, 'NONE'))


# ============================================================
# 注册
# ============================================================

classes = (
    FMODEL_IncrementalItem,
    FMODEL_IncrementalProperties,
    FMODEL_OT_PreviewIncremental,
    FMODEL_OT_ApplyIncremental,
    FMODEL_UL_IncrementalItems,
)


def register():
    for cls in classes:
        bpy.utils.register_class(cls)
    bpy.types.Scene.fmodel_incremental = bpy.props.PointerProperty(type=FMODEL_IncrementalProperties)


def unregister():
    del bpy.types.Scene.fmodel_incremental
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)