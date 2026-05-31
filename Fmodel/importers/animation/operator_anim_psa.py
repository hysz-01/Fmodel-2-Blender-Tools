# FModel_Tools/Fmodel/importers/animation/operator_anim_psa.py
# PSA 动画导入 — 支持 PSK 配套动画格式

import bpy
import os
import tempfile
from bpy_extras.io_utils import ImportHelper


class ANIM_OT_ImportPSA(bpy.types.Operator, ImportHelper):
    """导入 PSA 动画"""
    bl_idname = "fmodel.import_anim_psa"
    bl_label = "导入 PSA 动画"
    bl_options = {'REGISTER', 'UNDO'}
    
    filename_ext = ".psa"
    filter_glob: bpy.props.StringProperty(default="*.psa", options={'HIDDEN'}) # type: ignore

    files: bpy.props.CollectionProperty(
        type=bpy.types.OperatorFileListElement,
        options={'HIDDEN', 'SKIP_SAVE'},
    ) # type: ignore
    directory: bpy.props.StringProperty(subtype='DIR_PATH') # type: ignore

    def create_safe_psa(self, original_path):
        """创建安全的 PSA 文件，修复 UTF-8 乱码问题"""
        try:
            with open(original_path, 'rb') as f:
                data = bytearray(f.read())
                
            offset = 0
            seq_names = []
            patched = False
            
            while offset + 44 <= len(data):
                chunk_name = data[offset:offset+32].split(b'\x00')[0].decode('ascii', errors='ignore')
                data_count = int.from_bytes(data[offset+36:offset+40], byteorder='little')
                data_size = int.from_bytes(data[offset+40:offset+44], byteorder='little')
                
                offset += 44
                if chunk_name == 'ANIMINFO':
                    for i in range(data_count):
                        seq_offset = offset + i * data_size
                        if seq_offset + 32 > len(data): break
                        
                        safe_name_str = f"Seq_{i}"
                        safe_name_bytes = safe_name_str.encode('ascii').ljust(32, b'\x00')
                        data[seq_offset:seq_offset+32] = safe_name_bytes
                        seq_names.append(safe_name_str)
                    
                    patched = True
                    break
                offset += data_count * data_size
                
            if patched:
                fd, temp_path = tempfile.mkstemp(suffix=".psa", prefix="fmodel_safe_")
                with os.fdopen(fd, 'wb') as f:
                    f.write(data)
                return temp_path, seq_names
                
        except Exception as e:
            print(f"二进制修补 PSA 失败: {e}")
            # 使用日志系统
            import logging
            logging.getLogger(__name__).error(f"二进制修补 PSA 失败: {e}")
            
        return original_path, []

    def execute(self, context):
        target_arm = context.active_object
        if not target_arm or target_arm.type != 'ARMATURE':
            self.report({'ERROR'}, "请先选中骨架本体 (Armature)")
            return {'CANCELLED'}

        import_paths = []
        if self.files and len(self.files) > 0:
            for file_elem in self.files:
                if file_elem.name:
                    import_paths.append(os.path.join(self.directory, file_elem.name))
        else:
            import_paths.append(self.filepath)

        if not import_paths:
            return {'CANCELLED'}

        success_count = 0
        existing_actions = set(bpy.data.actions)
        
        for path in import_paths:
            safe_path = os.path.normpath(path)
            true_basename = os.path.splitext(os.path.basename(safe_path))[0]
            
            temp_path, seq_names = self.create_safe_psa(safe_path)
            psa_kwargs = {'filepath': temp_path}
            
            try:
                # 根据参考插件 io_scene_psk_psa，正确的操作符是 psa.import_file 或 psa.import_all
                if hasattr(bpy.ops.psa, "import_file"):
                    bpy.ops.psa.import_file(**psa_kwargs)
                elif hasattr(bpy.ops.psa, "import_all"):
                    bpy.ops.psa.import_all(**psa_kwargs)
                else:
                    self.report({'ERROR'}, "未找到 PSA 导入命令 (需要 io_scene_psk_psa 插件)")
                    return {'CANCELLED'}
                
                new_actions = set(bpy.data.actions) - existing_actions
                for act in new_actions:
                    if act.name in seq_names or act.name.startswith("Seq_"):
                        act.name = true_basename
                
                existing_actions = set(bpy.data.actions)
                success_count += 1
                
            except Exception as e:
                self.report({'ERROR'}, f"PSA 导入失败 ({os.path.basename(safe_path)}): {e}")
            finally:
                if temp_path != safe_path and os.path.exists(temp_path):
                    try: os.remove(temp_path)
                    except: pass

        if success_count > 0:
            self.report({'INFO'}, f"成功加载 {success_count} 个 PSA 动画！")
        return {'FINISHED'}


def register():
    bpy.utils.register_class(ANIM_OT_ImportPSA)


def unregister():
    bpy.utils.unregister_class(ANIM_OT_ImportPSA)
