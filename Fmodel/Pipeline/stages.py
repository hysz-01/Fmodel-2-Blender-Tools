# FModel_Tools/Fmodel/Pipeline/stages.py
# 管线阶段 — 字典获取、格式转换、扫描、打包

import bpy
import os
import json
import time
import re
import hashlib
import shutil
from abc import ABC, abstractmethod

from ...core import (
    PipelineContext, PipelineStage, StageStatus, SourceType, ImportMode,
    DictionaryManifest, SkeletonNode, FolderNode, AnimationEntry,
    ImportedAssetCollection, ImportedAction, AssetLibraryManifest,
    CatalogEntry, LibraryAsset, get_or_create_catalog_uuid, ensure_dir
)


# ============================================================
# 抽象基类
# ============================================================

class PipelineStageBase(ABC):
    """管线阶段抽象基类"""
    
    @abstractmethod
    def get_stage_name(self) -> str:
        pass
    
    @abstractmethod
    def validate_input(self, context: PipelineContext) -> tuple[bool, str]:
        pass
    
    @abstractmethod
    def execute(self, context: PipelineContext) -> bool:
        pass
    
    def run(self, context: PipelineContext) -> bool:
        """运行阶段（带状态管理）"""
        stage_name = self.get_stage_name()
        
        valid, error_msg = self.validate_input(context)
        if not valid:
            context.set_stage_status(stage_name, StageStatus.FAILED.value)
            context.log_error(stage_name, f"输入验证失败: {error_msg}")
            return False
        
        context.set_stage_status(stage_name, StageStatus.RUNNING.value)
        context.log_info(stage_name, f"开始执行阶段: {stage_name}")
        
        try:
            success = self.execute(context)
            if success:
                context.set_stage_status(stage_name, StageStatus.COMPLETED.value)
            else:
                context.set_stage_status(stage_name, StageStatus.FAILED.value)
            return success
        except Exception as e:
            context.set_stage_status(stage_name, StageStatus.FAILED.value)
            context.log_error(stage_name, f"异常: {str(e)}")
            return False


# ============================================================
# 阶段1: 字典获取
# ============================================================

class DictionaryAcquisitionStage(PipelineStageBase):
    """字典获取阶段 - 扫描源数据，生成标准化的字典清单"""
    
    def get_stage_name(self) -> str:
        return PipelineStage.DICTIONARY_ACQUISITION.value
    
    def validate_input(self, context: PipelineContext) -> tuple[bool, str]:
        source_dir = context.get_config("source_dir", "")
        if not source_dir:
            return False, "未指定源目录"
        abs_source = bpy.path.abspath(source_dir)
        if not os.path.exists(abs_source):
            return False, f"源目录不存在: {abs_source}"
        return True, ""
    
    def execute(self, context: PipelineContext) -> bool:
        source_type = context.get_config("source_type", SourceType.UNITY_ANIM.value)
        source_dir = bpy.path.abspath(context.get_config("source_dir", ""))
        
        handlers = {
            SourceType.UNITY_ANIM.value: self._process_unity_anims,
            SourceType.FMODEL_UEANIM.value: self._process_fmodel_manifests,
            SourceType.FBX_BATCH.value: self._process_fbx_batch,
        }
        
        handler = handlers.get(source_type)
        if not handler:
            context.log_error(self.get_stage_name(), f"不支持的源类型: {source_type}")
            return False
        
        return handler(context, source_dir)
    
    def _process_unity_anims(self, context: PipelineContext, source_dir: str) -> bool:
        """处理Unity .anim文件"""
        manifest = DictionaryManifest(
            source_type=SourceType.UNITY_ANIM.value,
            source_path=source_dir
        )
        
        processed_count = 0
        skip_processed = context.get_config("unity_skip_processed", True)
        
        for root, dirs, files in os.walk(source_dir):
            dirs[:] = [d for d in dirs if not d.startswith('.')]
            
            for file in files:
                if not file.lower().endswith('.anim'):
                    continue
                
                file_path = os.path.join(root, file)
                original_name = os.path.splitext(file)[0]
                
                if skip_processed and re.search(r'_[a-f0-9]{8}$', original_name):
                    continue
                
                try:
                    with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                        content = f.read()
                except Exception as e:
                    context.log_warning(self.get_stage_name(), f"读取文件失败 {file_path}: {e}")
                    continue
                
                content_no_name = re.sub(r'^\s*m_Name:.*$', '', content, flags=re.MULTILINE)
                content_hash = hashlib.md5(content_no_name.encode('utf-8')).hexdigest()[:8]
                hashed_name = f"{original_name}_{content_hash}"
                
                rel_dir = os.path.relpath(root, source_dir).replace('\\', '/')
                if rel_dir == '.':
                    skel_name, catalog_path = "Generic", "Uncategorized"
                else:
                    parts = rel_dir.split('/')
                    skel_name = parts[0]
                    catalog_path = "/".join(parts[1:]) if len(parts) > 1 else "Base"
                
                if skel_name not in manifest.skeletons:
                    manifest.skeletons[skel_name] = SkeletonNode(name=skel_name)
                
                skel = manifest.skeletons[skel_name]
                folder = skel.get_or_create_folder(catalog_path)
                
                anim_entry = AnimationEntry(
                    original_name=original_name,
                    hashed_name=hashed_name,
                    source_file=file_path,
                    content_hash=content_hash
                )
                folder.add_animation(hashed_name, anim_entry)
                processed_count += 1
        
        if processed_count == 0:
            context.log_warning(self.get_stage_name(), "未找到需要处理的动画文件")
            return False
        
        context.dictionary_manifest = manifest.to_dict()
        context.log_info(self.get_stage_name(), f"成功处理 {processed_count} 个动画文件")
        return True
    
    def _process_fmodel_manifests(self, context: PipelineContext, source_dir: str) -> bool:
        """处理FModel manifest文件"""
        skeleton_filter = str(context.get_config("skeleton_filter", "") or "").strip()
        manifest = DictionaryManifest(
            source_type=SourceType.FMODEL_UEANIM.value,
            source_path=source_dir
        )
        
        processed_count = 0
        
        for f in os.listdir(source_dir):
            if not f.endswith("_manifest.json"):
                continue
            
            manifest_path = os.path.join(source_dir, f)
            try:
                with open(manifest_path, 'r', encoding='utf-8') as mf:
                    data = json.load(mf)
                
                for skel_name, folder_tree in data.items():
                    if skel_name == "__processed_sources__":
                        continue
                    if skeleton_filter and not self._skeleton_match(skel_name, skeleton_filter):
                        continue
                    
                    if skel_name not in manifest.skeletons:
                        manifest.skeletons[skel_name] = SkeletonNode(name=skel_name)
                    
                    self._merge_fmodel_tree(manifest.skeletons[skel_name], folder_tree, "")
                    processed_count += 1
            except Exception as e:
                context.log_warning(self.get_stage_name(), f"manifest解析失败 {manifest_path}: {e}")
                continue
        
        if processed_count == 0:
            context.log_info(self.get_stage_name(), "未找到manifest，回退为直接扫描.ueanim/.uepose")
            return self._process_fmodel_raw_files(context, source_dir)
        
        context.dictionary_manifest = manifest.to_dict()
        context.log_info(self.get_stage_name(), f"成功解析 {processed_count} 个manifest文件")
        return True

    def _process_fmodel_raw_files(self, context: PipelineContext, source_dir: str) -> bool:
        """处理FModel原始导出文件（.ueanim/.uepose + 同名json）"""
        from ...Assets.Utils.utils_asset import get_skeleton_name_from_json

        skeleton_filter = str(context.get_config("skeleton_filter", "") or "").strip()

        manifest = DictionaryManifest(
            source_type=SourceType.FMODEL_UEANIM.value,
            source_path=source_dir
        )

        processed_count = 0

        for root, dirs, files in os.walk(source_dir):
            dirs[:] = [d for d in dirs if not d.startswith('.')]

            for file in files:
                if not file.lower().endswith(('.ueanim', '.uepose')):
                    continue

                file_path = os.path.join(root, file)
                original_name = os.path.splitext(file)[0]

                json_path = os.path.join(root, f"{original_name}.json")
                skeleton_name = get_skeleton_name_from_json(json_path)

                if not skeleton_name:
                    rel_dir = os.path.relpath(root, source_dir).replace('\\', '/')
                    if rel_dir != '.':
                        skeleton_name = rel_dir.split('/')[0]

                if not skeleton_name:
                    skeleton_name = "Generic"

                if skeleton_filter and not self._skeleton_match(skeleton_name, skeleton_filter):
                    continue

                rel_dir = os.path.relpath(root, source_dir).replace('\\', '/')
                if rel_dir == '.':
                    folder_path = "Base"
                else:
                    parts = rel_dir.split('/')
                    folder_path = "/".join(parts[1:]) if len(parts) > 1 else "Base"

                if skeleton_name not in manifest.skeletons:
                    manifest.skeletons[skeleton_name] = SkeletonNode(name=skeleton_name)

                folder = manifest.skeletons[skeleton_name].get_or_create_folder(folder_path)
                anim_entry = AnimationEntry(
                    original_name=original_name,
                    hashed_name=original_name,
                    source_file=file_path,
                    content_hash="",
                    metadata={
                        "file_type": "ueanim" if file.lower().endswith('.ueanim') else "uepose",
                        "json_path": json_path if os.path.exists(json_path) else ""
                    }
                )
                folder.add_animation(original_name, anim_entry)
                processed_count += 1

        if processed_count == 0:
            context.log_warning(self.get_stage_name(), "未找到.ueanim/.uepose文件")
            return False

        context.dictionary_manifest = manifest.to_dict()
        context.log_info(self.get_stage_name(), f"成功扫描 {processed_count} 个FModel动画文件")
        return True

    def _skeleton_match(self, source_name: str, filter_name: str) -> bool:
        source = (source_name or "").strip().lower()
        target = (filter_name or "").strip().lower()
        if not source or not target:
            return True
        return source == target or source in target or target in source
    
    def _merge_fmodel_tree(self, skel: SkeletonNode, tree: dict, parent_path: str):
        """合并FModel树结构"""
        for key, value in tree.items():
            if key == "__actions__":
                continue
            
            current_path = f"{parent_path}/{key}" if parent_path else key
            folder = skel.get_or_create_folder(current_path)
            
            if isinstance(value, dict):
                if "__actions__" in value:
                    for action_data in value["__actions__"]:
                        if isinstance(action_data, list) and len(action_data) >= 1:
                            action_name = action_data[0]
                            anim_entry = AnimationEntry(
                                original_name=action_name,
                                hashed_name=action_name,
                                source_file="",
                                content_hash=""
                            )
                            folder.add_animation(action_name, anim_entry)
                
                subfolders = {k: v for k, v in value.items() if k != "__actions__" and isinstance(v, dict)}
                if subfolders:
                    self._merge_fmodel_tree(skel, subfolders, current_path)
    
    def _process_fbx_batch(self, context: PipelineContext, source_dir: str) -> bool:
        """处理批量FBX文件"""
        manifest = DictionaryManifest(
            source_type=SourceType.FBX_BATCH.value,
            source_path=source_dir
        )
        
        processed_count = 0
        
        for root, dirs, files in os.walk(source_dir):
            dirs[:] = [d for d in dirs if not d.startswith('.')]
            
            for file in files:
                if not file.lower().endswith(('.fbx', '.FBX')):
                    continue
                
                file_path = os.path.join(root, file)
                original_name = os.path.splitext(file)[0]
                
                rel_dir = os.path.relpath(root, source_dir).replace('\\', '/')
                skel_name = "Generic" if rel_dir == "." else rel_dir.split('/')[0]
                catalog_path = "Uncategorized" if rel_dir == "." else rel_dir
                
                if skel_name not in manifest.skeletons:
                    manifest.skeletons[skel_name] = SkeletonNode(name=skel_name)
                
                folder = manifest.skeletons[skel_name].get_or_create_folder(catalog_path)
                anim_entry = AnimationEntry(
                    original_name=original_name,
                    hashed_name=original_name,
                    source_file=file_path,
                    content_hash=""
                )
                folder.add_animation(original_name, anim_entry)
                processed_count += 1
        
        if processed_count == 0:
            context.log_warning(self.get_stage_name(), "未找到FBX文件")
            return False
        
        context.dictionary_manifest = manifest.to_dict()
        context.log_info(self.get_stage_name(), f"成功扫描 {processed_count} 个FBX文件")
        return True


# ============================================================
# 阶段2: 格式中转 (新增 - 统一差异化环节)
# ============================================================

class FormatConversionStage(PipelineStageBase):
    """格式中转阶段 - 根据源类型执行差异化的格式转换"""
    
    def get_stage_name(self) -> str:
        return PipelineStage.FORMAT_CONVERSION.value
    
    def validate_input(self, context: PipelineContext) -> tuple[bool, str]:
        if not context.dictionary_manifest:
            return False, "缺少字典清单数据"
        return True, ""
    
    def execute(self, context: PipelineContext) -> bool:
        source_type = context.get_config("source_type", SourceType.UNITY_ANIM.value)
        
        handlers = {
            SourceType.FMODEL_UEANIM.value: self._convert_ueformat,
            SourceType.UNITY_ANIM.value: self._convert_unity,
            SourceType.FBX_BATCH.value: self._convert_fbx,
        }
        
        handler = handlers.get(source_type, self._convert_default)
        return handler(context)
    
    def _convert_ueformat(self, context: PipelineContext) -> bool:
        """UEFormat格式中转 - 直接使用，无需转换"""
        context.log_info(self.get_stage_name(), "UEFormat格式无需中转，直接使用")
        return True
    
    def _convert_unity(self, context: PipelineContext) -> bool:
        """Unity格式中转 - 重命名.anim文件并准备FBX导入"""
        manifest = DictionaryManifest.from_dict(context.dictionary_manifest)
        source_dir = bpy.path.abspath(context.get_config("source_dir", ""))
        output_dir = bpy.path.abspath(context.get_config("output_dir", ""))
        
        if not output_dir:
            output_dir = os.path.join(source_dir, "_converted")
            ensure_dir(output_dir)
        
        converted_count = 0
        conversion_manifest = {"converted_files": []}
        
        for skel_name, skel_node in manifest.skeletons.items():
            for folder_path, folder_node in skel_node.folders.items():
                for anim_name, anim_entry in folder_node.animations.items():
                    source_file = anim_entry.source_file
                    if not os.path.exists(source_file):
                        continue
                    
                    try:
                        # 重命名文件（添加hash后缀）
                        new_name = anim_entry.hashed_name
                        new_path = os.path.join(
                            output_dir,
                            skel_name,
                            folder_path if folder_path else "",
                            f"{new_name}.anim"
                        )
                        ensure_dir(os.path.dirname(new_path))
                        shutil.copy2(source_file, new_path)
                        
                        conversion_manifest["converted_files"].append({
                            "original": source_file,
                            "converted": new_path,
                            "skel_name": skel_name,
                            "folder_path": folder_path,
                            "anim_name": anim_name
                        })
                        converted_count += 1
                    except Exception as e:
                        context.log_warning(self.get_stage_name(), f"转换失败: {anim_name} - {e}")
        
        # 保存转换清单
        manifest_path = os.path.join(output_dir, "conversion_manifest.json")
        with open(manifest_path, 'w', encoding='utf-8') as f:
            json.dump(conversion_manifest, f, ensure_ascii=False, indent=2)
        
        context.conversion_manifest = conversion_manifest
        context.log_info(self.get_stage_name(), f"成功转换 {converted_count} 个文件")
        return converted_count > 0
    
    def _convert_fbx(self, context: PipelineContext) -> bool:
        """FBX格式中转 - 直接使用，无需转换"""
        context.log_info(self.get_stage_name(), "FBX格式无需中转，直接使用")
        return True
    
    def _convert_default(self, context: PipelineContext) -> bool:
        """默认中转处理"""
        context.log_info(self.get_stage_name(), "未知格式，跳过中转")
        return True


# ============================================================
# 阶段3: 资源导入
# ============================================================

class AssetImportStage(PipelineStageBase):
    """资源导入阶段 - 根据字典将资源导入Blender"""
    
    def get_stage_name(self) -> str:
        return PipelineStage.ASSET_IMPORT.value
    
    def validate_input(self, context: PipelineContext) -> tuple[bool, str]:
        if not context.dictionary_manifest:
            return False, "缺少字典清单数据"
        return True, ""
    
    def execute(self, context: PipelineContext) -> bool:
        import_mode = context.get_config("import_mode", ImportMode.FBX_MATCH.value)
        
        handlers = {
            ImportMode.FBX_MATCH.value: self._import_fbx_match,
            ImportMode.UEANIM_DIRECT.value: self._import_ueanim_direct,
            ImportMode.LINK_EXISTING.value: self._import_link_existing,
        }
        
        handler = handlers.get(import_mode)
        if not handler:
            context.log_error(self.get_stage_name(), f"不支持的导入模式: {import_mode}")
            return False
        
        return handler(context)
    
    def _import_fbx_match(self, context: PipelineContext) -> bool:
        """匹配已导入的FBX动画"""
        manifest = DictionaryManifest.from_dict(context.dictionary_manifest)
        collection = ImportedAssetCollection(import_mode=ImportMode.FBX_MATCH.value)
        
        all_actions = list(bpy.data.actions)
        matched_count = 0
        
        for skel, folder_path, anim_name, anim_entry in manifest.get_all_animations():
            hashed_name = anim_entry.hashed_name
            
            target_action = None
            for action in all_actions:
                if hashed_name.lower() in action.name.lower():
                    target_action = action
                    break
            
            if target_action:
                imported = ImportedAction(
                    action_name=target_action.name,
                    source_manifest_ref=f"{skel}/{folder_path}/{anim_name}",
                    import_status="success",
                    frame_range=tuple(target_action.frame_range) if target_action.frame_range else (0, 0)
                )
                collection.imported_actions.append(imported)
                matched_count += 1
            else:
                collection.failed_imports.append({
                    "source_file": anim_entry.source_file,
                    "error": "未找到匹配的动作",
                    "expected_name": hashed_name
                })
        
        context.imported_assets = collection.to_dict()
        context.log_info(self.get_stage_name(), f"成功匹配 {matched_count} 个动作")
        return matched_count > 0
    
    def _import_ueanim_direct(self, context: PipelineContext) -> bool:
        """直接导入.ueanim文件"""
        try:
            from ..importers.animation.operator_anim_ueformat import get_ueformat_api
            UEFormatImport, _, UEAnimOptions, _ = get_ueformat_api()
            if not UEFormatImport:
                context.log_error(self.get_stage_name(), "无法加载UEFormat API")
                return False
        except Exception as e:
            context.log_error(self.get_stage_name(), f"导入UEFormat模块失败: {e}")
            return False
        
        manifest = DictionaryManifest.from_dict(context.dictionary_manifest)
        collection = ImportedAssetCollection(import_mode=ImportMode.UEANIM_DIRECT.value)
        
        target_arm = None
        target_arm_name = context.get_config("target_armature", "")
        if target_arm_name:
            obj = bpy.data.objects.get(target_arm_name)
            if obj and obj.type == 'ARMATURE':
                target_arm = obj

        target_skeleton_name = ""
        if target_arm:
            target_skeleton_name = target_arm.get("FModel_Skeleton", target_arm.name)

        try:
            options = UEAnimOptions(
                scale_factor=context.get_config("import_scale", 0.01),
                rotation_only=context.get_config("rotation_only", False),
                import_curves=context.get_config("import_curves", False),
                override_skeleton=target_arm
            )
        except TypeError:
            options = UEAnimOptions(
                scale_factor=context.get_config("import_scale", 0.01),
                rotation_only=context.get_config("rotation_only", False),
                import_curves=context.get_config("import_curves", False)
            )
        importer = UEFormatImport(options)
        
        def _write_failure_report():
            if not collection.failed_imports:
                return ""
            output_dir = bpy.path.abspath(context.get_config("output_dir", ""))
            if not output_dir:
                return ""
            os.makedirs(output_dir, exist_ok=True)
            tmp_dir = os.path.join(output_dir, "_pipeline_tmp")
            os.makedirs(tmp_dir, exist_ok=True)
            ts = time.strftime("%Y%m%d_%H%M%S")
            report_path = os.path.join(tmp_dir, f"import_failures_{ts}.json")
            try:
                payload = {
                    "stage": self.get_stage_name(),
                    "failed_count": len(collection.failed_imports),
                    "failures": collection.failed_imports,
                }
                with open(report_path, 'w', encoding='utf-8') as f:
                    json.dump(payload, f, ensure_ascii=False, indent=2)
                return report_path
            except Exception:
                return ""

        valid_entries = []
        for skel, folder_path, anim_name, anim_entry in manifest.get_all_animations():
            source_file = anim_entry.source_file
            if not source_file or not os.path.exists(source_file):
                continue
            if not source_file.lower().endswith('.ueanim'):
                continue
            valid_entries.append((skel, folder_path, anim_name, source_file))

        if not valid_entries:
            context.log_warning(self.get_stage_name(), "没有可导入的.ueanim文件")
            context.imported_assets = collection.to_dict()
            return False

        resume_enabled = bool(context.get_config("import_resume_enabled", True))
        checkpoint = context.get_config("import_checkpoint", {}) if resume_enabled else {}
        if not isinstance(checkpoint, dict):
            checkpoint = {}

        batch_size = max(1, int(context.get_config("import_batch_size", 300)))
        max_cycles = max(1, int(context.get_config("max_import_cycles", 200)))
        max_consecutive_failures = max(20, int(context.get_config("max_consecutive_failures", 120)))
        large_threshold = max(1, int(context.get_config("large_import_threshold", 2000)))
        if len(valid_entries) >= large_threshold and batch_size > 120:
            old_size = batch_size
            batch_size = 120
            context.log_warning(
                self.get_stage_name(),
                f"检测到巨量导入({len(valid_entries)}). 自动降批次: {old_size} -> {batch_size}"
            )

        min_batch = max(10, batch_size // 4)
        max_batch = max(batch_size, batch_size * 4)

        imported_count = 0
        cycle_count = 0
        consecutive_failures = 0
        old_actions = set(bpy.data.actions)

        if resume_enabled and checkpoint:
            try:
                cursor = int(checkpoint.get("cursor", 0))
                cycle_count = int(checkpoint.get("cycle_count", 0))
                staged = checkpoint.get("imported_actions", [])
                fails = checkpoint.get("failed_imports", [])
                if staged:
                    staged_col = ImportedAssetCollection.from_dict({
                        "import_mode": ImportMode.UEANIM_DIRECT.value,
                        "imported_actions": staged,
                        "failed_imports": fails,
                    })
                    collection.imported_actions.extend(staged_col.imported_actions)
                    collection.failed_imports.extend(staged_col.failed_imports)
                context.log_info(self.get_stage_name(), f"断点恢复: cursor={cursor}, staged={len(collection.imported_actions)}")
            except Exception as e:
                cursor = 0
                context.log_warning(self.get_stage_name(), f"断点恢复解析失败，回退全量: {e}")
        else:
            cursor = 0

        def _flush_actions_to_temp_blend(skel_name: str):
            if not collection.imported_actions:
                return
            chunk_actions = []
            chunk_entries = []
            for ia in collection.imported_actions:
                if ia.import_status != "success":
                    continue
                act = bpy.data.actions.get(ia.action_name)
                if act:
                    chunk_actions.append(act)
                    chunk_entries.append(ia)
            if not chunk_actions:
                return

            output_dir = bpy.path.abspath(context.get_config("output_dir", ""))
            if not output_dir:
                return
            os.makedirs(output_dir, exist_ok=True)
            temp_dir = os.path.join(output_dir, "_pipeline_tmp")
            os.makedirs(temp_dir, exist_ok=True)
            chunk_index = cycle_count
            temp_blend = os.path.join(temp_dir, f"{skel_name}_chunk_{chunk_index:04d}.blend")

            bpy.data.libraries.write(filepath=temp_blend, datablocks=set(chunk_actions), fake_user=True)
            context.log_info(
                self.get_stage_name(),
                f"动作分块落盘: {os.path.basename(temp_blend)} ({len(chunk_actions)} actions)"
            )

            staged_entries = []
            for ia in chunk_entries:
                staged_entries.append(ImportedAction(
                    action_name=ia.action_name,
                    source_manifest_ref=ia.source_manifest_ref,
                    source_file=ia.source_file,
                    staged_blend=temp_blend,
                    import_status="staged",
                    frame_range=ia.frame_range,
                ))

            for act in chunk_actions:
                try:
                    bpy.data.actions.remove(act)
                except Exception:
                    collection.imported_actions = [
                ia for ia in collection.imported_actions
                if ia.import_status != "success"
            ]
            collection.imported_actions.extend(staged_entries)

        total_entries = len(valid_entries)
        aborted_by_failures = False
        while cursor < total_entries:
            batch = valid_entries[cursor:cursor + batch_size]
            cycle_count += 1
            if cycle_count > max_cycles:
                context.log_error(self.get_stage_name(), f"超过最大导入循环次数: {max_cycles}")
                break

            cycle_start = time.perf_counter()
            batch_success = 0
            batch_failed = 0

            for skel, folder_path, anim_name, source_file in batch:
                try:
                    importer.import_file(os.path.normpath(source_file))
                    new_actions = set(bpy.data.actions) - old_actions

                    if new_actions:
                        action = list(new_actions)[0]
                        action["Pipeline_Source"] = source_file
                        if target_skeleton_name:
                            action["Pipeline_Skeleton"] = target_skeleton_name
                        imported = ImportedAction(
                            action_name=action.name,
                            source_manifest_ref=f"{skel}/{folder_path}/{anim_name}",
                            source_file=source_file,
                            import_status="success",
                            frame_range=tuple(action.frame_range) if action.frame_range else (0, 0)
                        )
                        collection.imported_actions.append(imported)
                        old_actions = set(bpy.data.actions)
                        imported_count += 1
                        batch_success += 1
                        consecutive_failures = 0
                    else:
                        batch_failed += 1
                        consecutive_failures += 1
                        collection.failed_imports.append({
                            "source_file": source_file,
                            "error": "导入后未检测到新动作"
                        })
                except Exception as e:
                    collection.failed_imports.append({"source_file": source_file, "error": str(e)})
                    batch_failed += 1
                    consecutive_failures += 1

                if consecutive_failures >= max_consecutive_failures:
                    context.log_error(
                        self.get_stage_name(),
                        f"连续失败达到阈值({max_consecutive_failures})，提前中止导入"
                    )
                    aborted_by_failures = True
                    break

            if consecutive_failures >= max_consecutive_failures:
                break

            if resume_enabled:
                context.set_config("import_checkpoint", {
                    "cursor": cursor + len(batch),
                    "cycle_count": cycle_count,
                    "imported_actions": [a.__dict__ for a in collection.imported_actions],
                    "failed_imports": collection.failed_imports,
                })

            # 内存保护：每批次导入后落地并卸载动作，防止巨量动作常驻内存
            _flush_actions_to_temp_blend(target_skeleton_name or "Generic")

            cycle_cost = time.perf_counter() - cycle_start
            fail_ratio = (batch_failed / len(batch)) if batch else 0.0

            context.log_info(
                self.get_stage_name(),
                (
                    f"批次 {cycle_count}: "
                    f"范围[{cursor}-{cursor + len(batch) - 1}] "
                    f"成功 {batch_success} 失败 {batch_failed} "
                    f"耗时 {cycle_cost:.2f}s "
                    f"batch={batch_size}"
                )
            )

            # 自适应批次大小：慢批/高失败率降速，快批低失败率增速
            if fail_ratio > 0.25 or cycle_cost > 8.0:
                batch_size = max(min_batch, int(batch_size * 0.75))
            elif fail_ratio < 0.05 and cycle_cost < 2.5:
                batch_size = min(max_batch, int(batch_size * 1.2))

            cursor += len(batch)

            # 让Blender主线程有机会处理UI与事件，降低卡死感
            try:
                bpy.ops.wm.redraw_timer(type='DRAW_WIN_SWAP', iterations=1)
            except Exception:
                context.imported_assets = collection.to_dict()
        if resume_enabled:
            context.set_config("import_checkpoint", {})
        if collection.failed_imports:
            report_path = _write_failure_report()
            if report_path:
                context.log_warning(self.get_stage_name(), f"失败报告已导出: {report_path}")
        context.log_info(
            self.get_stage_name(),
            f"成功导入 {imported_count} 个动画，累计失败 {len(collection.failed_imports)}"
        )
        if aborted_by_failures:
            return False
        return imported_count > 0
    
    def _import_link_existing(self, context: PipelineContext) -> bool:
        """链接现有资产库"""
        collection = ImportedAssetCollection(import_mode=ImportMode.LINK_EXISTING.value)
        
        source_dir = bpy.path.abspath(context.get_config("source_dir", ""))
        if not source_dir or not os.path.exists(source_dir):
            context.log_error(self.get_stage_name(), "源目录无效")
            return False
        
        blend_files = [f for f in os.listdir(source_dir) if f.endswith('.blend')]
        if not blend_files:
            context.log_warning(self.get_stage_name(), "未找到blend文件")
            return False
        
        imported_count = 0
        for blend_file in blend_files:
            blend_path = os.path.join(source_dir, blend_file)
            try:
                with bpy.data.libraries.load(blend_path, link=True) as (data_from, data_to):
                    data_to.actions = data_from.actions
                for action in data_to.actions:
                    if action:
                        imported = ImportedAction(
                            action_name=action.name,
                            source_manifest_ref="",
                            import_status="success",
                            frame_range=tuple(action.frame_range) if action.frame_range else (0, 0)
                        )
                        collection.imported_actions.append(imported)
                        imported_count += 1
            except Exception as e:
                collection.failed_imports.append({"source_file": blend_path, "error": str(e)})
        
        context.imported_assets = collection.to_dict()
        context.log_info(self.get_stage_name(), f"成功链接 {imported_count} 个动作")
        return imported_count > 0


# ============================================================
# 阶段3: 建立资产库
# ============================================================

class LibraryBuildingStage(PipelineStageBase):
    """建立资产库阶段 - 标记资产、分配目录、生成清单、保存库文件"""
    
    def get_stage_name(self) -> str:
        return PipelineStage.LIBRARY_BUILDING.value
    
    def validate_input(self, context: PipelineContext) -> tuple[bool, str]:
        if not context.imported_assets:
            return False, "缺少导入资产数据"
        if not context.dictionary_manifest:
            return False, "缺少字典清单数据"
        return True, ""
    
    def execute(self, context: PipelineContext) -> bool:
        from ...Assets.Utils import utils_asset
        
        output_dir = bpy.path.abspath(context.get_config("output_dir", ""))
        library_name = context.get_config("library_name", "Asset_Library")
        
        if not output_dir:
            context.log_error(self.get_stage_name(), "未指定输出目录")
            return False
        
        if not ensure_dir(output_dir):
            context.log_error(self.get_stage_name(), "创建输出目录失败")
            return False
        
        # Reload actions from existing library blends (they may have been removed after first bake)
        self._reload_actions_from_blends(output_dir, library_name)
        
        manifest = AssetLibraryManifest(library_name=library_name, library_path=output_dir)
        imported_actions = context.imported_assets.get("imported_actions", [])
        print(f"[FModel DEBUG] LibraryBuilding: output_dir={output_dir}, actions={len(imported_actions)}")
        source_dir = bpy.path.abspath(context.get_config("source_dir", ""))
        chunk_size = max(1, int(context.get_config("chunk_size", 500)))
        force_rebuild = bool(context.get_config("force_rebuild", False))
        generate_thumbnails = bool(context.get_config("generate_thumbnails", True))
        thumb_resolution = str(context.get_config("thumb_resolution", "256"))
        
        skeleton_groups = {}
        
        for imp_action in imported_actions:
            ref = imp_action.get("source_manifest_ref", "")
            if "/" in ref:
                skel_name = ref.split("/")[0]
                if skel_name not in skeleton_groups:
                    skeleton_groups[skel_name] = []
                skeleton_groups[skel_name].append(imp_action)
        
        generated_actions = []
        success_count = 0
        
        for skel_name, actions in skeleton_groups.items():
            base_name = f"{library_name}_{skel_name}"
            existing_sources = set()
            next_vol_index = 1

            if force_rebuild:
                for f in os.listdir(output_dir):
                    if f.startswith(base_name) and (f.endswith(".blend") or f.endswith(".json")):
                        try:
                            os.remove(os.path.join(output_dir, f))
                        except Exception:
                            pass
            else:
                for f in os.listdir(output_dir):
                    if not (f.startswith(base_name) and f.endswith("_manifest.json")):
                        continue
                    vol_str = f.replace(base_name, "").replace("_manifest.json", "").replace("_Vol_", "")
                    if vol_str.isdigit():
                        next_vol_index = max(next_vol_index, int(vol_str) + 1)
                    elif f == f"{base_name}_manifest.json":
                        next_vol_index = max(next_vol_index, 2)

                    try:
                        with open(os.path.join(output_dir, f), 'r', encoding='utf-8') as mf:
                            old_manifest = json.load(mf)
                            existing_sources.update(old_manifest.get("__processed_sources__", []))
                    except Exception:
                        pending_entries = []
            for imp_action in actions:
                action_name = imp_action["action_name"]
                action = bpy.data.actions.get(action_name)
                staged_blend = imp_action.get("staged_blend", "")
                if not action and staged_blend and os.path.exists(staged_blend):
                    try:
                        with bpy.data.libraries.load(staged_blend, link=False) as (df, dt):
                            if action_name in df.actions:
                                dt.actions = [action_name]
                        action = bpy.data.actions.get(action_name)
                    except Exception as e:
                        context.log_warning(self.get_stage_name(), f"加载暂存动作失败 {action_name}: {e}")
                if not action:
                    continue

                source_ref = imp_action.get("source_manifest_ref", "") or action_name
                source_path = action.get("Pipeline_Source", "")
                source_key = source_ref
                if source_path and source_dir:
                    try:
                        source_key = os.path.relpath(source_path, source_dir).replace('\\', '/')
                    except Exception:
                        source_key = source_ref
                if not force_rebuild and source_key in existing_sources:
                    continue

                pending_entries.append((imp_action, action, source_key))

            if not pending_entries:
                continue

            chunks = [pending_entries[i:i + chunk_size] for i in range(0, len(pending_entries), chunk_size)]

            for chunk_idx, chunk_entries in enumerate(chunks):
                current_vol = next_vol_index + chunk_idx
                vol_suffix = f"_Vol_{current_vol}" if current_vol > 1 else ""
                blend_file_name = f"{base_name}{vol_suffix}.blend"
                blend_path = os.path.join(output_dir, blend_file_name)
                if blend_file_name not in manifest.blend_files:
                    manifest.blend_files.append(blend_file_name)

                chunk_manifest = {"__processed_sources__": [], skel_name: {}}
                arm_obj = self._find_skeleton_object(skel_name)

                for imp_action, action, source_key in chunk_entries:
                    ref = imp_action.get("source_manifest_ref", "")
                    parts = ref.split("/") if ref else []
                    catalog_path = "/".join(parts[1:-1]) if len(parts) > 2 else "Uncategorized"
                    rel_thumb_path = ""

                    if not action.asset_data:
                        action.asset_mark()

                    catalog_uuid = get_or_create_catalog_uuid(output_dir, catalog_path, skel_name)
                    action.asset_data.catalog_id = catalog_uuid
                    action["SA_Group"] = skel_name
                    action["SA_Folder"] = catalog_path

                    if generate_thumbnails and arm_obj:
                        try:
                            rel_thumb_path = utils_asset.bake_thumbnail_opengl(
                                arm_obj, action, output_dir, skel_name,
                                resolution=thumb_resolution,
                                quality=context.get_config("thumb_quality", "OPENGL"),
                                isolate=context.get_config("thumb_isolate", True),
                            )
                        except Exception as e:
                            rel_thumb_path = ""
                            import traceback
                            traceback.print_exc()

                    catalog_entry = next(
                        (c for c in manifest.catalog_entries if c.path == f"{skel_name}/{catalog_path}"),
                        None
                    )
                    if not catalog_entry:
                        catalog_entry = CatalogEntry(uuid=catalog_uuid, path=f"{skel_name}/{catalog_path}", action_count=0)
                        manifest.catalog_entries.append(catalog_entry)
                    catalog_entry.action_count += 1

                    manifest.assets.append(LibraryAsset(
                        action_name=action.name,
                        catalog_id=catalog_uuid,
                        blend_file=blend_file_name,
                        thumbnail_path=rel_thumb_path
                    ))

                    current_level = chunk_manifest[skel_name]
                    for part in [p for p in catalog_path.split('/') if p]:
                        if part not in current_level:
                            current_level[part] = {}
                        current_level = current_level[part]
                    if "__actions__" not in current_level:
                        current_level["__actions__"] = []
                    current_level["__actions__"].append([action.name, rel_thumb_path])
                    chunk_manifest["__processed_sources__"].append(source_key)

                    generated_actions.append(action)
                    success_count += 1

                if not generated_actions:
                    continue

                try:
                    bpy.data.libraries.write(filepath=blend_path, datablocks=set(generated_actions), fake_user=True)
                    for act in generated_actions:
                        bpy.data.actions.remove(act)
                    generated_actions.clear()
                except Exception as e:
                    context.log_error(self.get_stage_name(), f"保存blend文件失败: {e}")
                    generated_actions.clear()
                    continue

                chunk_manifest_path = os.path.join(output_dir, f"{base_name}{vol_suffix}_manifest.json")
                try:
                    with open(chunk_manifest_path, 'w', encoding='utf-8') as f:
                        json.dump(chunk_manifest, f, ensure_ascii=False, indent=4)
                except Exception as e:
                    context.log_warning(self.get_stage_name(), f"保存分卷manifest失败: {e}")
        
        manifest_path = os.path.join(output_dir, f"{library_name}_manifest.json")
        manifest.save_to_file(manifest_path)

        # 清理导入阶段产生的临时分块文件
        tmp_dir = os.path.join(output_dir, "_pipeline_tmp")
        if os.path.isdir(tmp_dir):
            for f in os.listdir(tmp_dir):
                if f.endswith('.blend'):
                    try:
                        os.remove(os.path.join(tmp_dir, f))
                    except Exception:
                        pass
            try:
                if not os.listdir(tmp_dir):
                    os.rmdir(tmp_dir)
            except Exception:
                pass
        
        context.library_manifest = manifest.to_dict()
        context.log_info(self.get_stage_name(), f"成功构建资产库，包含 {success_count} 个动作")
        return len(imported_actions) > 0  # success if we had actions to process (even if all already done)

    def _reload_actions_from_blends(self, output_dir: str, library_name: str):
        """从已有库文件恢复动作到 bpy.data，用于重烘焙"""
        if not os.path.isdir(output_dir):
            return
        for f in sorted(os.listdir(output_dir)):
            if not f.startswith(library_name) or not f.endswith(".blend"):
                continue
            blend_path = os.path.join(output_dir, f)
            try:
                with bpy.data.libraries.load(blend_path, link=False) as (df, dt):
                    for an in df.actions:
                        if an not in bpy.data.actions:
                            dt.actions.append(an)
            except Exception:
                pass

    def _find_skeleton_object(self, skeleton_name: str):
        for obj in bpy.data.objects:
            if obj.type != 'ARMATURE':
                continue
            sk = obj.get("FModel_Skeleton", obj.name)
            if sk == skeleton_name:
                return obj
        for obj in bpy.data.objects:
            if obj.type != 'ARMATURE':
                continue
            sk = obj.get("FModel_Skeleton", obj.name)
            if sk.lower() in skeleton_name.lower() or skeleton_name.lower() in sk.lower():
                return obj
        return None


# ============================================================
# 阶段4: 完成
# ============================================================

class FinalizationStage(PipelineStageBase):
    """完成阶段 - 动态挂载资产库、扫描动画、更新UI"""
    
    def get_stage_name(self) -> str:
        return PipelineStage.FINALIZATION.value
    
    def validate_input(self, context: PipelineContext) -> tuple[bool, str]:
        if not context.library_manifest:
            return False, "缺少资产库清单数据"
        return True, ""
    
    def execute(self, context: PipelineContext) -> bool:
        from ...core.utils import mount_dynamic_library
        
        manifest_data = context.library_manifest
        library_name = manifest_data.get("library_name", "")
        library_path = manifest_data.get("library_path", "")
        
        if not library_path or not os.path.exists(library_path):
            context.log_error(self.get_stage_name(), "资产库路径无效")
            return False
        
        try:
            mount_dynamic_library(library_name, library_path)
            context.log_info(self.get_stage_name(), f"已挂载资产库: {library_name}")
        except Exception as e:
            context.log_error(self.get_stage_name(), f"挂载资产库失败: {e}")
            return False
        
        scene = bpy.context.scene if bpy.context else None
        if scene and hasattr(scene, "fmodel_assets"):
            props = scene.fmodel_assets
            already_linked = any(lib.name == library_name for lib in props.project_libs)
            if not already_linked:
                new_lib = props.project_libs.add()
                new_lib.name = library_name
                new_lib.path = library_path
        
        try:
            if hasattr(bpy.ops.fmodel, "scan_anims"):
                bpy.ops.fmodel.scan_anims()
                context.log_info(self.get_stage_name(), "动画扫描完成")
            else:
                context.log_warning(self.get_stage_name(), "scan_anims 操作符未注册，跳过扫描")
        except Exception as e:
            context.log_warning(self.get_stage_name(), f"动画扫描失败: {e}")
            import traceback
            traceback.print_exc()
        
        context.status = StageStatus.COMPLETED.value
        context.log_info(self.get_stage_name(), "管线流程完成")
        return True


# ============================================================
# 注册
# ============================================================

def register():
    pass

def unregister():
    pass
