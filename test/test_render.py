import sys
import os

# resolve all paths relative to this script's directory so it works anywhere
script_dir = os.path.dirname(os.path.abspath(__file__))
project_dir = os.path.abspath(os.path.join(script_dir, "..", ".."))

# add blender_libs for numpy DLLs required by Blender 4.5
sys.path.insert(0, os.path.join(project_dir, "blender_libs"))
# EXTENSION load our local modified sim2real_docs at position 0 so it overrides all other copies
sys.path.insert(0, os.path.join(project_dir, "sim2real-docs"))

import bpy
from sim2real_docs.render_docs import get_image_renderings

input_path = os.path.join(script_dir, "pdf_input_6")
save_path = os.path.join(script_dir, "..", "outputs", "test_validated")

# Reduce Cycles samples for faster batch rendering
bpy.context.scene.cycles.samples = 64

print("Starting render...")

get_image_renderings(
    input_path=input_path,
    save_path=save_path,
    configs_path=os.path.join(script_dir, "config_blender45_natural.json")
)

print("Done! Check render_images folder.")
