# FModel_Tools/Universal_tools/Animations/clean_Anim.py
# 动作清理 — 关键帧精简、空通道删除、批量清理

import bpy


def clean_action(action, threshold=0.001, clean_channels=True, clean_flat=True):
    """
    清理单个动作的冗余关键帧
    
    参数:
        action: 要清理的 bpy.types.Action
        threshold: 精简阈值，越大清理越狠
        clean_channels: 是否删除空通道
        clean_flat: 是否精简平坦通道（保留第一帧）
    
    返回:
        dict: {'removed_keyframes': int, 'removed_channels': int, 'flat_channels': int}
    """
    if not action or not action.fcurves:
        return {'removed_keyframes': 0, 'removed_channels': 0, 'flat_channels': 0}
    
    stats = {'removed_keyframes': 0, 'removed_channels': 0, 'flat_channels': 0}
    initial_keyframe_count = sum(len(fc.keyframe_points) for fc in action.fcurves)
    
    # 选中所有关键帧（bpy.ops.action.clean 需要选中的关键帧）
    for fc in action.fcurves:
        for k in fc.keyframe_points:
            k.select_control_point = True
            k.select_left_handle = True
            k.select_right_handle = True
    
    # 找到 Dope Sheet 区域（操作符需要正确的上下文）
    dope_sheet_area = None
    for area in bpy.context.screen.areas:
        if area.type == 'DOPESHEET_EDITOR':
            dope_sheet_area = area
            break
    
    # 如果找到 Dope Sheet，使用操作符精简
    if dope_sheet_area:
        try:
            # 保存当前活动对象和动作
            orig_active = bpy.context.active_object
            orig_action = None
            if orig_active and orig_active.animation_data:
                orig_action = orig_active.animation_data.action
            
            # 创建临时对象绑定动作
            temp_obj = None
            temp_mesh = bpy.data.meshes.new("_FModel_CleanTemp")
            temp_obj = bpy.data.objects.new("_FModel_CleanTemp", temp_mesh)
            bpy.context.collection.objects.link(temp_obj)
            
            if not temp_obj.animation_data:
                temp_obj.animation_data_create()
            temp_obj.animation_data.action = action
            
            # 设置上下文覆盖
            override = bpy.context.copy()
            override['window'] = bpy.context.window
            override['screen'] = bpy.context.screen
            override['area'] = dope_sheet_area
            override['region'] = dope_sheet_area.regions[0]
            override['scene'] = bpy.context.scene
            override['active_object'] = temp_obj
            override['selected_objects'] = [temp_obj]
            override['selected_editable_objects'] = [temp_obj]
            
            # 执行清理（channels=False 避免删除通道导致姿态丢失）
            with bpy.context.temp_override(**override):
                bpy.ops.action.clean(threshold=threshold, channels=False)
            
            # 清理临时对象
            if temp_obj:
                if temp_obj.animation_data:
                    temp_obj.animation_data.action = None
                bpy.data.objects.remove(temp_obj, do_unlink=True)
            if temp_mesh and temp_mesh.users == 0:
                bpy.data.meshes.remove(temp_mesh)
            
            # 恢复原始状态
            if orig_active:
                bpy.context.view_layer.objects.active = orig_active

        except Exception as e:
            print(f"[FModel Clean] 操作符清理失败: {e}")
            # 使用日志系统
            import logging
            logging.getLogger(__name__).error(f"操作符清理失败: {e}")
    
    # 手动清理平坦通道和空通道
    for i in range(len(action.fcurves) - 1, -1, -1):
        fc = action.fcurves[i]
        
        # 删除空通道
        if len(fc.keyframe_points) == 0:
            if clean_channels:
                action.fcurves.remove(fc)
                stats['removed_channels'] += 1
            continue
        
        # 精简平坦通道（保留第一帧）
        if clean_flat:
            min_val = min([k.co[1] for k in fc.keyframe_points])
            max_val = max([k.co[1] for k in fc.keyframe_points])
            
            if (max_val - min_val) <= threshold:
                # 从后往前删，保留第一帧维持起始姿态
                key_count = len(fc.keyframe_points)
                for j in range(key_count - 1, 0, -1):
                    fc.keyframe_points.remove(fc.keyframe_points[j])
                stats['flat_channels'] += 1
                stats['removed_keyframes'] += (key_count - 1)
    
    # 统计最终关键帧数
    final_keyframe_count = sum(len(fc.keyframe_points) for fc in action.fcurves)
    stats['removed_keyframes'] += (initial_keyframe_count - final_keyframe_count)
    
    return stats


def clean_actions_batch(actions, threshold=0.001, clean_channels=True, clean_flat=True):
    """
    批量清理多个动作
    
    参数:
        actions: Action 列表
        threshold: 精简阈值
        clean_channels: 是否删除空通道
        clean_flat: 是否精简平坦通道
    
    返回:
        dict: {'total_actions': int, 'cleaned_actions': int, 'total_removed': int}
    """
    result = {'total_actions': len(actions), 'cleaned_actions': 0, 'total_removed': 0}
    
    for action in actions:
        try:
            stats = clean_action(action, threshold, clean_channels, clean_flat)
            if stats['removed_keyframes'] > 0 or stats['removed_channels'] > 0:
                result['cleaned_actions'] += 1
                result['total_removed'] += stats['removed_keyframes']
        except Exception as e:
            print(f"[FModel Clean] 清理 {action.name} 失败: {e}")
            # 使用日志系统
            import logging
            logging.getLogger(__name__).error(f"清理 {action.name} 失败: {e}")
    
    return result


def is_action_used(action):
    """
    检查动作是否被使用
    
    返回:
        bool: True 如果动作被任何对象、NLA 或形态键使用
    """
    # 检查对象动画数据
    for obj in bpy.data.objects:
        if obj.animation_data and obj.animation_data.action == action:
            return True
    
    # 检查 NLA 轨道
    for obj in bpy.data.objects:
        if obj.animation_data and obj.animation_data.nla_tracks:
            for track in obj.animation_data.nla_tracks:
                for strip in track.strips:
                    if strip.action == action:
                        return True
    
    # 检查形态键
    for key in bpy.data.shape_keys:
        if key.animation_data and key.animation_data.action == action:
            return True
    
    return False


def get_action_stats(action):
    """
    获取动作统计信息
    
    返回:
        dict: {'fcurves': int, 'keyframes': int, 'frame_range': tuple}
    """
    if not action:
        return {'fcurves': 0, 'keyframes': 0, 'frame_range': (0, 0)}
    
    keyframe_count = sum(len(fc.keyframe_points) for fc in action.fcurves)
    
    return {
        'fcurves': len(action.fcurves),
        'keyframes': keyframe_count,
        'frame_range': action.frame_range if action.frame_range else (0, 0)
    }


# ============================================================
# 操作符
# ============================================================

class ANIM_OT_CleanAction(bpy.types.Operator):
    """清理当前动作的冗余关键帧"""
    bl_idname = "fmodel.clean_action"
    bl_label = "清理动作"
    bl_options = {'REGISTER', 'UNDO'}
    
    threshold: bpy.props.FloatProperty(
        name="精简阈值",
        default=0.001,
        min=0.0,
        max=1.0,
        precision=4
    )
    clean_channels: bpy.props.BoolProperty(
        name="删除空通道",
        default=True
    )
    clean_flat: bpy.props.BoolProperty(
        name="精简平坦通道",
        default=True
    )
    
    @classmethod
    def poll(cls, context):
        obj = context.active_object
        return obj and obj.animation_data and obj.animation_data.action
    
    def execute(self, context):
        action = context.active_object.animation_data.action
        stats = clean_action(action, self.threshold, self.clean_channels, self.clean_flat)
        
        self.report({'INFO'}, 
            f"清理完成: 移除 {stats['removed_keyframes']} 个关键帧, "
            f"{stats['removed_channels']} 个空通道, "
            f"{stats['flat_channels']} 个平坦通道"
        )
        return {'FINISHED'}
    
    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self)


class ANIM_OT_CleanAllActions(bpy.types.Operator):
    """批量清理所有动作"""
    bl_idname = "fmodel.clean_all_actions"
    bl_label = "批量清理动作"
    bl_options = {'REGISTER', 'UNDO'}
    
    threshold: bpy.props.FloatProperty(
        name="精简阈值",
        default=0.001,
        min=0.0,
        max=1.0,
        precision=4
    )
    clean_channels: bpy.props.BoolProperty(
        name="删除空通道",
        default=True
    )
    clean_flat: bpy.props.BoolProperty(
        name="精简平坦通道",
        default=True
    )
    include_unused: bpy.props.BoolProperty(
        name="包含未使用动作",
        default=False
    )
    
    @classmethod
    def poll(cls, context):
        return len(bpy.data.actions) > 0
    
    def execute(self, context):
        if self.include_unused:
            actions = list(bpy.data.actions)
        else:
            actions = [a for a in bpy.data.actions if is_action_used(a)]
        
        result = clean_actions_batch(actions, self.threshold, self.clean_channels, self.clean_flat)
        
        self.report({'INFO'}, 
            f"批量清理完成: {result['cleaned_actions']}/{result['total_actions']} 个动作, "
            f"共移除 {result['total_removed']} 个关键帧"
        )
        return {'FINISHED'}
    
    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self)


# ============================================================
# 注册
# ============================================================

classes = (
    ANIM_OT_CleanAction,
    ANIM_OT_CleanAllActions,
)


def register():
    for cls in classes:
        bpy.utils.register_class(cls)


def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)