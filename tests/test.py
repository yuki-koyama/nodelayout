# blender test-nodes.blend --background --python test.py

import bpy
import sys
import os

sys.path.append(os.path.dirname(os.path.abspath(__file__) + "../.."))
import nodelayout

material = bpy.data.materials["Material"]
nodelayout.arrange_nodes(material.node_tree, verbose=True)
