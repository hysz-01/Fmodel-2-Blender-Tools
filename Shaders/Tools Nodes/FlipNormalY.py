import bpy
import mathutils
import os
import typing


def flipnormaly_1_node_group(node_tree_names: dict[typing.Callable, str]):
    """Initialize FlipNormalY node group"""
    flipnormaly_1 = bpy.data.node_groups.new(type = 'ShaderNodeTree', name = "FlipNormalY")

    flipnormaly_1.color_tag = 'CONVERTER'
    flipnormaly_1.description = ""
    flipnormaly_1.default_group_node_width = 140
    # flipnormaly_1 interface

    # Socket Texture Output
    texture_output_socket = flipnormaly_1.interface.new_socket(name="Texture Output", in_out='OUTPUT', socket_type='NodeSocketColor')
    texture_output_socket.default_value = (0.800000011920929, 0.800000011920929, 0.800000011920929, 1.0)
    texture_output_socket.attribute_domain = 'POINT'
    texture_output_socket.default_input = 'VALUE'
    texture_output_socket.structure_type = 'AUTO'

    # Socket Texture Input
    texture_input_socket = flipnormaly_1.interface.new_socket(name="Texture Input", in_out='INPUT', socket_type='NodeSocketColor')
    texture_input_socket.default_value = (0.5, 0.5, 1.0, 1.0)
    texture_input_socket.attribute_domain = 'POINT'
    texture_input_socket.default_input = 'VALUE'
    texture_input_socket.structure_type = 'AUTO'

    # Initialize flipnormaly_1 nodes

    # Node 组输出
    ___ = flipnormaly_1.nodes.new("NodeGroupOutput")
    ___.name = "组输出"
    ___.is_active_output = True

    # Node 组输入
    ____1 = flipnormaly_1.nodes.new("NodeGroupInput")
    ____1.name = "组输入"

    # Node 运算
    __ = flipnormaly_1.nodes.new("ShaderNodeMath")
    __.name = "运算"
    __.hide = True
    __.operation = 'SUBTRACT'
    __.use_clamp = False
    # Value
    __.inputs[0].default_value = 1.0

    # Node 分离颜色
    ____ = flipnormaly_1.nodes.new("ShaderNodeSeparateColor")
    ____.name = "分离颜色"
    ____.mode = 'RGB'

    # Node 合并颜色
    _____1 = flipnormaly_1.nodes.new("ShaderNodeCombineColor")
    _____1.name = "合并颜色"
    _____1.mode = 'RGB'

    # Set locations
    flipnormaly_1.nodes["组输出"].location = (360.0, 0.0)
    flipnormaly_1.nodes["组输入"].location = (-370.0, 0.0)
    flipnormaly_1.nodes["运算"].location = (0.0, 0.0)
    flipnormaly_1.nodes["分离颜色"].location = (-170.0, 40.0)
    flipnormaly_1.nodes["合并颜色"].location = (170.0, 40.0)

    # Set dimensions
    flipnormaly_1.nodes["组输出"].width  = 140.0
    flipnormaly_1.nodes["组输出"].height = 100.0

    flipnormaly_1.nodes["组输入"].width  = 140.0
    flipnormaly_1.nodes["组输入"].height = 100.0

    flipnormaly_1.nodes["运算"].width  = 140.0
    flipnormaly_1.nodes["运算"].height = 100.0

    flipnormaly_1.nodes["分离颜色"].width  = 140.0
    flipnormaly_1.nodes["分离颜色"].height = 100.0

    flipnormaly_1.nodes["合并颜色"].width  = 140.0
    flipnormaly_1.nodes["合并颜色"].height = 100.0


    # Initialize flipnormaly_1 links

    # ____.Red -> _____1.Red
    flipnormaly_1.links.new(
        flipnormaly_1.nodes["分离颜色"].outputs[0],
        flipnormaly_1.nodes["合并颜色"].inputs[0]
    )
    # __.Value -> _____1.Green
    flipnormaly_1.links.new(
        flipnormaly_1.nodes["运算"].outputs[0],
        flipnormaly_1.nodes["合并颜色"].inputs[1]
    )
    # ____.Blue -> _____1.Blue
    flipnormaly_1.links.new(
        flipnormaly_1.nodes["分离颜色"].outputs[2],
        flipnormaly_1.nodes["合并颜色"].inputs[2]
    )
    # ____1.Texture Input -> ____.Color
    flipnormaly_1.links.new(
        flipnormaly_1.nodes["组输入"].outputs[0],
        flipnormaly_1.nodes["分离颜色"].inputs[0]
    )
    # _____1.Color -> ___.Texture Output
    flipnormaly_1.links.new(
        flipnormaly_1.nodes["合并颜色"].outputs[0],
        flipnormaly_1.nodes["组输出"].inputs[0]
    )
    # ____.Green -> __.Value
    flipnormaly_1.links.new(
        flipnormaly_1.nodes["分离颜色"].outputs[1],
        flipnormaly_1.nodes["运算"].inputs[1]
    )

    return flipnormaly_1


if __name__ == "__main__":
    # Maps node tree creation functions to the node tree 
    # name, such that we don't recreate node trees unnecessarily
    node_tree_names : dict[typing.Callable, str] = {}

    flipnormaly = flipnormaly_1_node_group(node_tree_names)
    node_tree_names[flipnormaly_1_node_group] = flipnormaly.name

