import sys
import os

script_dir = os.path.dirname(os.path.abspath(__file__))
project_dir = os.path.abspath(os.path.join(script_dir, "..", ".."))

sys.path.insert(0, os.path.join(project_dir, "blender_libs"))
sys.path.insert(0, os.path.join(project_dir, "sim2real-docs"))

import bpy
import sim2real_docs.scene_utils as _scene_utils

# Paper's original intent: flat color background, no PBR textures
_scene_utils._TEXTURE_DIR = "__disabled__"

from sim2real_docs.render_docs import get_image_renderings

input_path = os.path.join(script_dir, "pdf_input_6")
save_path = os.path.join(script_dir, "..", "outputs", "original")

bpy.context.scene.cycles.samples = 16

print("Starting ORIGINAL render (paper config, flat background)...")

get_image_renderings(
    input_path=input_path,
    save_path=save_path,
    configs_path=os.path.join(script_dir, "config_blender45.json")
)

print("Done! Outputs in outputs/original")