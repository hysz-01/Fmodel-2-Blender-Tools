# FModel_Tools/Fmodel/importers/export/operator_export_gltf.py
# glTF 批量导出 — 支持批量导出选中对象

import bpy
import os
from bpy_extras.io_utils import ExportHelper


class EXPORT_OT_GLTF_Batch(bpy.types.Operator, ExportHelper):
    """批量导出选中对象为 glTF 文件"""
    bl_idname = "fmodel.export_gltf_batch"
    bl_label = "批量导出 glTF"
    bl_options = {'REGISTER', 'UNDO'}
    
    filename_ext = ".glb"
    filter_glob: bpy.props.StringProperty(default="*.glb;*.gltf", options={'HIDDEN'}) # type: ignore
    
    export_format: bpy.props.EnumProperty(
        name="格式",
        items=[
            ('GLB', "glTF Binary (.glb)", "单文件格式"),
            ('GLTF_SEPARATE', "glTF Separate (.gltf + .bin)", "分离格式"),
        ],
        default='GLB'
    ) # type: ignore
    
    export_animations: bpy.props.BoolProperty(
        name="导出动画",
        description="导出物体的动画数据",
        default=True
    ) # type: ignore
    
    export_skins: bpy.props.BoolProperty(
        name="导出蒙皮",
        description="导出骨架和蒙皮数据",
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
    
    export_yup: bpy.props.BoolProperty(
        name="Y 轴向上",
        description="使用 Y 轴作为向上方向（UE 标准）",
        default=True
    ) # type: ignore
    
    export_individual: bpy.props.BoolProperty(
        name="单独导出每个对象",
        description="为每个选中的对象创建单独的文件",
        default=False
    ) # type: ignore
    
    def draw(self, context):
        layout = self.layout
        
        box = layout.box()
        box.label(text="导出格式", icon='FILE_FOLDER')
        box.prop(self, "export_format", expand=True)
        
        box_data = layout.box()
        box_data.label(text="导出数据", icon='MESH_DATA')
        box_data.prop(self, "export_animations")
        box_data.prop(self, "export_skins")
        box_data.prop(self, "export_morph")
        box_data.prop(self, "export_apply")
        box_data.prop(self, "export_yup")
        
        box_batch = layout.box()
        box_batch.label(text="批量选项", icon='COLLECTION_NEW')
        box_batch.prop(self, "export_individual")
    
    def execute(self, context):
        selected_objects = [obj for obj in context.selected_objects if obj.type in ('MESH', 'ARMATURE')]
        
        if not selected_objects:
            self.report({'WARNING'}, "请选中要导出的网格或骨架对象！")
            return {'CANCELLED'}
        
        export_dir = os.path.dirname(self.filepath)
        base_name = os.path.splitext(os.path.basename(self.filepath))[0]
        
        export_kwargs = {
            'export_format': self.export_format,
            'export_animations': self.export_animations,
            'export_skins': self.export_skins,
            'export_morph': self.export_morph,
            'export_apply': self.export_apply,
            'export_yup': self.export_yup,
        }
        
        success_count = 0
        
        if self.export_individual:
            for obj in selected_objects:
                bpy.ops.object.select_all(action='DESELECT')
                obj.select_set(True)
                context.view_layer.objects.active = obj
                
                safe_name = "".join(c for c in obj.name if c.isalnum() or c in (' ', '-', '_')).strip()
                file_path = os.path.join(export_dir, f"{safe_name}.glb")
                
                try:
                    bpy.ops.export_scene.gltf(filepath=file_path, use_selection=True, **export_kwargs)
                    success_count += 1
                except Exception as e:
                    self.report({'WARNING'}, f"导出 {obj.name} 失败: {e}")
        else:
            try:
                bpy.ops.export_scene.gltf(filepath=self.filepath, use_selection=True, **export_kwargs)
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
    bpy.utils.register_class(EXPORT_OT_GLTF_Batch)


def unregister():
    bpy.utils.unregister_class(EXPORT_OT_GLTF_Batch)