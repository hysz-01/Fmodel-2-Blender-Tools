import bpy
import mathutils
import os
import typing


def normalmaptonormal_1_node_group(node_tree_names: dict[typing.Callable, str]):
    """Initialize NormalMapToNormal node group"""
    normalmaptonormal_1 = bpy.data.node_groups.new(type = 'ShaderNodeTree', name = "NormalMapToNormal")

    normalmaptonormal_1.color_tag = 'VECTOR'
    normalmaptonormal_1.description = ""
    normalmaptonormal_1.default_group_node_width = 140
    # normalmaptonormal_1 interface

    # Socket Normal Output
    normal_output_socket = normalmaptonormal_1.interface.new_socket(name="Normal Output", in_out='OUTPUT', socket_type='NodeSocketVector')
    normal_output_socket.default_value = (0.0, 0.0, 0.0)
    normal_output_socket.min_value = -3.4028234663852886e+38
    normal_output_socket.max_value = 3.4028234663852886e+38
    normal_output_socket.subtype = 'NONE'
    normal_output_socket.attribute_domain = 'POINT'
    normal_output_socket.default_input = 'VALUE'
    normal_output_socket.structure_type = 'AUTO'

    # Socket Strength
    strength_socket = normalmaptonormal_1.interface.new_socket(name="Strength", in_out='INPUT', socket_type='NodeSocketFloat')
    strength_socket.default_value = 1.0
    strength_socket.min_value = 0.0
    strength_socket.max_value = 10.0
    strength_socket.subtype = 'NONE'
    strength_socket.attribute_domain = 'POINT'
    strength_socket.description = "Strength of the normal mapping effect"
    strength_socket.default_input = 'VALUE'
    strength_socket.structure_type = 'AUTO'

    # Socket Texture Input
    texture_input_socket = normalmaptonormal_1.interface.new_socket(name="Texture Input", in_out='INPUT', socket_type='NodeSocketColor')
    texture_input_socket.default_value = (0.5, 0.5, 1.0, 1.0)
    texture_input_socket.attribute_domain = 'POINT'
    texture_input_socket.description = "Color that encodes the normal map in the specified space"
    texture_input_socket.default_input = 'VALUE'
    texture_input_socket.structure_type = 'AUTO'

    # Initialize normalmaptonormal_1 nodes

    # Node 组输入
    ___ = normalmaptonormal_1.nodes.new("NodeGroupInput")
    ___.name = "组输入"

    # Node 组输出
    ____1 = normalmaptonormal_1.nodes.new("NodeGroupOutput")
    ____1.name = "组输出"
    ____1.is_active_output = True

    # Node 法线贴图
    ____ = normalmaptonormal_1.nodes.new("ShaderNodeNormalMap")
    ____.name = "法线贴图"
    ____.space = 'TANGENT'
    ____.uv_map = ""

    # Set locations
    normalmaptonormal_1.nodes["组输入"].location = (-260.0, 0.0)
    normalmaptonormal_1.nodes["组输出"].location = (80.0, 0.0)
    normalmaptonormal_1.nodes["法线贴图"].location = (-100.0, 0.0)

    # Set dimensions
    normalmaptonormal_1.nodes["组输入"].width  = 140.0
    normalmaptonormal_1.nodes["组输入"].height = 100.0

    normalmaptonormal_1.nodes["组输出"].width  = 140.0
    normalmaptonormal_1.nodes["组输出"].height = 100.0

    normalmaptonormal_1.nodes["法线贴图"].width  = 150.0
    normalmaptonormal_1.nodes["法线贴图"].height = 100.0


    # Initialize normalmaptonormal_1 links

    # ___.Strength -> ____.Strength
    normalmaptonormal_1.links.new(
        normalmaptonormal_1.nodes["组输入"].outputs[0],
        normalmaptonormal_1.nodes["法线贴图"].inputs[0]
    )
    # ___.Texture Input -> ____.Color
    normalmaptonormal_1.links.new(
        normalmaptonormal_1.nodes["组输入"].outputs[1],
        normalmaptonormal_1.nodes["法线贴图"].inputs[1]
    )
    # ____.Normal -> ____1.Normal Output
    normalmaptonormal_1.links.new(
        normalmaptonormal_1.nodes["法线贴图"].outputs[0],
        normalmaptonormal_1.nodes["组输出"].inputs[0]
    )

    return normalmaptonormal_1


if __name__ == "__main__":
    # Maps node tree creation functions to the node tree 
    # name, such that we don't recreate node trees unnecessarily
    node_tree_names : dict[typing.Callable, str] = {}

    normalmaptonormal = normalmaptonormal_1_node_group(node_tree_names)
    node_tree_names[normalmaptonormal_1_node_group] = normalmaptonormal.name

