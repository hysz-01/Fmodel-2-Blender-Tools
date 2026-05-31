import bpy
import mathutils
import os
import typing


def flipnormalx_1_node_group(node_tree_names: dict[typing.Callable, str]):
    """Initialize FlipNormalX node group"""
    flipnormalx_1 = bpy.data.node_groups.new(type = 'ShaderNodeTree', name = "FlipNormalX")

    flipnormalx_1.color_tag = 'CONVERTER'
    flipnormalx_1.description = ""
    flipnormalx_1.default_group_node_width = 140
    # flipnormalx_1 interface

    # Socket Texture Output
    texture_output_socket = flipnormalx_1.interface.new_socket(name="Texture Output", in_out='OUTPUT', socket_type='NodeSocketColor')
    texture_output_socket.default_value = (0.800000011920929, 0.800000011920929, 0.800000011920929, 1.0)
    texture_output_socket.attribute_domain = 'POINT'
    texture_output_socket.default_input = 'VALUE'
    texture_output_socket.structure_type = 'AUTO'

    # Socket Texture Input
    texture_input_socket = flipnormalx_1.interface.new_socket(name="Texture Input", in_out='INPUT', socket_type='NodeSocketColor')
    texture_input_socket.default_value = (0.5, 0.5, 1.0, 1.0)
    texture_input_socket.attribute_domain = 'POINT'
    texture_input_socket.default_input = 'VALUE'
    texture_input_socket.structure_type = 'AUTO'

    # Initialize flipnormalx_1 nodes

    # Node 组输出
    ___ = flipnormalx_1.nodes.new("NodeGroupOutput")
    ___.name = "组输出"
    ___.is_active_output = True

    # Node 组输入
    ____1 = flipnormalx_1.nodes.new("NodeGroupInput")
    ____1.name = "组输入"

    # Node 运算
    __ = flipnormalx_1.nodes.new("ShaderNodeMath")
    __.name = "运算"
    __.hide = True
    __.operation = 'SUBTRACT'
    __.use_clamp = False
    # Value
    __.inputs[0].default_value = 1.0

    # Node 分离颜色
    ____ = flipnormalx_1.nodes.new("ShaderNodeSeparateColor")
    ____.name = "分离颜色"
    ____.mode = 'RGB'

    # Node 合并颜色
    _____1 = flipnormalx_1.nodes.new("ShaderNodeCombineColor")
    _____1.name = "合并颜色"
    _____1.mode = 'RGB'

    # Set locations
    flipnormalx_1.nodes["组输出"].location = (380.0, 0.0)
    flipnormalx_1.nodes["组输入"].location = (-370.0, 0.0)
    flipnormalx_1.nodes["运算"].location = (0.0, 40.0)
    flipnormalx_1.nodes["分离颜色"].location = (-170.0, 40.0)
    flipnormalx_1.nodes["合并颜色"].location = (180.0, 40.0)

    # Set dimensions
    flipnormalx_1.nodes["组输出"].width  = 140.0
    flipnormalx_1.nodes["组输出"].height = 100.0

    flipnormalx_1.nodes["组输入"].width  = 140.0
    flipnormalx_1.nodes["组输入"].height = 100.0

    flipnormalx_1.nodes["运算"].width  = 140.0
    flipnormalx_1.nodes["运算"].height = 100.0

    flipnormalx_1.nodes["分离颜色"].width  = 140.0
    flipnormalx_1.nodes["分离颜色"].height = 100.0

    flipnormalx_1.nodes["合并颜色"].width  = 140.0
    flipnormalx_1.nodes["合并颜色"].height = 100.0


    # Initialize flipnormalx_1 links

    # __.Value -> _____1.Red
    flipnormalx_1.links.new(
        flipnormalx_1.nodes["运算"].outputs[0],
        flipnormalx_1.nodes["合并颜色"].inputs[0]
    )
    # ____1.Texture Input -> ____.Color
    flipnormalx_1.links.new(
        flipnormalx_1.nodes["组输入"].outputs[0],
        flipnormalx_1.nodes["分离颜色"].inputs[0]
    )
    # _____1.Color -> ___.Texture Output
    flipnormalx_1.links.new(
        flipnormalx_1.nodes["合并颜色"].outputs[0],
        flipnormalx_1.nodes["组输出"].inputs[0]
    )
    # ____.Green -> _____1.Green
    flipnormalx_1.links.new(
        flipnormalx_1.nodes["分离颜色"].outputs[1],
        flipnormalx_1.nodes["合并颜色"].inputs[1]
    )
    # ____.Blue -> _____1.Blue
    flipnormalx_1.links.new(
        flipnormalx_1.nodes["分离颜色"].outputs[2],
        flipnormalx_1.nodes["合并颜色"].inputs[2]
    )
    # ____.Red -> __.Value
    flipnormalx_1.links.new(
        flipnormalx_1.nodes["分离颜色"].outputs[0],
        flipnormalx_1.nodes["运算"].inputs[1]
    )

    return flipnormalx_1


if __name__ == "__main__":
    # Maps node tree creation functions to the node tree 
    # name, such that we don't recreate node trees unnecessarily
    node_tree_names : dict[typing.Callable, str] = {}

    flipnormalx = flipnormalx_1_node_group(node_tree_names)
    node_tree_names[flipnormalx_1_node_group] = flipnormalx.name

