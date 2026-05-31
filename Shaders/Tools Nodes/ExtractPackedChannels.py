import bpy
import mathutils
import os
import typing


def extractpackedchannels_1_node_group(node_tree_names: dict[typing.Callable, str]):
    """Initialize ExtractPackedChannels node group"""
    extractpackedchannels_1 = bpy.data.node_groups.new(type = 'ShaderNodeTree', name = "ExtractPackedChannels")

    extractpackedchannels_1.color_tag = 'CONVERTER'
    extractpackedchannels_1.description = ""
    extractpackedchannels_1.default_group_node_width = 140
    # extractpackedchannels_1 interface

    # Socket R
    r_socket = extractpackedchannels_1.interface.new_socket(name="R", in_out='OUTPUT', socket_type='NodeSocketFloat')
    r_socket.default_value = 0.0
    r_socket.min_value = -3.4028234663852886e+38
    r_socket.max_value = 3.4028234663852886e+38
    r_socket.subtype = 'NONE'
    r_socket.attribute_domain = 'POINT'
    r_socket.default_input = 'VALUE'
    r_socket.structure_type = 'AUTO'

    # Socket G
    g_socket = extractpackedchannels_1.interface.new_socket(name="G", in_out='OUTPUT', socket_type='NodeSocketFloat')
    g_socket.default_value = 0.0
    g_socket.min_value = -3.4028234663852886e+38
    g_socket.max_value = 3.4028234663852886e+38
    g_socket.subtype = 'NONE'
    g_socket.attribute_domain = 'POINT'
    g_socket.default_input = 'VALUE'
    g_socket.structure_type = 'AUTO'

    # Socket B
    b_socket = extractpackedchannels_1.interface.new_socket(name="B", in_out='OUTPUT', socket_type='NodeSocketFloat')
    b_socket.default_value = 0.0
    b_socket.min_value = -3.4028234663852886e+38
    b_socket.max_value = 3.4028234663852886e+38
    b_socket.subtype = 'NONE'
    b_socket.attribute_domain = 'POINT'
    b_socket.default_input = 'VALUE'
    b_socket.structure_type = 'AUTO'

    # Socket A
    a_socket = extractpackedchannels_1.interface.new_socket(name="A", in_out='OUTPUT', socket_type='NodeSocketFloat')
    a_socket.default_value = 1.0
    a_socket.min_value = 0.0
    a_socket.max_value = 1.0
    a_socket.subtype = 'NONE'
    a_socket.attribute_domain = 'POINT'
    a_socket.default_input = 'VALUE'
    a_socket.structure_type = 'AUTO'

    # Socket Texture Input
    texture_input_socket = extractpackedchannels_1.interface.new_socket(name="Texture Input", in_out='INPUT', socket_type='NodeSocketColor')
    texture_input_socket.default_value = (0.5, 0.5, 0.0, 1.0)
    texture_input_socket.attribute_domain = 'POINT'
    texture_input_socket.default_input = 'VALUE'
    texture_input_socket.structure_type = 'AUTO'

    # Socket Alpha Input
    alpha_input_socket = extractpackedchannels_1.interface.new_socket(name="Alpha Input", in_out='INPUT', socket_type='NodeSocketFloat')
    alpha_input_socket.default_value = 0.0
    alpha_input_socket.min_value = 0.0
    alpha_input_socket.max_value = 1.0
    alpha_input_socket.subtype = 'NONE'
    alpha_input_socket.attribute_domain = 'POINT'
    alpha_input_socket.default_input = 'VALUE'
    alpha_input_socket.structure_type = 'AUTO'

    # Initialize extractpackedchannels_1 nodes

    # Node 组输出
    ___ = extractpackedchannels_1.nodes.new("NodeGroupOutput")
    ___.name = "组输出"
    ___.is_active_output = True

    # Node 组输入
    ____1 = extractpackedchannels_1.nodes.new("NodeGroupInput")
    ____1.name = "组输入"

    # Node 分离颜色
    ____ = extractpackedchannels_1.nodes.new("ShaderNodeSeparateColor")
    ____.name = "分离颜色"
    ____.mode = 'RGB'

    # Set locations
    extractpackedchannels_1.nodes["组输出"].location = (20.0, 40.0)
    extractpackedchannels_1.nodes["组输入"].location = (-380.0, 40.0)
    extractpackedchannels_1.nodes["分离颜色"].location = (-180.0, 40.0)

    # Set dimensions
    extractpackedchannels_1.nodes["组输出"].width  = 140.0
    extractpackedchannels_1.nodes["组输出"].height = 100.0

    extractpackedchannels_1.nodes["组输入"].width  = 140.0
    extractpackedchannels_1.nodes["组输入"].height = 100.0

    extractpackedchannels_1.nodes["分离颜色"].width  = 140.0
    extractpackedchannels_1.nodes["分离颜色"].height = 100.0


    # Initialize extractpackedchannels_1 links

    # ____1.Texture Input -> ____.Color
    extractpackedchannels_1.links.new(
        extractpackedchannels_1.nodes["组输入"].outputs[0],
        extractpackedchannels_1.nodes["分离颜色"].inputs[0]
    )
    # ____.Red -> ___.R
    extractpackedchannels_1.links.new(
        extractpackedchannels_1.nodes["分离颜色"].outputs[0],
        extractpackedchannels_1.nodes["组输出"].inputs[0]
    )
    # ____1.Alpha Input -> ___.A
    extractpackedchannels_1.links.new(
        extractpackedchannels_1.nodes["组输入"].outputs[1],
        extractpackedchannels_1.nodes["组输出"].inputs[3]
    )
    # ____.Green -> ___.G
    extractpackedchannels_1.links.new(
        extractpackedchannels_1.nodes["分离颜色"].outputs[1],
        extractpackedchannels_1.nodes["组输出"].inputs[1]
    )
    # ____.Blue -> ___.B
    extractpackedchannels_1.links.new(
        extractpackedchannels_1.nodes["分离颜色"].outputs[2],
        extractpackedchannels_1.nodes["组输出"].inputs[2]
    )

    return extractpackedchannels_1


if __name__ == "__main__":
    # Maps node tree creation functions to the node tree 
    # name, such that we don't recreate node trees unnecessarily
    node_tree_names : dict[typing.Callable, str] = {}

    extractpackedchannels = extractpackedchannels_1_node_group(node_tree_names)
    node_tree_names[extractpackedchannels_1_node_group] = extractpackedchannels.name

