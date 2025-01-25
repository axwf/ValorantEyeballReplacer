bl_info = {
    "name": "Valorant Eye Replacer",
    "blender": (2, 80, 0),
    "category": "Object",
    "author": "Brainez Visuals // Max Goldblatt",
    "description": "Allows user to quickly change default eyes on Valorant characters to those in a selected directory.",
    "location": "View3D > Tool Shelf > Valo Eye Replacer",
    "license": "GPL",
    "version": (1, 0, 0)
}

import bpy
import math
import bmesh
from bpy.types import Operator, AddonPreferences, PropertyGroup
from bpy.props import StringProperty, CollectionProperty

# Global Variables
rig = None
mesh = None
rig_select = False
mesh_select = False
l_data = None #Rotation & Loc data for Left eye
r_data = None #Rotation & Loc data for Right eye


def remove_eyes(mesh, group_name, weight_threshold=0.01):
    """Deletes the Eye Mesh from the model"""
    
    bpy.context.view_layer.objects.active = mesh
    bpy.ops.object.mode_set(mode='OBJECT')

    # Get the vertex group
    group = mesh.vertex_groups.get(group_name)
    if group is None:
        print(f"Vertex group '{group_name}' not found!")
        return

    # Use bmesh for more reliable operations
    bpy.ops.object.mode_set(mode='EDIT')
    bm = bmesh.from_edit_mesh(mesh.data)

    # Find and delete vertices based on group weights
    vertices_to_delete = []
    for vertex in bm.verts:
        for group_element in mesh.data.vertices[vertex.index].groups:
            if group_element.group == group.index and group_element.weight > weight_threshold:
                vertices_to_delete.append(vertex)
                break

    # Delete the vertices
    bmesh.ops.delete(bm, geom=vertices_to_delete, context='VERTS')
    bmesh.update_edit_mesh(mesh.data)

    bpy.ops.object.mode_set(mode='OBJECT')
    
    return


def BoneInfo(rig, bone_name):
    """Returns Bone Location & Rotations"""
    # Find bone
    bone = rig.pose.bones.get(bone_name)
    
    #Get Location     
    bone_location = rig.matrix_world @ bone.head
    
    #Get rotation
    bone_rotation = rig.matrix_world.to_quaternion().inverted() @ bone.matrix_basis.to_quaternion()
    
    # Optionally, convert the rotation to Euler angles (in radians)
    bone_rotation_euler = bone_rotation.to_euler()
    
    # Return the bone data as a dictionary
    return {
        "bone_name": bone_name,
        "location": bone_location,
        "location_x": bone_location.x,
        "location_y": bone_location.y,
        "location_z": bone_location.z,
        "rotation_x": bone_rotation.x,
        "rotation_y": bone_rotation.y,
        "rotation_z": bone_rotation.z,
        "rotation_euler": bone_rotation_euler,
        "rotation_euler_x": bone_rotation_euler.x,
        "rotation_euler_y": bone_rotation_euler.y,
        "rotation_euler_z": bone_rotation_euler.z
    }
    
    
def append_eyes(blend_file_path, l_data, r_data, rig):
    """Appends object from eye file into scene"""
    
    # List to hold each eye object
    eyes_list = []
    
    for i in range (2):
        # Link Blender file objects into blend file
        with bpy.data.libraries.load(blend_file_path, link = False) as (data_from, data_to):
            data_to.objects = data_from.objects
        
        scene = bpy.context.scene
        # Add into scene
        for obj in data_to.objects:
            if obj is None:
                continue    
            scene.collection.objects.link(obj)
            eyes_list.append(obj)
    
    #Moves left eye in right location & rotation & constraints
    left_eye = eyes_list[0]
    left_eye.location = l_data["location"]
    left_eye.rotation_euler = l_data["rotation_euler"]
    left_eye.rotation_euler.z = math.radians(90)
    
    child_of_constraint_left = left_eye.constraints.new(type='CHILD_OF')
    child_of_constraint_left.target = rig
    child_of_constraint_left.subtarget = l_data["bone_name"]

    #Moves right eye in right location & rotation & constraints
    right_eye = eyes_list[1]
    right_eye.location = r_data["location"]
    right_eye.rotation_euler = r_data["rotation_euler"]
    right_eye.rotation_euler.z = math.radians(90)
    
    child_of_constraint_right = right_eye.constraints.new(type='CHILD_OF')
    child_of_constraint_right.target = rig  # Replace with the armature name
    child_of_constraint_right.subtarget = r_data["bone_name"]  # Set the specific bone name
     
    return


class ValorantEyeReplacerPreferences(bpy.types.AddonPreferences):
    """Folder Preferences"""
    # Set bl_idname to match the name of your addon module
    bl_idname = "valo_eye_replacer"

    folder_path: bpy.props.StringProperty(
        name="Eye Directory (.blend)",
        description="File containing replacement eyeball .blend file",
        default="",
        subtype='FILE_PATH',
    )

    def draw(self, context):
        layout = self.layout
        layout.prop(self, "folder_path")


class ReplaceEyes(bpy.types.Operator):
    """Removes Eyes & Replaces them // Main Function Class"""
    bl_idname = "object.replace_eyes"
    bl_label = "Replace Eyes"
    bl_description = "Removes eyes & replaces them with user-selected eyes."
    
    def execute(self, context):
        global mesh, rig, mesh_select, rig_select, l_data, r_data
        
        addon_prefs = bpy.context.preferences.addons["valo_eye_replacer"].preferences
        folder_path = addon_prefs.folder_path
        
        
        if mesh is None or rig is None:
            self.report({'WARNING'}, "Please select both a mesh and an armature.")
            
            return {'CANCELLED'}
        
        if folder_path:
            #Functions to Remove Eyes
            remove_eyes(mesh, "L_Eyeball")
            remove_eyes(mesh, "R_Eyeball")
            l_data = BoneInfo(rig, "L_Eyeball")
            r_data = BoneInfo(rig, "R_Eyeball")
            append_eyes(folder_path, l_data, r_data, rig)
        
            return {'FINISHED'}
        
        else:
            self.report({'WARNING'}, "Invalid or missing directory!")
            return {'CANCELLED'}
        

class GetRig(bpy.types.Operator):
    """Button to grab armature object"""
    bl_idname = "object.get_rig"
    bl_label = "Select Armature"
    bl_description = "Selects armature on model"

    def execute(self, context):
        global rig, rig_select, mesh
        if bpy.context.view_layer.objects.active != mesh:  # Ensures rig & mesh aren't same
            if bpy.context.view_layer.objects.active.type == 'ARMATURE':
                rig = bpy.context.view_layer.objects.active
                rig_select = True
            else:
                self.report({'WARNING'}, "The selected object is not an armature.")
        return {'FINISHED'}


class GetMesh(bpy.types.Operator):
    """Button to grab mesh object"""
    bl_idname = "object.get_mesh"
    bl_label = "Select Mesh"
    bl_description = "Selects mesh on model"
    
    def execute(self, context):
        global mesh, mesh_select, rig
        if bpy.context.view_layer.objects.active != rig:  # Ensures rig & mesh aren't same
            if bpy.context.view_layer.objects.active.type == 'MESH':
                mesh = bpy.context.view_layer.objects.active
                mesh_select = True
            else:
                self.report({'WARNING'}, "The selected object is not a mesh.")
        return {'FINISHED'}


class MainUIPanel(bpy.types.Panel):
    bl_label = "VALORANT Eye Replacer"
    bl_idname = "LightAdder"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "Valo Eye Replacer"  # Tab Name

    def draw(self, context):
        global rig, mesh, rig_select, mesh_select
        layout = self.layout
        scene = context.scene

        # Label1
        layout.label(text="VALORANT Eye Replacer")
        layout.label(text = "By @BrainezVisuals on X")
        
        # Row1 - Armature selection
        row1 = layout.row()
        row1.label(text="Select Armature:", icon= 'OUTLINER_DATA_ARMATURE')
        row1.operator("object.get_rig")
        
        rig_row = layout.row()
        if rig_select:
            rig_row.label(text="Active Armature: " + rig.name)
        
        # Row2 - Mesh selection
        row2 = layout.row()
        row2.label(text="Select Mesh:", icon = 'CUBE')
        row2.operator("object.get_mesh")
        
        mesh_row = layout.row()
        if mesh_select:
            mesh_row.label(text="Active Mesh: " + mesh.name)

        # Big render button
        row = layout.row()
        row.scale_y = 2.0
        row.operator("object.replace_eyes", icon = 'PLAY')
        
        row3 = layout.row()
        row3.label(text="v1.00")


class_list = (
    ValorantEyeReplacerPreferences,
    MainUIPanel,
    GetRig,
    GetMesh,
    ReplaceEyes,
)


def register():
    for cls in class_list:
        bpy.utils.register_class(cls)


def unregister():
    for cls in class_list:
        bpy.utils.unregister_class(cls)


if __name__ == "__main__":
    register()
