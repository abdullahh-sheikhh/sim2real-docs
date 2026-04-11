"""
Autonomous validation test — runs the pipeline on 10 documents and checks ALL
5 hard constraints using world_to_camera_view ground-truth projection.

Constraints checked per render:
  C1  No clipping:    all 4 corners inside [crop_min, crop_max]
  C2  Safe margin:    corners >= crop_limit +/- 0.05
  C3  Centering:      center_x in [0.40, 0.60], center_y in [0.40, 0.60]
  C4  Scale realism:  document bounding box 30%-85% of crop area
  C5  Camera realism: camera_z increased <= 30% from sampled value

Usage (run inside Blender):
  blender --background --python test_validate_full.py
"""

import sys
import os
import json
import random

script_dir  = os.path.dirname(os.path.abspath(__file__))
project_dir = os.path.abspath(os.path.join(script_dir, "..", ".."))

sys.path.insert(0, os.path.join(project_dir, "blender_libs"))
sys.path.insert(0, os.path.join(project_dir, "sim2real-docs"))

import bpy
from sim2real_docs import render_docs as rd

# ── configuration ────────────────────────────────────────────────────────────
INPUT_ALL   = os.path.join(script_dir, "pdf_input_images")
INPUT_10    = os.path.join(script_dir, "pdf_input_validate")   # 10-image subset
SAVE_PATH   = os.path.join(script_dir, "..", "outputs", "test_validated")
CONFIG_PATH = os.path.join(script_dir, "config_blender45_natural.json")
N_RENDERS   = 10
CYCLES_SAMPLES = 32   # fast for validation; increase for final quality renders

# ── build 10-image subset ────────────────────────────────────────────────────
valid_ext = {".png", ".jpg", ".jpeg", ".tif", ".tiff"}
all_imgs  = sorted([
    f for f in os.listdir(INPUT_ALL)
    if os.path.splitext(f)[1].lower() in valid_ext
])
random.seed(42)
chosen = random.sample(all_imgs, min(N_RENDERS, len(all_imgs)))

os.makedirs(INPUT_10, exist_ok=True)
for img in chosen:
    src = os.path.join(INPUT_ALL, img)
    dst = os.path.join(INPUT_10, img)
    if not os.path.exists(dst):
        import shutil
        shutil.copy2(src, dst)

print("=== Validation test: {} images ===".format(len(chosen)))
for img in chosen:
    print("  ", img)

# ── render ───────────────────────────────────────────────────────────────────
rd._VALIDATION_LOG.clear()
bpy.context.scene.cycles.samples = CYCLES_SAMPLES

rd.get_image_renderings(
    input_path=INPUT_10,
    save_path=SAVE_PATH,
    configs_path=CONFIG_PATH,
)

# ── read and print report ────────────────────────────────────────────────────
log_path = os.path.join(SAVE_PATH, "validation_log.json")
with open(log_path) as f:
    results = json.load(f)

CONSTRAINT_LABELS = {
    "c1_no_clip":     "C1 No-clip",
    "c2_margin":      "C2 Margin(0.05)",
    "c3_centering":   "C3 Centering",
    "c4_scale_area":  "C4 Scale(30-85%)",
    "c5_cam_realism": "C5 Cam-Z(<=30%)",
}

print("\n" + "="*72)
print("VALIDATION REPORT")
print("="*72)

n_pass = 0
for r in results:
    status = "PASS" if r["pass"] else "FAIL"
    if r["pass"]:
        n_pass += 1

    print("\n{} | {}".format(status, r["image_name"]))
    print("  NDC  x=[{:.4f},{:.4f}]  y=[{:.4f},{:.4f}]  center=({:.3f},{:.3f})".format(
        r["x_min"], r["x_max"], r["y_min"], r["y_max"],
        r["center_x"], r["center_y"]))
    print("  crop x=[{:.2f},{:.2f}]  y=[{:.2f},{:.2f}]  area={:.1%}  cam_z_inc={:.2f}x".format(
        r["crop"][0], r["crop"][1], r["crop"][2], r["crop"][3],
        r["area_fraction"], r["cam_z_increase"]))
    failures = [label for key, label in CONSTRAINT_LABELS.items() if not r.get(key, True)]
    if failures:
        print("  FAILED: {}".format(", ".join(failures)))
    else:
        print("  All constraints satisfied")

print("\n" + "="*72)
print("FINAL: {}/{} renders PASS all constraints".format(n_pass, len(results)))
print("="*72)

# Return non-zero exit code if any render failed (useful for CI)
if n_pass < len(results):
    sys.exit(1)
