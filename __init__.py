import bpy
from bpy.props import (
    BoolProperty,
    FloatProperty,
    IntProperty,
)

# Import the main function in the way that works for both add-on and library usages
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from arrange_nodes import arrange_nodes

bl_info = {
    "name": "Node Layout",
    "author": "Yuki Koyama",
    "version": (0, 3),
    "blender": (2, 80, 0),
    "location": "Shader Editor, Compositor, Texture Node Editor > Node",
    "description": "Automatic layout of node trees",
    "warning": "",
    "support": "TESTING",
    "wiki_url": "https://github.com/yuki-koyama/nodelayout",
    "tracker_url": "https://github.com/yuki-koyama/nodelayout/issues",
    "category": "Node"
}


class NODELAYOUT_OP_ArrangeSelectedNodes(bpy.types.Operator):

    bl_idname = "node.arrange_selected_nodes"
    bl_label = "Node Auto Layout"
    bl_description = "Arrange selected nodes automatically"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context: bpy.types.Context):
        if bpy.context.space_data.type != "NODE_EDITOR":
            self.report({'ERROR'}, "Failed because no active node tree was found.")
            return {'CANCELLED'}

        if bpy.context.space_data.node_tree is None:
            self.report({'ERROR'}, "Failed because no active node tree was found.")
            return {'CANCELLED'}

        scene = context.scene

        target_nodes = [x for x in context.space_data.edit_tree.nodes if x.select]

        arrange_nodes(node_tree=context.space_data.edit_tree,
                      target_nodes=target_nodes,
                      use_current_layout_as_initial_guess=scene.nodelayout_prop_bool,
                      max_num_iters=scene.nodelayout_prop_int,
                      target_space=scene.nodelayout_prop_float)

        self.report({'INFO'}, "The node tree has been arranged.")
        return {'FINISHED'}


class NODELAYOUT_OP_ArrangeNodes(bpy.types.Operator):

    bl_idname = "node.arrange_nodes"
    bl_label = "Node Auto Layout"
    bl_description = "Arrange nodes automatically"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context: bpy.types.Context):
        if bpy.context.space_data.type != "NODE_EDITOR":
            self.report({'ERROR'}, "Failed because no active node tree was found.")
            return {'CANCELLED'}

        if bpy.context.space_data.node_tree is None:
            self.report({'ERROR'}, "Failed because no active node tree was found.")
            return {'CANCELLED'}

        scene = context.scene

        arrange_nodes(node_tree=context.space_data.edit_tree,
                      use_current_layout_as_initial_guess=scene.nodelayout_prop_bool,
                      max_num_iters=scene.nodelayout_prop_int,
                      target_space=scene.nodelayout_prop_float)

        self.report({'INFO'}, "The node tree has been arranged.")
        return {'FINISHED'}


class NODELAYOUT_PT_NodeLayoutPanel(bpy.types.Panel):

    bl_label = "Node Auto Layout"
    bl_space_type = 'NODE_EDITOR'
    bl_region_type = 'UI'
    bl_category = "Layout"

    @classmethod
    def poll(cls, context: bpy.types.Context):
        return True

    def draw_header(self, context: bpy.types.Context):
        layout = self.layout
        layout.label(text="", icon='PLUGIN')

    def draw(self, context: bpy.types.Context):
        layout = self.layout
        scene = context.scene

        layout.label(text="Parameters:")
        layout.prop(scene, "nodelayout_prop_int", text="#iterations")
        layout.prop(scene, "nodelayout_prop_float", text="Target space")
        layout.prop(scene, "nodelayout_prop_bool", text="Use current as initial")

        layout.label(text="Operations:")
        layout.operator(NODELAYOUT_OP_ArrangeNodes.bl_idname, text="Arrange all nodes")
        layout.operator(NODELAYOUT_OP_ArrangeSelectedNodes.bl_idname, text="Arrange selected nodes")


def menu_func(self, context: bpy.types.Context) -> None:
    self.layout.separator()
    self.layout.operator(NODELAYOUT_OP_ArrangeNodes.bl_idname)


classes = [
    NODELAYOUT_OP_ArrangeNodes,
    NODELAYOUT_OP_ArrangeSelectedNodes,
    NODELAYOUT_PT_NodeLayoutPanel,
]


def init_props() -> None:
    scene = bpy.types.Scene
    scene.nodelayout_prop_int = IntProperty(description="The number of iterations", default=500, min=0, max=5000)
    scene.nodelayout_prop_bool = BoolProperty(description="Use the current layout as an initial solution",
                                              default=False)
    scene.nodelayout_prop_float = FloatProperty(description="The target space between nodes",
                                                default=50.0,
                                                min=0.0,
                                                max=500.0)


def clear_props() -> None:
    scene = bpy.types.Scene
    del scene.nodelayout_prop_int
    del scene.nodelayout_prop_bool
    del scene.nodelayout_prop_float


def register():
    for cls in classes:
        bpy.utils.register_class(cls)
    bpy.types.NODE_MT_node.append(menu_func)
    init_props()


def unregister():
    clear_props()
    bpy.types.NODE_MT_node.remove(menu_func)
    for cls in classes:
        bpy.utils.unregister_class(cls)


if __name__ == "__main__":
    register()
