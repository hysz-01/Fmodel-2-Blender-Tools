import bpy

from ..manager import PipelineManager
from ....core import PipelineConfig, PipelineContext, SourceType, ImportMode


def _load_or_create_context(config_dict: dict) -> PipelineContext:
    context_data = PipelineContext.load_from_blender_text()
    if context_data:
        context_data.config.update(config_dict)
        return context_data
    return PipelineContext(config=config_dict)


def _build_config_from_wizard(state, context) -> dict:
    source_type = SourceType.FMODEL_UEANIM.value if state.flow_type == 'FMODEL' else SourceType.UNITY_ANIM.value
    import_mode = ImportMode.UEANIM_DIRECT.value if state.flow_type == 'FMODEL' else ImportMode.FBX_MATCH.value

    cfg = PipelineConfig(
        source_dir=state.source_dir,
        output_dir=state.output_dir,
        library_name=state.library_name,
        skeleton_filter=state.skeleton_filter,
        source_type=source_type,
        import_mode=import_mode,
        import_scale=state.import_scale,
        rotation_only=state.rotation_only,
        import_curves=state.import_curves,
        generate_thumbnails=state.lib_generate_thumbnails,
        thumb_resolution=state.lib_thumb_resolution,
        thumb_quality=state.lib_thumb_quality,
        thumb_isolate=state.lib_thumb_isolate,
        chunk_size=state.lib_chunk_size,
        force_rebuild=state.lib_force_rebuild,
        import_batch_size=state.import_batch_size,
        max_import_cycles=state.import_max_cycles,
        large_import_threshold=state.import_large_threshold,
        max_consecutive_failures=state.import_max_consecutive_failures,
        import_resume_enabled=state.import_resume_enabled,
    ).to_dict()

    obj = context.active_object
    if obj and obj.type == 'ARMATURE':
        cfg["target_armature"] = obj.name

    return cfg


def run_wizard_stage(context, state, stage_name: str) -> bool:
    cfg = _build_config_from_wizard(state, context)
    manager = PipelineManager()
    pipeline_context = _load_or_create_context(cfg)
    success = manager.run_stage(pipeline_context, stage_name)
    pipeline_context.save_to_blender_text()
    return success
