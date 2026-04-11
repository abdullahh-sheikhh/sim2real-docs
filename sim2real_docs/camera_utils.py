# Copyright FMR LLC <opensource@fidelity.com>
# SPDX-License-Identifier: Apache-2.0

"""
This script defines all methods that are applied to a camera object
"""

from collections import namedtuple
import bpy
import math

# Must match image_utils.py image_object.location[2] and render_docs._DOC_PLANE_Z
_DOC_PLANE_Z = 0.25


class Camera:
    def __init__(self, camera_configs: namedtuple, collection: str):
        camera = bpy.data.cameras.new("Camera")
        camera_object = bpy.data.objects.new("Camera", camera)
        bpy.data.collections[collection].objects.link(camera_object)
        scene = bpy.context.scene
        scene.camera = bpy.data.objects["Camera"]
        self.camera_configs = camera_configs
        self.camera_object = camera_object

    def set_camera_location(self):
        """
        Function sets the camera location.
        X and Y are offset to compensate for camera tilt (X rotation) combined
        with Z rotation so the camera always centres its view on the document
        plane at Z=_DOC_PLANE_Z regardless of orbit angle.

        Derivation: view direction after X-tilt theta then Z-rotation phi is
            (-sin(theta)*sin(phi), sin(theta)*cos(phi), -cos(theta))
        The ray from cam_pos hits Z=_DOC_PLANE_Z at t=(z-_DOC_PLANE_Z)/cos(theta), giving:
            focus_x = cam_x - (z-_DOC_PLANE_Z)*tan(theta)*sin(phi) = 0
            focus_y = cam_y + (z-_DOC_PLANE_Z)*tan(theta)*cos(phi) = 0
        Therefore:
            cam_x = base_x + (z-_DOC_PLANE_Z)*tan(theta)*sin(phi)
            cam_y = base_y - (z-_DOC_PLANE_Z)*tan(theta)*cos(phi)
        """
        tilt_rad  = math.radians(self.camera_configs.camera_x_rotation)
        z_rot_rad = math.radians(self.camera_configs.camera_z_rotation)
        z = self.camera_configs.camera_z_location
        offset = (z - _DOC_PLANE_Z) * math.tan(tilt_rad)
        # BUGFIX: tilt compensation decomposes offset by Z rotation so document
        # stays centred regardless of camera orbit angle around the scene
        self.camera_object.location[0] = self.camera_configs.camera_x_location + offset * math.sin(z_rot_rad)
        self.camera_object.location[1] = self.camera_configs.camera_y_location - offset * math.cos(z_rot_rad)
        self.camera_object.location[2] = z

    def set_camera_rotation(self):
        """
        Function sets the camera rotation.
        Angles are stored in degrees in the named tuple and converted once here.
        """
        self.camera_object.rotation_euler[0] = math.radians(self.camera_configs.camera_x_rotation)
        self.camera_object.rotation_euler[1] = math.radians(self.camera_configs.camera_y_rotation)
        self.camera_object.rotation_euler[2] = math.radians(self.camera_configs.camera_z_rotation)

    def set_focal_length(self):
        """
        Function sets the camera focal length
        """
        self.camera_object.data.lens = self.camera_configs.camera_focal_length