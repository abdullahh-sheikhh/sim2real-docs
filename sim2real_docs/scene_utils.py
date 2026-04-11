# Copyright FMR LLC <opensource@fidelity.com>
# SPDX-License-Identifier: Apache-2.0
"""
This script defines all methods that sets the scene to render an image
"""

import os
import bpy

# Path to optional CC0 tabletop/floor texture images.
# If this folder contains images, set_surface_background() will use them
# instead of the flat-color fallback. See Asset Guidance in documents/plan.md.
_TEXTURE_DIR = os.path.normpath(
    os.path.join(os.path.dirname(__file__), "..", "test", "surface_textures")
)
_IMG_EXTS = {".png", ".jpg", ".jpeg"}


class Scene:
    def __init__(self, scene_configs):
        self.scene_configs = scene_configs

    def clear_images(self):
        """
        The function clears the images in the data
        """
        for img in bpy.data.images:
            bpy.data.images.remove(img)

    def clear_meshes(self):
        """
        The function clears the meshes in the data
        """
        for mesh in list(bpy.data.meshes):
            bpy.data.meshes.remove(mesh)

    def clear_material(self):
        """
        The function clears the materials
        """
        for material in list(bpy.data.materials):
            bpy.data.materials.remove(material)

    def clear_scene(self):
        """
        Blender scene starts with a cube camera and a light object.
        Type of light is a parameter and will change on every iteration. Therefore the initial light objects are removed
        Cube object is deleted as it is not required.
        """
        initial_objects = []
        for collection in bpy.data.collections:
            for obj in collection.all_objects:
                initial_objects.append(obj.name)
        for o in bpy.data.objects:
            if o.name in initial_objects:
                o.select_set(True)
        # deleting all the selected objects
        bpy.ops.object.delete(use_global=False)
        self.clear_images()
        self.clear_light_points()
        self.clear_meshes()
        self.clear_material()
        # resetting the scene borders
        bpy.context.scene.render.border_min_x = 0
        bpy.context.scene.render.border_min_y = 0
        bpy.context.scene.render.border_max_x = 1
        bpy.context.scene.render.border_max_y = 1
        bpy.context.scene.render.use_crop_to_border = False
        # BUGFIX: was hardcoded to 1.0 (+1 EV = 2x brightness) on every render;
        # reset to neutral 0.0 so set_exposure() controls brightness per render
        bpy.context.scene.view_settings.exposure = 0.0
        bpy.context.scene.render.use_border = False
        bpy.context.scene.view_settings.look = "AgX - Base Contrast"

    def clear_light_points(self):
        """
        The function clears the light points in the data
        """
        lights = list(bpy.data.lights)
        for light in lights:
            bpy.data.lights.remove(light)

    def set_resolution(self):
        """
        Setting the resolution of the scene
        """
        bpy.context.scene.render.resolution_x = self.scene_configs.resolution_x
        bpy.context.scene.render.resolution_y = self.scene_configs.resolution_y
        # BUGFIX Blender 4.5 requires int for resolution_percentage not numpy float64
        bpy.context.scene.render.resolution_percentage = int(
            self.scene_configs.resolution_percentage
        )

    def set_render_engine(self):
        bpy.context.scene.render.engine = self.scene_configs.render_engine

    def set_color_mode(self):
        """
        Setting final image color mode - RGB, RGBA, BW
        """
        scene = bpy.context.scene
        render = scene.render
        render.image_settings.color_mode = self.scene_configs.color_mode

    def set_aspect_ratio(self):
        """
        Setting aspect ratio of the scene.
        """
        scene = bpy.context.scene
        render = scene.render
        render.pixel_aspect_x = self.scene_configs.aspect_ratio[0]
        render.pixel_aspect_y = self.scene_configs.aspect_ratio[1]

    def set_scene_crop(self):
        """
        Setting scene crop paramaters
        """
        bpy.context.scene.render.use_border = True
        bpy.context.scene.render.border_min_x = self.scene_configs.crop_min_x
        bpy.context.scene.render.border_min_y = self.scene_configs.crop_min_y
        bpy.context.scene.render.border_max_x = self.scene_configs.crop_max_x
        bpy.context.scene.render.border_max_y = self.scene_configs.crop_max_y
        bpy.context.scene.render.use_crop_to_border = True

    def set_contrast(self):
        bpy.context.scene.view_settings.look = self.scene_configs.contrast

    def set_exposure(self):
        """
        Apply sampled exposure value (EV stops) to the scene color management.
        0.0 = neutral, positive = brighter, negative = darker.
        Previously this was never called and clear_scene() always forced +1.0 EV.
        """
        bpy.context.scene.view_settings.exposure = float(self.scene_configs.exposure_value)

    def set_surface_background(self):
        """
        Creates a large flat plane simulating a real-world surface (desk, table).
        If test/surface_textures/ contains CC0 tabletop images, uses them for
        photorealistic surface appearance. Falls back to flat Principled BSDF
        color if no textures are present.
        """
        import random

        # EXTENSION procedural surface background using Principled BSDF material
        # EXTENSION randomized surface color and roughness simulate different real world materials
        surface_colors = [
            (0.95, 0.93, 0.88, 1.0),  # bright white paper
            (0.82, 0.76, 0.62, 1.0),  # manila / beige desk
            (0.70, 0.58, 0.40, 1.0),  # light pine wood
            (0.80, 0.80, 0.80, 1.0),  # neutral gray tabletop
            (0.55, 0.42, 0.28, 1.0),  # medium oak / brown desk
            (0.90, 0.88, 0.82, 1.0),  # cream / off-white surface
            (0.30, 0.22, 0.15, 1.0),  # dark walnut desk
            (0.20, 0.35, 0.22, 1.0),  # green felt / conference table
            (0.25, 0.30, 0.45, 1.0),  # blue denim / fabric surface
            (0.65, 0.63, 0.60, 1.0),  # concrete / stone table
            (0.45, 0.35, 0.30, 1.0),  # terracotta / red tile
            (0.88, 0.85, 0.78, 1.0),  # aged paper / parchment
        ]
        roughness = random.uniform(0.3, 0.95)

        # EXTENSION randomized ambient world fill light; kept low so key lamp dominates
        world = bpy.context.scene.world
        world.use_nodes = True
        bg_node = world.node_tree.nodes.get("Background")
        if bg_node:
            ambient_strength = random.uniform(0.10, 0.30)
            bg_node.inputs["Strength"].default_value = ambient_strength

        bpy.ops.mesh.primitive_plane_add(size=8.0, location=(0, 0, 0))
        plane = bpy.context.active_object

        mat = bpy.data.materials.new(name="SurfaceMaterial")
        mat.use_nodes = True
        bsdf = mat.node_tree.nodes["Principled BSDF"]
        bsdf.inputs["Roughness"].default_value = roughness

        # Use a real tabletop texture if available in test/surface_textures/
        texture_files = []
        if os.path.isdir(_TEXTURE_DIR):
            texture_files = [
                os.path.join(_TEXTURE_DIR, f)
                for f in os.listdir(_TEXTURE_DIR)
                if os.path.splitext(f)[1].lower() in _IMG_EXTS
            ]

        if texture_files:
            # EXTENSION CC0 PBR tabletop texture for photorealistic surface appearance
            tex_path = random.choice(texture_files)
            img_node = mat.node_tree.nodes.new("ShaderNodeTexImage")
            img_node.image = bpy.data.images.load(tex_path)
            # Tile texture: 8m plane with scale=3 gives ~2.7m per tile (realistic desk grain scale)
            tex_coord = mat.node_tree.nodes.new("ShaderNodeTexCoord")
            mapping = mat.node_tree.nodes.new("ShaderNodeMapping")
            mapping.inputs["Scale"].default_value = (3.0, 3.0, 1.0)
            mat.node_tree.links.new(tex_coord.outputs["UV"], mapping.inputs["Vector"])
            mat.node_tree.links.new(mapping.outputs["Vector"], img_node.inputs["Vector"])
            mat.node_tree.links.new(img_node.outputs["Color"], bsdf.inputs["Base Color"])
        else:
            # Fallback: flat procedural color when no textures present
            color = random.choice(surface_colors)
            bsdf.inputs["Base Color"].default_value = color

        plane.data.materials.append(mat)
        bpy.ops.object.select_all(action="DESELECT")