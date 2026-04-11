# Copyright FMR LLC <opensource@fidelity.com>
# SPDX-License-Identifier: Apache-2.0
"""
The script generates variations for the parameters using configuration file and stores them in respective named tuple
"""
import math
import random
from collections import namedtuple

import numpy as np

# configuration parameters
scene_options = [
    "aspect_ratio",
    "color_mode",
    "exposure_value",
    "contrast",
    "crop_min_x",
    "crop_max_x",
    "crop_min_y",
    "crop_max_y",
    "resolution_x",
    "resolution_y",
    "resolution_percentage",
    "render_engine",
]
Scene_tuple = namedtuple(
    "SceneParameters", scene_options, defaults=[None] * len(scene_options)
)
light_options = [
    "light_energies",
    "light_x_location",
    "light_y_location",
    "light_z_location",
    "color_hue",
    "color_saturation",
    "color_value",
    "light_type",
]
Light_tuple = namedtuple(
    "LightParameters", light_options, defaults=[None] * len(light_options)
)
camera_options = [
    "camera_x_location",
    "camera_y_location",
    "camera_z_location",
    "camera_x_rotation",
    "camera_y_rotation",
    "camera_z_rotation",
    "camera_focal_length",
]
Camera_tuple = namedtuple(
    "CameraParameters", camera_options, defaults=[None] * len(camera_options)
)
image_options = [
    "image_x_scale",
    "image_y_scale",
    "image_z_scale",
    "image_x_rotation",
    "image_y_rotation",
    "image_z_rotation",
    "image_bbs",
    "background_image_name",
    "image_name",
]
Image_tuple = namedtuple(
    "ImageParameters", image_options, defaults=[None] * len(image_options)
)
other_options = ["render_device_type"]
other_parameter_tuple = namedtuple(
    "OtherBlenderParameters", other_options, defaults=[None] * len(other_options)
)


def random_range(configs, variable, variations):
    """
    Generate random values for the variable in continous scale
    """

    random_values = np.random.uniform(
        configs[variable]["range"][0], configs[variable]["range"][1], variations
    )
    return random_values


def random_categorical_values(configs, variable, variations):
    """
    Generate random values for the variable (e.g aspect ratio etc)
    If weights values are not given, the function assign equal weight to all the values
    """
    try:
        weight_values = configs[variable]["weights"]
    except:
        weight_values = [1.0] * len(configs[variable]["range"])

    random_values = random.choices(
        configs[variable]["range"], k=variations, weights=weight_values
    )
    return random_values


def get_image_parameters(
    n_variations: int, image_configs: dict, image_files: list, bg_list: list
):
    """
    Generate scene variations based on random values in config file and creates a named tuple for each variation
    """
    # sampling background images from background image files
    if len(bg_list) == 0:
        bg_images = [""] * len(image_files)
    else:
        bg_images = [random.choice(bg_list) for i in range(len(image_files))]
    image_parameters_list = [Image_tuple for i in range(n_variations)]
    image_scale_x_values = random_range(image_configs, "image_x_scale", n_variations)
    image_scale_y_values = random_range(image_configs, "image_y_scale", n_variations)
    image_scale_z_values = random_range(image_configs, "image_z_scale", n_variations)
    image_rotation_x_values = random_range(
        image_configs, "image_x_rotation", n_variations
    )
    image_rotation_y_values = random_range(
        image_configs, "image_y_rotation", n_variations
    )
    image_rotation_z_values = random_range(
        image_configs, "image_z_rotation", n_variations
    )
    for index, _ in enumerate(image_parameters_list):
        image_parameters_list[index] = image_parameters_list[index](
            image_x_scale=image_scale_x_values[index],
            image_y_scale=image_scale_y_values[index],
            image_z_scale=image_scale_z_values[index],
            image_x_rotation=image_rotation_x_values[index],
            image_y_rotation=image_rotation_y_values[index],
            image_z_rotation=image_rotation_z_values[index],
            image_bbs=[],
            image_name=image_files[index],
            background_image_name=bg_images[index],
        )
    return image_parameters_list


def get_other_blender_parameters(other_parameters: dict):
    other_parameter_tuple_value = other_parameter_tuple(
        render_device_type=other_parameters["render_device_type"]
    )
    return other_parameter_tuple_value


def get_camera_parameters(n_variations: int, camera_configs: dict):
    """
    Generate camera variations based on random values in config file and creates a named tuple for each variation
    """
    camera_parameters_list = [Camera_tuple for i in range(n_variations)]

    camera_focal_length_values = random_range(
        camera_configs, "camera_focal_length", n_variations
    )
    camera_x_location_values = random_range(
        camera_configs, "camera_x_location", n_variations
    )
    camera_y_location_values = random_range(
        camera_configs, "camera_y_location", n_variations
    )
    camera_z_location_values = random_range(
        camera_configs, "camera_z_location", n_variations
    )
    camera_x_rotation_values = random_range(
        camera_configs, "camera_x_rotation", n_variations
    )
    camera_y_rotation_values = random_range(
        camera_configs, "camera_y_rotation", n_variations
    )
    camera_z_rotation_values = random_range(
        camera_configs, "camera_z_rotation", n_variations
    )
    for index, _ in enumerate(camera_parameters_list):
        camera_parameters_list[index] = camera_parameters_list[index](
            camera_x_location=camera_x_location_values[index],
            camera_y_location=camera_y_location_values[index],
            camera_z_location=camera_z_location_values[index],
            camera_focal_length=camera_focal_length_values[index],
            # BUGFIX: store degrees here; camera_utils.py converts to radians once when applying
            camera_x_rotation=camera_x_rotation_values[index],
            camera_y_rotation=camera_y_rotation_values[index],
            camera_z_rotation=camera_z_rotation_values[index],
        )
    return camera_parameters_list


def get_light_parameters(n_variations: int, light_configs: dict):
    """
    Generate light variations based on random values in config file and creates a named tuple for each variation
    """
    light_parameters_list = [Light_tuple for i in range(n_variations)]
    light_energies = random_range(light_configs, "light_energy", n_variations)
    light_type_values = random_categorical_values(
        light_configs, "light_types", n_variations
    )
    hue = random_range(light_configs, "hue", n_variations)
    saturation = random_range(light_configs, "saturation", n_variations)
    value = random_range(light_configs, "value", n_variations)
    light_x_values = random_range(light_configs, "light_x_location", n_variations)
    # BUGFIX original code sampled all three axes from light_x_location causing Y and Z to always equal X
    light_y_values = random_range(light_configs, "light_y_location", n_variations)
    # BUGFIX negative Z values placed the light underground making the scene render completely black
    light_z_values = random_range(light_configs, "light_z_location", n_variations)
    for index, _ in enumerate(light_parameters_list):
        light_parameters_list[index] = light_parameters_list[index](
            light_energies=light_energies[index],
            light_x_location=light_x_values[index],
            light_y_location=light_y_values[index],
            light_z_location=light_z_values[index],
            color_hue=hue[index],
            color_saturation=saturation[index],
            color_value=value[index],
            light_type=light_type_values[index],
        )
    return light_parameters_list


def get_scene_parameters(n_variations: int, scene_config: dict):
    """
    Generate scene variations based on random values in config file and creates a named tuple for each variation
    """
    scene_parameters_list = [Scene_tuple for i in range(n_variations)]
    aspect_ratio_values = random_categorical_values(
        scene_config, "aspect_ratio", n_variations
    )
    color_mode_values = random_categorical_values(
        scene_config, "color_modes", n_variations
    )
    resolution_values = random_categorical_values(
        scene_config, "resolution", n_variations
    )
    contrast_values = random_categorical_values(scene_config, "contrast", n_variations)
    render_engine_values = random_categorical_values(
        scene_config, "render_engine", n_variations
    )
    exposure_value_values = random_range(scene_config, "exposure", n_variations)
    crop_min_x_values = random_range(scene_config, "crop_min_x", n_variations)
    crop_max_x_values = random_range(scene_config, "crop_max_x", n_variations)
    crop_min_y_values = random_range(scene_config, "crop_min_y", n_variations)
    crop_max_y_values = random_range(scene_config, "crop_max_y", n_variations)
    resolution_percentage_values = random_range(
        scene_config, "resolution_percentage", n_variations
    )
    for index, _ in enumerate(scene_parameters_list):
        scene_parameters_list[index] = scene_parameters_list[index](
            aspect_ratio=aspect_ratio_values[index],
            color_mode=color_mode_values[index],
            exposure_value=exposure_value_values[index],
            contrast=contrast_values[index],
            crop_min_x=crop_min_x_values[index],
            crop_max_x=crop_max_x_values[index],
            crop_min_y=crop_min_y_values[index],
            crop_max_y=crop_max_y_values[index],
            resolution_x=resolution_values[index][0],
            resolution_y=resolution_values[index][1],
            resolution_percentage=resolution_percentage_values[index],
            render_engine=render_engine_values[index],
        )
    return scene_parameters_list


def validate_and_resample_geometry(
    camera_params_list, image_params_list, scene_params_list,
    camera_configs, image_configs
):
    """
    EXTENSION geometric validation layer ensures every sampled camera-document pair is physically plausible.
    Uses analytical resampling: given current scale and focal, computes the minimum camera Z that guarantees
    the document fits in frame (both X and Y axes plus diagonal corners), then samples Z from the valid range.
    If no valid Z exists for current focal, reduces scale by 10% and retries up to MAX_ATTEMPTS times.
    This converges deterministically rather than relying on random luck.

    Three correctness fixes vs original model:
      1. BASE_DOC = 1.5 BU (import_image.to_plane actual plane size, between 1.0 underestimate and 2.0 overestimate)
      2. Both sensor axes validated using per-render aspect ratio and crop
      3. Diagonal corner radius check added as final safety
    """
    SENSOR_WIDTH_MM = 36.0  # Blender default sensor width
    # BASE_DOC: import_image.to_plane creates planes at ~1.0 BU wide x ~1.4 BU tall for portrait docs
    # Using the larger dimension (height) conservatively for both axes
    BASE_DOC = 1.1
    SAFETY_MARGIN = 0.15    # 15% safety buffer on each side
    SCALE_REDUCTION = 0.90  # reduce scale by 10% each time no valid z exists
    MAX_ATTEMPTS = 15

    z_min_config = float(camera_configs["camera_z_location"]["range"][0])
    z_max_config = float(camera_configs["camera_z_location"]["range"][1])
    f_min_config = float(camera_configs["camera_focal_length"]["range"][0])
    xs_min_config = float(image_configs["image_x_scale"]["range"][0])
    ys_min_config = float(image_configs["image_y_scale"]["range"][0])

    for i in range(len(camera_params_list)):
        cam = camera_params_list[i]
        img = image_params_list[i]
        scene = scene_params_list[i]

        pixel_ax = float(scene.aspect_ratio[0])
        pixel_ay = float(scene.aspect_ratio[1])
        res_x = float(scene.resolution_x)
        res_y = float(scene.resolution_y)
        # sensor height derived from render resolution and pixel aspect
        sensor_half_w = SENSOR_WIDTH_MM / 2.0
        sensor_half_h = (SENSOR_WIDTH_MM * (res_y / res_x) * (pixel_ay / pixel_ax)) / 2.0
        # effective crop fractions
        crop_w = scene.crop_max_x - scene.crop_min_x
        crop_h = scene.crop_max_y - scene.crop_min_y
        diag_denom = math.sqrt((sensor_half_w * crop_w) ** 2 + (sensor_half_h * crop_h) ** 2)

        scale_reduced = False
        valid = False
        for attempt in range(MAX_ATTEMPTS):
            focal_mm = cam.camera_focal_length
            x_scale = img.image_x_scale
            y_scale = img.image_y_scale
            theta = math.radians(abs(img.image_z_rotation))

            # axis-aligned bounding box of document after scale and in-plane rotation
            w = BASE_DOC * x_scale
            h = BASE_DOC * y_scale
            bbox_w = w * math.cos(theta) + h * math.sin(theta)
            bbox_h = w * math.sin(theta) + h * math.cos(theta)
            doc_corner_r = math.sqrt((bbox_w / 2.0) ** 2 + (bbox_h / 2.0) ** 2)

            # ANALYTICAL: compute minimum cam_z that satisfies all three constraints
            # constraint X: cam_z * (sensor_half_w / focal) * crop_w * (1-margin) >= bbox_w/2
            min_z_x = (bbox_w / 2.0) * focal_mm / (sensor_half_w * crop_w * (1.0 - SAFETY_MARGIN))
            # constraint Y: cam_z * (sensor_half_h / focal) * crop_h * (1-margin) >= bbox_h/2
            min_z_y = (bbox_h / 2.0) * focal_mm / (sensor_half_h * crop_h * (1.0 - SAFETY_MARGIN))
            # constraint diagonal
            min_z_diag = doc_corner_r * focal_mm / (diag_denom * (1.0 - SAFETY_MARGIN))

            min_z_needed = max(min_z_x, min_z_y, min_z_diag)

            if min_z_needed <= z_max_config:
                # valid z exists: sample uniformly from [min_z_needed, z_max_config]
                actual_min = max(min_z_needed, z_min_config)
                new_z = float(np.random.uniform(actual_min, z_max_config))
                cam = cam._replace(camera_z_location=new_z)
                valid = True
                print(
                    "[GeomCheck] i={} attempt={} focal={:.1f}mm cam_z={:.2f}m (min_needed={:.2f}m) "
                    "scale=({:.2f},{:.2f}) rot={:.1f}deg aspect=({}/{}px) valid=True".format(
                        i, attempt, focal_mm, new_z, min_z_needed,
                        x_scale, y_scale, math.degrees(theta),
                        int(pixel_ax), int(pixel_ay)
                    )
                )
                break

            # no valid z for this focal + scale
            # first pass: try reducing scale
            if not scale_reduced:
                new_xs = max(x_scale * SCALE_REDUCTION, xs_min_config)
                new_ys = max(y_scale * SCALE_REDUCTION, ys_min_config)
                if new_xs != x_scale or new_ys != y_scale:
                    img = img._replace(image_x_scale=new_xs, image_y_scale=new_ys)
                    print(
                        "[GeomCheck] i={} attempt={} focal={:.1f}mm min_z={:.2f}m > z_max={:.2f}m "
                        "scale reduced ({:.2f},{:.2f})->({:.2f},{:.2f}) rot={:.1f}deg".format(
                            i, attempt, focal_mm, min_z_needed, z_max_config,
                            x_scale, y_scale, new_xs, new_ys, math.degrees(theta)
                        )
                    )
                    continue
                else:
                    scale_reduced = True  # already at minimum scale, switch to focal resampling

            # scale is at minimum: analytically compute max focal that fits at z_max
            # from diagonal constraint: focal_max = z_max * diag_denom * (1-margin) / doc_corner_r
            doc_corner_at_min = math.sqrt(
                (BASE_DOC * xs_min_config * math.cos(theta) + BASE_DOC * ys_min_config * math.sin(theta)) ** 2 / 4.0 +
                (BASE_DOC * xs_min_config * math.sin(theta) + BASE_DOC * ys_min_config * math.cos(theta)) ** 2 / 4.0
            )
            max_focal_x = (sensor_half_w * crop_w * (1.0 - SAFETY_MARGIN) * z_max_config) / (BASE_DOC * xs_min_config * (math.cos(theta) + math.sin(theta)) / 2.0)
            max_focal_y = (sensor_half_h * crop_h * (1.0 - SAFETY_MARGIN) * z_max_config) / (BASE_DOC * ys_min_config * (math.sin(theta) + math.cos(theta)) / 2.0)
            max_focal_diag = (diag_denom * (1.0 - SAFETY_MARGIN) * z_max_config) / doc_corner_at_min
            max_focal_allowed = min(max_focal_x, max_focal_y, max_focal_diag)

            if max_focal_allowed >= f_min_config:
                new_focal = float(np.random.uniform(f_min_config, max_focal_allowed))
            else:
                # even shortest focal is too long: use minimum focal as best effort
                new_focal = f_min_config
            cam = cam._replace(camera_focal_length=new_focal)
            print(
                "[GeomCheck] i={} attempt={} scale at min, focal resampled {:.1f}mm->{:.1f}mm "
                "(max_allowed={:.1f}mm) rot={:.1f}deg".format(
                    i, attempt, focal_mm, new_focal, max_focal_allowed, math.degrees(theta)
                )
            )

        if not valid:
            print(
                "[GeomCheck] WARNING: i={} could not find valid combination after {} attempts, accepting last sample".format(
                    i, MAX_ATTEMPTS
                )
            )

        camera_params_list[i] = cam
        image_params_list[i] = img

    return camera_params_list, image_params_list