import sys
import os

script_dir = os.path.dirname(os.path.abspath(__file__))
project_dir = os.path.abspath(os.path.join(script_dir, "..", ".."))

sys.path.insert(0, os.path.join(project_dir, "blender_libs"))
sys.path.insert(0, os.path.join(project_dir, "sim2real-docs"))

import bpy
from sim2real_docs.render_docs import get_image_renderings

input_path = os.path.join(script_dir, "pdf_input_6")
save_path = os.path.join(script_dir, "..", "outputs", "improved")

bpy.context.scene.cycles.samples = 16

print("Starting IMPROVED render...")

get_image_renderings(
    input_path=input_path,
    save_path=save_path,
    configs_path=os.path.join(script_dir, "config_blender45_natural.json")
)

print("Done! Outputs in outputs/improved")