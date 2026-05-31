# FModel_Tools/Fmodel/importers/export/operator_export_fbx.py
# FBX 导出

import bpy
import os
from bpy_extras.io_utils import ExportHelper


class EXPORT_OT_FBX_Batch(bpy.types.Operator, ExportHelper):
    """批量导出选中对象为 FBX 文件"""
    bl_idname = "fmodel.export_fbx_batch"
    bl_label = "批量导出 FBX"
    bl_options = {'REGISTER', 'UNDO'}
    
    filename_ext = ".fbx"
    filter_glob: bpy.props.StringProperty(default="*.fbx", options={'HIDDEN'}) # type: ignore
    
    export_animations: bpy.props.BoolProperty(
        name="导出动画",
        description="导出物体的动画数据",
        default=True
    ) # type: ignore
    
    export_armatures: bpy.props.BoolProperty(
        name="导出骨架",
        description="导出骨架数据",
        default=True
    ) # type: ignore
    
    export_morph: bpy.props.BoolProperty(
        name="导出形态键",
        description="导出网格的形态键数据",
        default=True
    ) # type: ignore
    
    export_apply: bpy.props.BoolProperty(
        name="应用修改器",
        description="应用所有修改器后再导出",
        default=True
    ) # type: ignore
    
    export_scale: bpy.props.FloatProperty(
        name="导出缩放",
        description="导出时的缩放比例",
        default=1.0,
        min=0.001,
        max=1000.0
    ) # type: ignore
    
    export_axis_forward: bpy.props.EnumProperty(
        name="前向轴",
        items=[
            ('X', "X", ""),
            ('Y', "Y", ""),
            ('Z', "Z", ""),
            ('-X', "-X", ""),
            ('-Y', "-Y", ""),
            ('-Z', "-Z", ""),
        ],
        default='-Z'
    ) # type: ignore
    
    export_axis_up: bpy.props.EnumProperty(
        name="上向轴",
        items=[
            ('X', "X", ""),
            ('Y', "Y", ""),
            ('Z', "Z", ""),
            ('-X', "-X", ""),
            ('-Y', "-Y", ""),
            ('-Z', "-Z", ""),
        ],
        default='Y'
    ) # type: ignore
    
    export_individual: bpy.props.BoolProperty(
        name="单独导出每个对象",
        description="为每个选中的对象创建单独的文件",
        default=False
    ) # type: ignore
    
    def draw(self, context):
        layout = self.layout
        
        box = layout.box()
        box.label(text="导出数据", icon='MESH_DATA')
        box.prop(self, "export_animations")
        box.prop(self, "export_armatures")
        box.prop(self, "export_morph")
        box.prop(self, "export_apply")
        
        box_transform = layout.box()
        box_transform.label(text="变换设置", icon='OBJECT_ORIGIN')
        box_transform.prop(self, "export_scale")
        row = box_transform.row()
        row.prop(self, "export_axis_forward")
        row.prop(self, "export_axis_up")
        
        box_batch = layout.box()
        box_batch.label(text="批量选项", icon='COLLECTION_NEW')
        box_batch.prop(self, "export_individual")
    
    def execute(self, context):
        selected_objects = [obj for obj in context.selected_objects if obj.type in ('MESH', 'ARMATURE')]
        
        if not selected_objects:
            self.report({'WARNING'}, "请选中要导出的网格或骨架对象！")
            return {'CANCELLED'}
        
        export_dir = os.path.dirname(self.filepath)
        
        export_kwargs = {
            'use_selection': True,
            'apply_scale_options': 'FBX_SCALE_ALL',
            'apply_unit_scale': True,
            'bake_anim': self.export_animations,
            'add_leaf_bones': False,
            'use_armature_deform_only': True,
            'use_mesh_modifiers': self.export_apply,
            'use_shape_key': self.export_morph,
            'axis_forward': self.export_axis_forward,
            'axis_up': self.export_axis_up,
            'global_scale': self.export_scale,
        }
        
        success_count = 0
        
        if self.export_individual:
            for obj in selected_objects:
                bpy.ops.object.select_all(action='DESELECT')
                obj.select_set(True)
                context.view_layer.objects.active = obj
                
                safe_name = "".join(c for c in obj.name if c.isalnum() or c in (' ', '-', '_')).strip()
                file_path = os.path.join(export_dir, f"{safe_name}.fbx")
                
                try:
                    bpy.ops.export_scene.fbx(filepath=file_path, **export_kwargs)
                    success_count += 1
                except Exception as e:
                    self.report({'WARNING'}, f"导出 {obj.name} 失败: {e}")
        else:
            try:
                bpy.ops.export_scene.fbx(filepath=self.filepath, **export_kwargs)
                success_count = len(selected_objects)
            except Exception as e:
                self.report({'ERROR'}, f"导出失败: {e}")
                return {'CANCELLED'}
        
        if self.export_individual:
            self.report({'INFO'}, f"成功导出 {success_count} 个文件到 {export_dir}")
        else:
            self.report({'INFO'}, f"成功导出 {success_count} 个对象")
        
        return {'FINISHED'}


def register():
    bpy.utils.register_class(EXPORT_OT_FBX_Batch)


def unregister():
    bpy.utils.unregister_class(EXPORT_OT_FBX_Batch)