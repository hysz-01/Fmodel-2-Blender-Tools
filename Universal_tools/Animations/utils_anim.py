# FModel_Tools/Universal_tools/Animations/utils_anim.py
# 动画工具函数 — 帧范围、Action 辅助

import bpy
from mathutils import Matrix
import re

def safe_invert(m):
    try:
        return m.inverted()
    except ValueError:
        return Matrix()

# ⭐ 新增：绝对安全的深度孤立数据清理器
def deep_purge_orphans():
    """循环执行垃圾回收，无视上下文，彻底清除无用材质/贴图/动作"""
    for _ in range(3): 
        for data_collections in (
            bpy.data.meshes, bpy.data.materials, bpy.data.textures,
            bpy.data.images, bpy.data.armatures, bpy.data.actions, bpy.data.node_groups
        ):
            # ⭐ 核心修复：套上一层 list() 强制转换为静态副本再遍历
            for block in list(data_collections): 
                if block.users == 0:
                    try: data_collections.remove(block)
                    except: pass

def get_all_fcurves(action):
    fcurves = []
    if hasattr(action, "layers"): 
        for layer in action.layers:
            for strip in layer.strips:
                if hasattr(strip, "channelbags"):
                    for bag in strip.channelbags:
                        fcurves.extend(bag.fcurves)
    elif hasattr(action, "fcurves"): 
        fcurves = action.fcurves
    return fcurves

def get_unique_keyframes(action):
    frames = set()
    for fcu in get_all_fcurves(action):
        for kp in fcu.keyframe_points: 
            frames.add(kp.co[0])
    return sorted(list(frames))

def transfer_all_animations(source, target, clean_old=True):
    scene = bpy.context.scene
    orig_frame = scene.frame_current

    actions = []
    source_bone_names = {b.name for b in source.pose.bones}
    path_pattern = re.compile(r'pose\.bones\[["\']([^"\']+)["\']\]')
    
    for act in bpy.data.actions:
        is_compatible = False
        for fcu in get_all_fcurves(act):
            match = path_pattern.search(fcu.data_path)
            if match:
                if match.group(1) in source_bone_names:
                    is_compatible = True
                    break
        if is_compatible:
            actions.append(act)

    if not actions: return False

    if not target.animation_data: target.animation_data_create()
    if target.animation_data.nla_tracks:
        for track in reversed(target.animation_data.nla_tracks):
            target.animation_data.nla_tracks.remove(track)

    def get_sorted_bones(arm_obj):
        sorted_bones = []
        def add_recursive(bone):
            sorted_bones.append(bone.name)
            for child in bone.children: add_recursive(child)
        roots = [b for b in arm_obj.pose.bones if not b.parent]
        for r in roots: add_recursive(r)
        return sorted_bones

    bone_names_order = get_sorted_bones(target)
    action_map = {}

    if not source.animation_data: source.animation_data_create()

    try:
        for action in set(actions):
            source.animation_data.action = action
            
            new_action = bpy.data.actions.new(name=action.name + "_Fixed")
            new_action.use_fake_user = True 
            action_map[action] = new_action
            
            frames = get_unique_keyframes(action)
            if not frames: continue

            scene.frame_set(int(round(frames[0])))
            bpy.context.evaluated_depsgraph_get().update()
            
            target.animation_data.action = new_action
            bpy.ops.object.mode_set(mode='POSE')

            for f in frames:
                f_int = int(round(f))
                scene.frame_set(f_int)
                bpy.context.view_layer.update()
                
                src_mats = {pb.name: pb.matrix.copy() for pb in source.pose.bones}
                tgt_pose_mats = {}

                for b_name in bone_names_order:
                    if b_name not in src_mats: continue
                    tpb = target.pose.bones[b_name]
                    spb = source.pose.bones[b_name]
                    
                    M_target_world = src_mats[b_name] @ safe_invert(spb.bone.matrix_local) @ tpb.bone.matrix_local
                    tgt_pose_mats[b_name] = M_target_world
                    
                    if tpb.parent:
                        M_parent_pose = tgt_pose_mats[tpb.parent.name]
                        M_parent_rest = tpb.parent.bone.matrix_local
                        M_rest = tpb.bone.matrix_local
                        M_base = M_parent_pose @ safe_invert(M_parent_rest) @ M_rest
                        M_local = safe_invert(M_base) @ M_target_world
                    else:
                        M_local = safe_invert(tpb.bone.matrix_local) @ M_target_world
                        
                    loc, rot, sca = M_local.decompose()
                    
                    tpb.location = loc 
                    if tpb.rotation_mode == 'QUATERNION': tpb.rotation_quaternion = rot
                    else: tpb.rotation_euler = rot.to_euler(tpb.rotation_mode)
                    tpb.scale = sca

                    target.keyframe_insert(data_path=f'pose.bones["{b_name}"].location', frame=f_int)
                    rot_p = "rotation_quaternion" if tpb.rotation_mode == 'QUATERNION' else "rotation_euler"
                    target.keyframe_insert(data_path=f'pose.bones["{b_name}"].{rot_p}', frame=f_int)
                    target.keyframe_insert(data_path=f'pose.bones["{b_name}"].scale', frame=f_int)

            bpy.ops.object.mode_set(mode='OBJECT')
            
            track = target.animation_data.nla_tracks.new()
            track.name = new_action.name
            track.strips.new(new_action.name, int(round(frames[0])), new_action)
            track.mute = True
            
            target.animation_data.action = None

        if target.animation_data.nla_tracks:
            last_track = target.animation_data.nla_tracks[-1]
            last_track.mute = False
            target.animation_data.action = last_track.strips[0].action

        if clean_old:
            if source.animation_data:
                source.animation_data.action = None
                if source.animation_data.nla_tracks:
                    for t in reversed(source.animation_data.nla_tracks):
                        source.animation_data.nla_tracks.remove(t)

            for old_act, new_act in action_map.items():
                old_name = old_act.name
                if old_name in bpy.data.actions:
                    bpy.data.actions.remove(old_act)
                new_act.name = old_name
                
                if target.animation_data and target.animation_data.nla_tracks:
                    for track in target.animation_data.nla_tracks:
                        for strip in track.strips:
                            if strip.action == new_act:
                                track.name = old_name
                                strip.name = old_name

        for obj in scene.objects:
            if obj.type == 'MESH':
                if obj.parent == source:
                    mat = obj.matrix_world.copy()
                    obj.parent = target
                    obj.matrix_world = mat
                for mod in obj.modifiers:
                    if mod.type == 'ARMATURE' and mod.object == source:
                        mod.object = target
                        
    finally:
        scene.frame_set(orig_frame)

    return True