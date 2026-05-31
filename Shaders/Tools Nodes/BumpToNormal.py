import bpy
import mathutils
import os
import typing


def bumptonormal_1_node_group(node_tree_names: dict[typing.Callable, str]):
    """Initialize BumpToNormal node group"""
    bumptonormal_1 = bpy.data.node_groups.new(type = 'ShaderNodeTree', name = "BumpToNormal")

    bumptonormal_1.color_tag = 'VECTOR'
    bumptonormal_1.description = ""
    bumptonormal_1.default_group_node_width = 140
    # bumptonormal_1 interface

    # Socket Normal Output
    normal_output_socket = bumptonormal_1.interface.new_socket(name="Normal Output", in_out='OUTPUT', socket_type='NodeSocketVector')
    normal_output_socket.default_value = (0.0, 0.0, 0.0)
    normal_output_socket.min_value = -3.4028234663852886e+38
    normal_output_socket.max_value = 3.4028234663852886e+38
    normal_output_socket.subtype = 'NONE'
    normal_output_socket.attribute_domain = 'POINT'
    normal_output_socket.default_input = 'VALUE'
    normal_output_socket.structure_type = 'AUTO'

    # Socket Strength
    strength_socket = bumptonormal_1.interface.new_socket(name="Strength", in_out='INPUT', socket_type='NodeSocketFloat')
    strength_socket.default_value = 1.0
    strength_socket.min_value = 0.0
    strength_socket.max_value = 1.0
    strength_socket.subtype = 'FACTOR'
    strength_socket.attribute_domain = 'POINT'
    strength_socket.description = "Strength of the bump mapping effect, interpolating between no bump mapping and full bump mapping"
    strength_socket.default_input = 'VALUE'
    strength_socket.structure_type = 'AUTO'

    # Socket Texture Input
    texture_input_socket = bumptonormal_1.interface.new_socket(name="Texture Input", in_out='INPUT', socket_type='NodeSocketColor')
    texture_input_socket.default_value = (0.0, 0.0, 0.0, 1.0)
    texture_input_socket.attribute_domain = 'POINT'
    texture_input_socket.description = "Height above surface. Connect the height map texture to this input"
    texture_input_socket.default_input = 'VALUE'
    texture_input_socket.structure_type = 'AUTO'

    # Socket Normal Input
    normal_input_socket = bumptonormal_1.interface.new_socket(name="Normal Input", in_out='INPUT', socket_type='NodeSocketVector')
    normal_input_socket.default_value = (0.0, 0.0, 0.0)
    normal_input_socket.min_value = -1.0
    normal_input_socket.max_value = 1.0
    normal_input_socket.subtype = 'NONE'
    normal_input_socket.attribute_domain = 'POINT'
    normal_input_socket.hide_value = True
    normal_input_socket.default_input = 'VALUE'
    normal_input_socket.structure_type = 'AUTO'

    # Initialize bumptonormal_1 nodes

    # Node 组输入
    ___ = bumptonormal_1.nodes.new("NodeGroupInput")
    ___.name = "组输入"

    # Node 组输出
    ____1 = bumptonormal_1.nodes.new("NodeGroupOutput")
    ____1.name = "组输出"
    ____1.is_active_output = True

    # Node 凹凸
    __ = bumptonormal_1.nodes.new("ShaderNodeBump")
    __.name = "凹凸"
    __.invert = False
    # Strength
    __.inputs[0].default_value = 1.0
    # Filter Width
    __.inputs[2].default_value = 0.10000000149011612

    # Set locations
    bumptonormal_1.nodes["组输入"].location = (-280.0, -20.0)
    bumptonormal_1.nodes["组输出"].location = (100.0, 0.0)
    bumptonormal_1.nodes["凹凸"].location = (-70.0, 0.0)

    # Set dimensions
    bumptonormal_1.nodes["组输入"].width  = 140.0
    bumptonormal_1.nodes["组输入"].height = 100.0

    bumptonormal_1.nodes["组输出"].width  = 140.0
    bumptonormal_1.nodes["组输出"].height = 100.0

    bumptonormal_1.nodes["凹凸"].width  = 140.0
    bumptonormal_1.nodes["凹凸"].height = 100.0


    # Initialize bumptonormal_1 links

    # ___.Texture Input -> __.Height
    bumptonormal_1.links.new(
        bumptonormal_1.nodes["组输入"].outputs[1],
        bumptonormal_1.nodes["凹凸"].inputs[3]
    )
    # ___.Normal Input -> __.Normal
    bumptonormal_1.links.new(
        bumptonormal_1.nodes["组输入"].outputs[2],
        bumptonormal_1.nodes["凹凸"].inputs[4]
    )
    # __.Normal -> ____1.Normal Output
    bumptonormal_1.links.new(
        bumptonormal_1.nodes["凹凸"].outputs[0],
        bumptonormal_1.nodes["组输出"].inputs[0]
    )
    # ___.Strength -> __.Distance
    bumptonormal_1.links.new(
        bumptonormal_1.nodes["组输入"].outputs[0],
        bumptonormal_1.nodes["凹凸"].inputs[1]
    )

    return bumptonormal_1


if __name__ == "__main__":
    # Maps node tree creation functions to the node tree 
    # name, such that we don't recreate node trees unnecessarily
    node_tree_names : dict[typing.Callable, str] = {}

    bumptonormal = bumptonormal_1_node_group(node_tree_names)
    node_tree_names[bumptonormal_1_node_group] = bumptonormal.name

