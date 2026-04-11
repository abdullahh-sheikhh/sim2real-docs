# Copyright FMR LLC <opensource@fidelity.com>
# SPDX-License-Identifier: Apache-2.0
"""
The scripts create a synthetic images for documents.
"To run the script you need to install the package (package name yet to be decided), run the function get_image_rendering to get rendered images"
"""

import os
import json
from pathlib import Path

from .config import (
    get_configuration_parameters,
    parameter_file,
    run_background_check,
    get_sample_variations,
)
from .utils import (
    install_addons,
    render_scene,
    set_render_device,
    set_render_viewport,
    add_n_scale_background_image,
    get_collection_name,
    check_path_exists,
    create_dir,
    clear_segmentation_nodes,
    image_3d_to_2d_coords,
)

# === FIX: camera-space validation using world_to_camera_view ===
# Replaces validate_and_resample_geometry (disabled in config.py) which:
#   - confused sensor axes for portrait resolutions (overestimated FOV by ~7%)
#   - used a fixed BASE_DOC=1.1 that does not match real document plane sizes
#   - ran before the Blender scene existed (could not use actual projection)
#   - ignored image X/Y rotation which expands the projected corner footprint
#
# This validation runs AFTER camera and document are placed in the scene.
# Uses world_to_camera_view as ground truth — no geometric approximations.

_CONSTRAINT_MARGIN = 0.05          # corners must be this far inside crop edge
_CAM_Z_MAX_FACTOR  = 1.30          # camera z may increase at most 30%
_DOC_PLANE_Z       = 0.25          # image_utils.py line 22: image_object.location[2] = 0.25
_SCALE_MIN_FLOOR   = 0.40          # never shrink image below this absolute scale

# Accumulated per-render validation results; read by external test scripts.
_VALIDATION_LOG = []


def _get_ndc_metrics(image_obj, bpy_scene):
    """Return (x_min, x_max, y_min, y_max) NDC for all 4 document corners."""
    from bpy_extras.object_utils import world_to_camera_view
    corners = image_obj.get_image_coordinates()
    xs, ys = [], []
    for c in corners:
        ndc = world_to_camera_view(bpy_scene, bpy_scene.camera, c)
        xs.append(ndc.x)
        ys.append(ndc.y)
    return min(xs), max(xs), min(ys), max(ys)


def _check_constraints(x_min, x_max, y_min, y_max, scene_var,
                       original_cam_z, final_cam_z):
    """Evaluate all 5 constraints. Returns (passed_bool, details_dict).
    All values are cast to native Python types for JSON serialisation."""
    cmin_x, cmax_x = float(scene_var.crop_min_x), float(scene_var.crop_max_x)
    cmin_y, cmax_y = float(scene_var.crop_min_y), float(scene_var.crop_max_y)
    m = _CONSTRAINT_MARGIN
    x_min, x_max = float(x_min), float(x_max)
    y_min, y_max = float(y_min), float(y_max)

    c1 = bool(x_min >= cmin_x     and x_max <= cmax_x     and
              y_min >= cmin_y     and y_max <= cmax_y)
    c2 = bool(x_min >= cmin_x + m and x_max <= cmax_x - m and
              y_min >= cmin_y + m and y_max <= cmax_y - m)

    cx = (x_min + x_max) / 2.0
    cy = (y_min + y_max) / 2.0
    c3 = bool(0.40 <= cx <= 0.60 and 0.40 <= cy <= 0.60)

    crop_w = max(cmax_x - cmin_x, 1e-6)
    crop_h = max(cmax_y - cmin_y, 1e-6)
    area   = ((x_max - x_min) / crop_w) * ((y_max - y_min) / crop_h)
    c4 = bool(0.30 <= area <= 0.85)

    cam_inc = float(final_cam_z) / max(float(original_cam_z), 1e-6)
    c5 = bool(cam_inc <= _CAM_Z_MAX_FACTOR)

    passed = bool(c1 and c2 and c3 and c4 and c5)
    details = {
        "c1_no_clip":     c1,
        "c2_margin":      c2,
        "c3_centering":   c3,
        "c4_scale_area":  c4,
        "c5_cam_realism": c5,
        "x_min": round(x_min, 4), "x_max": round(x_max, 4),
        "y_min": round(y_min, 4), "y_max": round(y_max, 4),
        "center_x": round(cx, 4), "center_y": round(cy, 4),
        "area_fraction": round(float(area), 4),
        "cam_z_increase": round(cam_inc, 4),
        "crop": [round(cmin_x, 4), round(cmax_x, 4),
                 round(cmin_y, 4), round(cmax_y, 4)],
    }
    return passed, details


def _ensure_document_in_frame(camera_obj, image_obj, scene_var,
                               original_cam_z, max_attempts=10):
    """
    Enforces all 4 document corners project inside the crop region with safety
    margin, respecting the 30% camera-Z increase limit.

    Per attempt:
      - Compute scale factor to bring violating corners to (crop_limit - MARGIN).
      - If ideal new camera_z <= original_z * 1.3 → move camera only.
      - Otherwise → cap camera at original_z * 1.3, shrink image scale for rest.

    Returns (x_min, x_max, y_min, y_max) NDC after all corrections.
    """
    import bpy
    import math

    cmin_x, cmax_x = scene_var.crop_min_x, scene_var.crop_max_x
    cmin_y, cmax_y = scene_var.crop_min_y, scene_var.crop_max_y
    m = _CONSTRAINT_MARGIN

    t_min_x, t_max_x = cmin_x + m, cmax_x - m
    t_min_y, t_max_y = cmin_y + m, cmax_y - m
    z_max_allowed    = original_cam_z * _CAM_Z_MAX_FACTOR

    for attempt in range(max_attempts):
        bpy_scene = bpy.context.scene
        x_min, x_max, y_min, y_max = _get_ndc_metrics(image_obj, bpy_scene)

        all_ok = (x_min >= t_min_x and x_max <= t_max_x and
                  y_min >= t_min_y and y_max <= t_max_y)
        if all_ok:
            if attempt > 0:
                print("[FIX] attempt={}: all corners inside crop+margin".format(attempt))
            break

        # Scale factor needed to pull violating corners to their target
        max_scale = 1.0
        for val, limit, outer in [
            (x_max, t_max_x, True),  (x_min, t_min_x, False),
            (y_max, t_max_y, True),  (y_min, t_min_y, False),
        ]:
            if outer and val > limit:
                max_scale = max(max_scale, (val - 0.5) / max(limit - 0.5, 1e-6))
            elif not outer and val < limit:
                max_scale = max(max_scale, (0.5 - val) / max(0.5 - limit, 1e-6))

        current_z = camera_obj.location[2]
        ideal_z   = current_z * max_scale * 1.02   # 2% extra safety

        if ideal_z <= z_max_allowed:
            camera_obj.location[2] = ideal_z
            _off = (ideal_z - _DOC_PLANE_Z) * math.tan(camera_obj.rotation_euler[0])
            camera_obj.location[0] = _off * math.sin(camera_obj.rotation_euler[2])
            camera_obj.location[1] = -_off * math.cos(camera_obj.rotation_euler[2])
            print("[FIX] attempt={}: cam_z {:.3f}->{:.3f}".format(
                attempt, current_z, ideal_z))
        else:
            # Cap camera z and compensate with image scale reduction
            camera_obj.location[2] = z_max_allowed
            _off = (z_max_allowed - _DOC_PLANE_Z) * math.tan(camera_obj.rotation_euler[0])
            camera_obj.location[0] = _off * math.sin(camera_obj.rotation_euler[2])
            camera_obj.location[1] = -_off * math.cos(camera_obj.rotation_euler[2])
            depth_old      = current_z    - _DOC_PLANE_Z
            depth_new      = z_max_allowed - _DOC_PLANE_Z
            cam_factor     = depth_new / max(depth_old, 1e-6)
            remaining      = (max_scale * 1.02) / cam_factor
            if remaining > 1.0:
                cur_sx = image_obj.image_object.scale[0]
                cur_sy = image_obj.image_object.scale[1]
                new_sx = max(cur_sx / remaining, _SCALE_MIN_FLOOR)
                new_sy = max(cur_sy / remaining, _SCALE_MIN_FLOOR)
                image_obj.image_object.scale[0] = new_sx
                image_obj.image_object.scale[1] = new_sy
                print("[FIX] attempt={}: z capped={:.3f}, scale ({:.3f},{:.3f})->({:.3f},{:.3f})".format(
                    attempt, z_max_allowed, cur_sx, cur_sy, new_sx, new_sy))
            else:
                print("[FIX] attempt={}: cam_z capped at {:.3f}".format(
                    attempt, z_max_allowed))

        bpy.context.view_layer.update()

    else:
        print("[FIX] WARNING: margin constraint unsatisfied after {} attempts".format(max_attempts))

    x_min, x_max, y_min, y_max = _get_ndc_metrics(image_obj, bpy.context.scene)
    return x_min, x_max, y_min, y_max
# === END FIX ===

from .run_variations import (
    run_camera_settings,
    run_image_settings,
    run_light_settings,
    run_scene_settings,
)

current_dir = Path(__file__).parent
default_config_path = os.path.join(current_dir, "default_config.json")


def get_configuration_file(user_configs: str, user_all_configs: str):
    """
    Decides on the configuration file to use.
    """
    if user_configs == None and user_all_configs == None:
        with open(default_config_path) as f:
            default_config = json.load(f)
        return default_config, "range"
    elif user_configs != None and user_all_configs == None:
        with open(user_configs) as f:
            user_configs_values = json.load(f)
        return user_configs_values, "range"
    elif user_configs == None and user_all_configs != None:
        with open(user_all_configs) as f:
            user_configs_values = json.load(f)
        return user_configs_values, "all"


def get_image_renderings(
    input_path: str,
    save_path: str,
    add_on_paths: dict = None,
    bg_images_path: str = None,
    seg_path: str = None,
    configs_path: str = None,
    all_configurations: str = None,
):
    """
    Runs blender rendering for the images or files present in the path
        1) identifies number of images present in the given folder
        2) create random variations - light, camera, image, scene
        3) renders an image
        4) clears the scene
        5) saves the metadata
    """
    check_path_exists(input_path)
    create_dir(save_path)
    # background images
    bg_images = run_background_check(bg_images_path)
    # determining configuration files
    configurations, config_type = get_configuration_file(
        configs_path, all_configurations
    )
    (
        image_files,
        variations_required,
        scene_variations,
        light_variations,
        camera_variations,
        image_variations,
        other_parameters,
    ) = get_configuration_parameters(
        input_path,
        configs_params=configurations,
        configuration_type=config_type,
        background_images_list=bg_images,
    )
    install_addons(add_on_paths)
    set_render_device(other_parameters.render_device_type)
    set_render_viewport()
    for i in range(variations_required):
        print("Rendering image - {}".format(image_variations[i].image_name))
        scene = run_scene_settings(scene_variation=scene_variations[i])
        scene_col = get_collection_name()
        camera = run_camera_settings(
            camera_variation=camera_variations[i], collection_name=scene_col
        )  # camera settings
        _ = run_light_settings(light_variation=light_variations[i])  # light settings
        image_2d_coords, image_obj = run_image_settings(
            image_variation=image_variations[i],
            path=input_path,
            scene_variations=scene_variations[i],
        )
        # === FIX: camera-space validation ===
        original_cam_z = camera_variations[i].camera_z_location
        x_min, x_max, y_min, y_max = _ensure_document_in_frame(
            camera.camera_object, image_obj, scene_variations[i], original_cam_z
        )
        # BUGFIX: write corrected camera Z and image scale back to named tuples before metadata export
        camera_variations[i] = camera_variations[i]._replace(
            camera_z_location=camera.camera_object.location[2]
        )
        image_variations[i] = image_variations[i]._replace(
            image_x_scale=image_obj.image_object.scale[0],
            image_y_scale=image_obj.image_object.scale[1],
        )
        # Recompute 2D coordinates after camera / scale may have changed
        image_3d_coords = image_obj.get_image_coordinates()
        image_2d_coords = image_3d_to_2d_coords(image_3d_coords, scene_variations[i])
        # Log constraint results for post-run analysis
        passed, details = _check_constraints(
            x_min, x_max, y_min, y_max,
            scene_variations[i], original_cam_z,
            camera.camera_object.location[2],
        )
        details["image_name"] = image_variations[i].image_name
        details["pass"] = passed
        _VALIDATION_LOG.append(details)
        status_str = "PASS" if passed else "FAIL"
        print("[VALIDATE] {} | {} | area={:.2f} cam_inc={:.2f}x".format(
            status_str, image_variations[i].image_name,
            details["area_fraction"], details["cam_z_increase"]))
        # === END FIX ===
        # updating the named tuple to add bounding boxes of document in the final rendered image
        image_variations[i] = image_variations[i]._replace(image_bbs=image_2d_coords)
        # segmentation check
        if seg_path != None:
            check_path_exists(seg_path)
            nodes_present = image_obj.get_segmentation_images(
                seg_path, scene_variations[i]
            )
        # background images
        if len(bg_images) > 0:
            add_n_scale_background_image(image_variations[i], bg_images_path)
        # rendering the image
        render_scene(
            save_path, image_files[i], camera.camera_object.name
        )  # render the scene
        if seg_path != None:
            clear_segmentation_nodes(seg_path, nodes_present)
        scene.clear_scene()  # clear the scene
    # saving the parameters file
    parameter_file(
        scene_params=scene_variations,
        light_params=light_variations,
        camera_params=camera_variations,
        image_params=image_variations,
        save_path=save_path,
        n_variations=variations_required,
        other_params=other_parameters,
    )
    # === FIX: save validation log ===
    validation_path = os.path.join(save_path, "validation_log.json")
    with open(validation_path, "w") as _vf:
        json.dump(_VALIDATION_LOG, _vf, indent=2)
    n_pass = sum(1 for r in _VALIDATION_LOG if r.get("pass"))
    print("[VALIDATE] FINAL: {}/{} renders PASS all constraints".format(
        n_pass, len(_VALIDATION_LOG)))
    # === END FIX ===


def load_config(image_path, image_name=None, bg_path=None, config_file=None):
    (
        scene_params,
        light_params,
        camera_params,
        other_params,
        image_params,
    ) = get_sample_variations(image_path, image_name, bg_path, config_file)
    index = 0
    install_addons()
    set_render_device(other_params.render_device_type)
    set_render_viewport()
    scene_col = get_collection_name()
    scene = run_scene_settings(scene_variation=scene_params[index])
    camera = run_camera_settings(
        camera_variation=camera_params[index], collection_name=scene_col
    )
    light = run_light_settings(light_variation=light_params[index])
    _, image = run_image_settings(
        image_variation=image_params[index],
        path=image_path,
        scene_variations=scene_params[index],
    )
    if image_params[index].background_image_name != "":
        add_n_scale_background_image(image_params[index], bg_path)
    return light.light_object, camera.camera_object, image.image_object
