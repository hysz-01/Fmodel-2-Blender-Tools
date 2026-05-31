import bpy
import mathutils
import os
import typing


def __________1_node_group(node_tree_names: dict[typing.Callable, str]):
    """Initialize 三角函数计算第三值 node group"""
    __________1 = bpy.data.node_groups.new(type = 'ShaderNodeTree', name = "三角函数计算第三值")

    __________1.color_tag = 'CONVERTER'
    __________1.description = ""
    __________1.default_group_node_width = 140
    # __________1 interface

    # Socket c
    c_socket = __________1.interface.new_socket(name="c", in_out='OUTPUT', socket_type='NodeSocketFloat')
    c_socket.default_value = 0.0
    c_socket.min_value = -3.4028234663852886e+38
    c_socket.max_value = 3.4028234663852886e+38
    c_socket.subtype = 'NONE'
    c_socket.attribute_domain = 'POINT'
    c_socket.default_input = 'VALUE'
    c_socket.structure_type = 'AUTO'

    # Socket a
    a_socket = __________1.interface.new_socket(name="a", in_out='INPUT', socket_type='NodeSocketFloat')
    a_socket.default_value = 0.5
    a_socket.min_value = -10000.0
    a_socket.max_value = 10000.0
    a_socket.subtype = 'NONE'
    a_socket.attribute_domain = 'POINT'
    a_socket.default_input = 'VALUE'
    a_socket.structure_type = 'AUTO'

    # Socket b
    b_socket = __________1.interface.new_socket(name="b", in_out='INPUT', socket_type='NodeSocketFloat')
    b_socket.default_value = 0.5
    b_socket.min_value = -10000.0
    b_socket.max_value = 10000.0
    b_socket.subtype = 'NONE'
    b_socket.attribute_domain = 'POINT'
    b_socket.default_input = 'VALUE'
    b_socket.structure_type = 'AUTO'

    # Initialize __________1 nodes

    # Node Group Output
    group_output = __________1.nodes.new("NodeGroupOutput")
    group_output.name = "Group Output"
    group_output.is_active_output = True

    # Node Group Input
    group_input = __________1.nodes.new("NodeGroupInput")
    group_input.name = "Group Input"

    # Node Math.001
    math_001 = __________1.nodes.new("ShaderNodeMath")
    math_001.name = "Math.001"
    math_001.operation = 'POWER'
    math_001.use_clamp = False
    # Value_001
    math_001.inputs[1].default_value = 2.0

    # Node Math.002
    math_002 = __________1.nodes.new("ShaderNodeMath")
    math_002.name = "Math.002"
    math_002.operation = 'POWER'
    math_002.use_clamp = False
    # Value_001
    math_002.inputs[1].default_value = 2.0

    # Node Math.003
    math_003 = __________1.nodes.new("ShaderNodeMath")
    math_003.name = "Math.003"
    math_003.operation = 'ADD'
    math_003.use_clamp = False

    # Node Math.004
    math_004 = __________1.nodes.new("ShaderNodeMath")
    math_004.name = "Math.004"
    math_004.operation = 'SUBTRACT'
    math_004.use_clamp = False
    # Value
    math_004.inputs[0].default_value = 1.0

    # Node Math.005
    math_005 = __________1.nodes.new("ShaderNodeMath")
    math_005.name = "Math.005"
    math_005.operation = 'SQRT'
    math_005.use_clamp = False

    # Node Map Range
    map_range = __________1.nodes.new("ShaderNodeMapRange")
    map_range.label = "Map (0,1) to (-1,1)"
    map_range.name = "Map Range"
    map_range.hide = True
    map_range.clamp = False
    map_range.data_type = 'FLOAT'
    map_range.interpolation_type = 'LINEAR'
    map_range.inputs[1].hide = True
    map_range.inputs[2].hide = True
    map_range.inputs[3].hide = True
    map_range.inputs[4].hide = True
    map_range.inputs[5].hide = True
    map_range.inputs[6].hide = True
    map_range.inputs[7].hide = True
    map_range.inputs[8].hide = True
    map_range.inputs[9].hide = True
    map_range.inputs[10].hide = True
    map_range.inputs[11].hide = True
    map_range.outputs[1].hide = True
    # From Min
    map_range.inputs[1].default_value = 0.0
    # From Max
    map_range.inputs[2].default_value = 1.0
    # To Min
    map_range.inputs[3].default_value = -1.0
    # To Max
    map_range.inputs[4].default_value = 1.0

    # Node Map Range.001
    map_range_001 = __________1.nodes.new("ShaderNodeMapRange")
    map_range_001.label = "Map (0,1) to (-1,1)"
    map_range_001.name = "Map Range.001"
    map_range_001.hide = True
    map_range_001.clamp = False
    map_range_001.data_type = 'FLOAT'
    map_range_001.interpolation_type = 'LINEAR'
    map_range_001.inputs[1].hide = True
    map_range_001.inputs[2].hide = True
    map_range_001.inputs[3].hide = True
    map_range_001.inputs[4].hide = True
    map_range_001.inputs[5].hide = True
    map_range_001.inputs[6].hide = True
    map_range_001.inputs[7].hide = True
    map_range_001.inputs[8].hide = True
    map_range_001.inputs[9].hide = True
    map_range_001.inputs[10].hide = True
    map_range_001.inputs[11].hide = True
    map_range_001.outputs[1].hide = True
    # From Min
    map_range_001.inputs[1].default_value = 0.0
    # From Max
    map_range_001.inputs[2].default_value = 1.0
    # To Min
    map_range_001.inputs[3].default_value = -1.0
    # To Max
    map_range_001.inputs[4].default_value = 1.0

    # Node Math
    math = __________1.nodes.new("ShaderNodeMath")
    math.name = "Math"
    math.operation = 'MAXIMUM'
    math.use_clamp = False
    # Value_001
    math.inputs[1].default_value = 0.0

    # Set locations
    __________1.nodes["Group Output"].location = (560.0, 80.0)
    __________1.nodes["Group Input"].location = (-580.0, 80.0)
    __________1.nodes["Math.001"].location = (-240.0, 80.0)
    __________1.nodes["Math.002"].location = (-240.0, -80.0)
    __________1.nodes["Math.003"].location = (-80.0, 80.0)
    __________1.nodes["Math.004"].location = (80.0, 80.0)
    __________1.nodes["Math.005"].location = (400.0, 80.0)
    __________1.nodes["Map Range"].location = (-400.0, 80.0)
    __________1.nodes["Map Range.001"].location = (-400.0, 40.0)
    __________1.nodes["Math"].location = (240.0, 80.0)

    # Set dimensions
    __________1.nodes["Group Output"].width  = 140.0
    __________1.nodes["Group Output"].height = 100.0

    __________1.nodes["Group Input"].width  = 140.0
    __________1.nodes["Group Input"].height = 100.0

    __________1.nodes["Math.001"].width  = 140.0
    __________1.nodes["Math.001"].height = 100.0

    __________1.nodes["Math.002"].width  = 140.0
    __________1.nodes["Math.002"].height = 100.0

    __________1.nodes["Math.003"].width  = 140.0
    __________1.nodes["Math.003"].height = 100.0

    __________1.nodes["Math.004"].width  = 140.0
    __________1.nodes["Math.004"].height = 100.0

    __________1.nodes["Math.005"].width  = 140.0
    __________1.nodes["Math.005"].height = 100.0

    __________1.nodes["Map Range"].width  = 140.0
    __________1.nodes["Map Range"].height = 100.0

    __________1.nodes["Map Range.001"].width  = 140.0
    __________1.nodes["Map Range.001"].height = 100.0

    __________1.nodes["Math"].width  = 140.0
    __________1.nodes["Math"].height = 100.0


    # Initialize __________1 links

    # math_002.Value -> math_003.Value
    __________1.links.new(
        __________1.nodes["Math.002"].outputs[0],
        __________1.nodes["Math.003"].inputs[1]
    )
    # math_001.Value -> math_003.Value
    __________1.links.new(
        __________1.nodes["Math.001"].outputs[0],
        __________1.nodes["Math.003"].inputs[0]
    )
    # math_003.Value -> math_004.Value
    __________1.links.new(
        __________1.nodes["Math.003"].outputs[0],
        __________1.nodes["Math.004"].inputs[1]
    )
    # math.Value -> math_005.Value
    __________1.links.new(
        __________1.nodes["Math"].outputs[0],
        __________1.nodes["Math.005"].inputs[0]
    )
    # map_range.Result -> math_001.Value
    __________1.links.new(
        __________1.nodes["Map Range"].outputs[0],
        __________1.nodes["Math.001"].inputs[0]
    )
    # map_range_001.Result -> math_002.Value
    __________1.links.new(
        __________1.nodes["Map Range.001"].outputs[0],
        __________1.nodes["Math.002"].inputs[0]
    )
    # group_input.a -> map_range.Value
    __________1.links.new(
        __________1.nodes["Group Input"].outputs[0],
        __________1.nodes["Map Range"].inputs[0]
    )
    # group_input.b -> map_range_001.Value
    __________1.links.new(
        __________1.nodes["Group Input"].outputs[1],
        __________1.nodes["Map Range.001"].inputs[0]
    )
    # math_004.Value -> math.Value
    __________1.links.new(
        __________1.nodes["Math.004"].outputs[0],
        __________1.nodes["Math"].inputs[0]
    )
    # math_005.Value -> group_output.c
    __________1.links.new(
        __________1.nodes["Math.005"].outputs[0],
        __________1.nodes["Group Output"].inputs[0]
    )

    return __________1


def decodedxt5_1_node_group(node_tree_names: dict[typing.Callable, str]):
    """Initialize DecodeDXT5 node group"""
    decodedxt5_1 = bpy.data.node_groups.new(type = 'ShaderNodeTree', name = "DecodeDXT5")

    decodedxt5_1.color_tag = 'CONVERTER'
    decodedxt5_1.description = ""
    decodedxt5_1.default_group_node_width = 140
    # decodedxt5_1 interface

    # Socket Texture Output
    texture_output_socket = decodedxt5_1.interface.new_socket(name="Texture Output", in_out='OUTPUT', socket_type='NodeSocketColor')
    texture_output_socket.default_value = (0.800000011920929, 0.800000011920929, 0.800000011920929, 1.0)
    texture_output_socket.attribute_domain = 'POINT'
    texture_output_socket.default_input = 'VALUE'
    texture_output_socket.structure_type = 'AUTO'

    # Socket Texture Input
    texture_input_socket = decodedxt5_1.interface.new_socket(name="Texture Input", in_out='INPUT', socket_type='NodeSocketColor')
    texture_input_socket.default_value = (0.5, 0.5, 0.0, 1.0)
    texture_input_socket.attribute_domain = 'POINT'
    texture_input_socket.default_input = 'VALUE'
    texture_input_socket.structure_type = 'AUTO'

    # Socket Alpha Input
    alpha_input_socket = decodedxt5_1.interface.new_socket(name="Alpha Input", in_out='INPUT', socket_type='NodeSocketFloat')
    alpha_input_socket.default_value = 1.0
    alpha_input_socket.min_value = -10000.0
    alpha_input_socket.max_value = 10000.0
    alpha_input_socket.subtype = 'NONE'
    alpha_input_socket.attribute_domain = 'POINT'
    alpha_input_socket.default_input = 'VALUE'
    alpha_input_socket.structure_type = 'AUTO'

    # Initialize decodedxt5_1 nodes

    # Node 组输出
    ___ = decodedxt5_1.nodes.new("NodeGroupOutput")
    ___.name = "组输出"
    ___.is_active_output = True

    # Node 组输入
    ____1 = decodedxt5_1.nodes.new("NodeGroupInput")
    ____1.name = "组输入"

    # Node Combine Color.002
    combine_color_002 = decodedxt5_1.nodes.new("ShaderNodeCombineColor")
    combine_color_002.name = "Combine Color.002"
    combine_color_002.mode = 'RGB'

    # Node Separate Color.002
    separate_color_002 = decodedxt5_1.nodes.new("ShaderNodeSeparateColor")
    separate_color_002.name = "Separate Color.002"
    separate_color_002.mode = 'RGB'

    # Node Group.002
    group_002 = decodedxt5_1.nodes.new("ShaderNodeGroup")
    group_002.name = "Group.002"
    group_002.node_tree = bpy.data.node_groups[node_tree_names[__________1_node_group]]

    # Node 转接点
    ____2 = decodedxt5_1.nodes.new("NodeReroute")
    ____2.name = "转接点"
    ____2.socket_idname = "NodeSocketFloat"
    # Set locations
    decodedxt5_1.nodes["组输出"].location = (400.0, 20.0)
    decodedxt5_1.nodes["组输入"].location = (-380.0, 20.0)
    decodedxt5_1.nodes["Combine Color.002"].location = (200.0, 20.0)
    decodedxt5_1.nodes["Separate Color.002"].location = (-180.0, 20.0)
    decodedxt5_1.nodes["Group.002"].location = (20.0, 20.0)
    decodedxt5_1.nodes["转接点"].location = (-40.0, 40.0)

    # Set dimensions
    decodedxt5_1.nodes["组输出"].width  = 140.0
    decodedxt5_1.nodes["组输出"].height = 100.0

    decodedxt5_1.nodes["组输入"].width  = 140.0
    decodedxt5_1.nodes["组输入"].height = 100.0

    decodedxt5_1.nodes["Combine Color.002"].width  = 140.0
    decodedxt5_1.nodes["Combine Color.002"].height = 100.0

    decodedxt5_1.nodes["Separate Color.002"].width  = 140.0
    decodedxt5_1.nodes["Separate Color.002"].height = 100.0

    decodedxt5_1.nodes["Group.002"].width  = 120.0
    decodedxt5_1.nodes["Group.002"].height = 100.0

    decodedxt5_1.nodes["转接点"].width  = 14.5
    decodedxt5_1.nodes["转接点"].height = 100.0


    # Initialize decodedxt5_1 links

    # separate_color_002.Green -> combine_color_002.Green
    decodedxt5_1.links.new(
        decodedxt5_1.nodes["Separate Color.002"].outputs[1],
        decodedxt5_1.nodes["Combine Color.002"].inputs[1]
    )
    # combine_color_002.Color -> ___.Texture Output
    decodedxt5_1.links.new(
        decodedxt5_1.nodes["Combine Color.002"].outputs[0],
        decodedxt5_1.nodes["组输出"].inputs[0]
    )
    # ____2.Output -> combine_color_002.Red
    decodedxt5_1.links.new(
        decodedxt5_1.nodes["转接点"].outputs[0],
        decodedxt5_1.nodes["Combine Color.002"].inputs[0]
    )
    # ____1.Texture Input -> separate_color_002.Color
    decodedxt5_1.links.new(
        decodedxt5_1.nodes["组输入"].outputs[0],
        decodedxt5_1.nodes["Separate Color.002"].inputs[0]
    )
    # group_002.c -> combine_color_002.Blue
    decodedxt5_1.links.new(
        decodedxt5_1.nodes["Group.002"].outputs[0],
        decodedxt5_1.nodes["Combine Color.002"].inputs[2]
    )
    # ____1.Alpha Input -> ____2.Input
    decodedxt5_1.links.new(
        decodedxt5_1.nodes["组输入"].outputs[1],
        decodedxt5_1.nodes["转接点"].inputs[0]
    )
    # ____2.Output -> group_002.a
    decodedxt5_1.links.new(
        decodedxt5_1.nodes["转接点"].outputs[0],
        decodedxt5_1.nodes["Group.002"].inputs[0]
    )
    # separate_color_002.Green -> group_002.b
    decodedxt5_1.links.new(
        decodedxt5_1.nodes["Separate Color.002"].outputs[1],
        decodedxt5_1.nodes["Group.002"].inputs[1]
    )

    return decodedxt5_1


if __name__ == "__main__":
    # Maps node tree creation functions to the node tree 
    # name, such that we don't recreate node trees unnecessarily
    node_tree_names : dict[typing.Callable, str] = {}

    _________ = __________1_node_group(node_tree_names)
    node_tree_names[__________1_node_group] = _________.name

    decodedxt5 = decodedxt5_1_node_group(node_tree_names)
    node_tree_names[decodedxt5_1_node_group] = decodedxt5.name

