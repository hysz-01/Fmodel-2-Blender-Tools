import bpy
import mathutils
import os
import typing


def decodearm_1_node_group(node_tree_names: dict[typing.Callable, str]):
    """Initialize DecodeARM node group"""
    decodearm_1 = bpy.data.node_groups.new(type = 'ShaderNodeTree', name = "DecodeARM")

    decodearm_1.color_tag = 'CONVERTER'
    decodearm_1.description = ""
    decodearm_1.default_group_node_width = 140
    # decodearm_1 interface

    # Socket R(Metal)
    r_metal__socket = decodearm_1.interface.new_socket(name="R(Metal)", in_out='OUTPUT', socket_type='NodeSocketFloat')
    r_metal__socket.default_value = 0.0
    r_metal__socket.min_value = -3.4028234663852886e+38
    r_metal__socket.max_value = 3.4028234663852886e+38
    r_metal__socket.subtype = 'NONE'
    r_metal__socket.attribute_domain = 'POINT'
    r_metal__socket.default_input = 'VALUE'
    r_metal__socket.structure_type = 'AUTO'

    # Socket G(AO)
    g_ao__socket = decodearm_1.interface.new_socket(name="G(AO)", in_out='OUTPUT', socket_type='NodeSocketFloat')
    g_ao__socket.default_value = 0.0
    g_ao__socket.min_value = -3.4028234663852886e+38
    g_ao__socket.max_value = 3.4028234663852886e+38
    g_ao__socket.subtype = 'NONE'
    g_ao__socket.attribute_domain = 'POINT'
    g_ao__socket.default_input = 'VALUE'
    g_ao__socket.structure_type = 'AUTO'

    # Socket B(Rough)
    b_rough__socket = decodearm_1.interface.new_socket(name="B(Rough)", in_out='OUTPUT', socket_type='NodeSocketFloat')
    b_rough__socket.default_value = 0.0
    b_rough__socket.min_value = -3.4028234663852886e+38
    b_rough__socket.max_value = 3.4028234663852886e+38
    b_rough__socket.subtype = 'NONE'
    b_rough__socket.attribute_domain = 'POINT'
    b_rough__socket.default_input = 'VALUE'
    b_rough__socket.structure_type = 'AUTO'

    # Socket A
    a_socket = decodearm_1.interface.new_socket(name="A", in_out='OUTPUT', socket_type='NodeSocketFloat')
    a_socket.default_value = 1.0
    a_socket.min_value = 0.0
    a_socket.max_value = 1.0
    a_socket.subtype = 'NONE'
    a_socket.attribute_domain = 'POINT'
    a_socket.default_input = 'VALUE'
    a_socket.structure_type = 'AUTO'

    # Socket Texture Input
    texture_input_socket = decodearm_1.interface.new_socket(name="Texture Input", in_out='INPUT', socket_type='NodeSocketColor')
    texture_input_socket.default_value = (0.5, 0.5, 0.0, 1.0)
    texture_input_socket.attribute_domain = 'POINT'
    texture_input_socket.default_input = 'VALUE'
    texture_input_socket.structure_type = 'AUTO'

    # Socket Alpha Input
    alpha_input_socket = decodearm_1.interface.new_socket(name="Alpha Input", in_out='INPUT', socket_type='NodeSocketFloat')
    alpha_input_socket.default_value = 0.0
    alpha_input_socket.min_value = 0.0
    alpha_input_socket.max_value = 1.0
    alpha_input_socket.subtype = 'NONE'
    alpha_input_socket.attribute_domain = 'POINT'
    alpha_input_socket.default_input = 'VALUE'
    alpha_input_socket.structure_type = 'AUTO'

    # Initialize decodearm_1 nodes

    # Node 组输出
    ___ = decodearm_1.nodes.new("NodeGroupOutput")
    ___.name = "组输出"
    ___.is_active_output = True

    # Node 组输入
    ____1 = decodearm_1.nodes.new("NodeGroupInput")
    ____1.name = "组输入"

    # Node 分离颜色
    ____ = decodearm_1.nodes.new("ShaderNodeSeparateColor")
    ____.name = "分离颜色"
    ____.mode = 'RGB'

    # Set locations
    decodearm_1.nodes["组输出"].location = (20.0, 40.0)
    decodearm_1.nodes["组输入"].location = (-380.0, 40.0)
    decodearm_1.nodes["分离颜色"].location = (-180.0, 40.0)

    # Set dimensions
    decodearm_1.nodes["组输出"].width  = 140.0
    decodearm_1.nodes["组输出"].height = 100.0

    decodearm_1.nodes["组输入"].width  = 140.0
    decodearm_1.nodes["组输入"].height = 100.0

    decodearm_1.nodes["分离颜色"].width  = 140.0
    decodearm_1.nodes["分离颜色"].height = 100.0


    # Initialize decodearm_1 links

    # ____1.Texture Input -> ____.Color
    decodearm_1.links.new(
        decodearm_1.nodes["组输入"].outputs[0],
        decodearm_1.nodes["分离颜色"].inputs[0]
    )
    # ____.Red -> ___.R(Metal)
    decodearm_1.links.new(
        decodearm_1.nodes["分离颜色"].outputs[0],
        decodearm_1.nodes["组输出"].inputs[0]
    )
    # ____1.Alpha Input -> ___.A
    decodearm_1.links.new(
        decodearm_1.nodes["组输入"].outputs[1],
        decodearm_1.nodes["组输出"].inputs[3]
    )
    # ____.Green -> ___.G(AO)
    decodearm_1.links.new(
        decodearm_1.nodes["分离颜色"].outputs[1],
        decodearm_1.nodes["组输出"].inputs[1]
    )
    # ____.Blue -> ___.B(Rough)
    decodearm_1.links.new(
        decodearm_1.nodes["分离颜色"].outputs[2],
        decodearm_1.nodes["组输出"].inputs[2]
    )

    return decodearm_1


if __name__ == "__main__":
    # Maps node tree creation functions to the node tree 
    # name, such that we don't recreate node trees unnecessarily
    node_tree_names : dict[typing.Callable, str] = {}

    decodearm = decodearm_1_node_group(node_tree_names)
    node_tree_names[decodearm_1_node_group] = decodearm.name

