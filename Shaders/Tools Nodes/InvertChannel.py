import bpy
import mathutils
import os
import typing


def invertchannel_1_node_group(node_tree_names: dict[typing.Callable, str]):
    """Initialize InvertChannel node group"""
    invertchannel_1 = bpy.data.node_groups.new(type = 'ShaderNodeTree', name = "InvertChannel")

    invertchannel_1.color_tag = 'CONVERTER'
    invertchannel_1.description = ""
    invertchannel_1.default_group_node_width = 140
    # invertchannel_1 interface

    # Socket Texture Output
    texture_output_socket = invertchannel_1.interface.new_socket(name="Texture Output", in_out='OUTPUT', socket_type='NodeSocketFloat')
    texture_output_socket.default_value = 0.0
    texture_output_socket.min_value = -3.4028234663852886e+38
    texture_output_socket.max_value = 3.4028234663852886e+38
    texture_output_socket.subtype = 'NONE'
    texture_output_socket.attribute_domain = 'POINT'
    texture_output_socket.default_input = 'VALUE'
    texture_output_socket.structure_type = 'AUTO'

    # Socket Texture Input
    texture_input_socket = invertchannel_1.interface.new_socket(name="Texture Input", in_out='INPUT', socket_type='NodeSocketFloat')
    texture_input_socket.default_value = 1.0
    texture_input_socket.min_value = 0.0
    texture_input_socket.max_value = 1.0
    texture_input_socket.subtype = 'NONE'
    texture_input_socket.attribute_domain = 'POINT'
    texture_input_socket.default_input = 'VALUE'
    texture_input_socket.structure_type = 'AUTO'

    # Initialize invertchannel_1 nodes

    # Node 组输入
    ___ = invertchannel_1.nodes.new("NodeGroupInput")
    ___.name = "组输入"

    # Node 组输出
    ____1 = invertchannel_1.nodes.new("NodeGroupOutput")
    ____1.name = "组输出"
    ____1.is_active_output = True

    # Node 运算
    __ = invertchannel_1.nodes.new("ShaderNodeMath")
    __.name = "运算"
    __.operation = 'SUBTRACT'
    __.use_clamp = False
    # Value
    __.inputs[0].default_value = 1.0

    # Set locations
    invertchannel_1.nodes["组输入"].location = (-460.0, 20.0)
    invertchannel_1.nodes["组输出"].location = (-100.0, 20.0)
    invertchannel_1.nodes["运算"].location = (-280.0, 20.0)

    # Set dimensions
    invertchannel_1.nodes["组输入"].width  = 140.0
    invertchannel_1.nodes["组输入"].height = 100.0

    invertchannel_1.nodes["组输出"].width  = 140.0
    invertchannel_1.nodes["组输出"].height = 100.0

    invertchannel_1.nodes["运算"].width  = 140.0
    invertchannel_1.nodes["运算"].height = 100.0


    # Initialize invertchannel_1 links

    # ___.Texture Input -> __.Value
    invertchannel_1.links.new(
        invertchannel_1.nodes["组输入"].outputs[0],
        invertchannel_1.nodes["运算"].inputs[1]
    )
    # __.Value -> ____1.Texture Output
    invertchannel_1.links.new(
        invertchannel_1.nodes["运算"].outputs[0],
        invertchannel_1.nodes["组输出"].inputs[0]
    )

    return invertchannel_1


if __name__ == "__main__":
    # Maps node tree creation functions to the node tree 
    # name, such that we don't recreate node trees unnecessarily
    node_tree_names : dict[typing.Callable, str] = {}

    invertchannel = invertchannel_1_node_group(node_tree_names)
    node_tree_names[invertchannel_1_node_group] = invertchannel.name

