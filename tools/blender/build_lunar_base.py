from __future__ import annotations

import argparse
import math
import random
import sys
from pathlib import Path

import bpy
import bmesh
from mathutils import Euler, Matrix, Vector


SEED = 240416
RNG = random.Random(SEED)
PROJECT_DIR = Path(__file__).resolve().parent
TERRAIN_COLOR_PATH = PROJECT_DIR / "lroc_color_16bit_srgb_8k.tif"
TERRAIN_HEIGHT_PATH = PROJECT_DIR / "ldem_64_uint.tif"
COLLECTIONS = [
    "Terrain",
    "Main_Base_Buildings",
    "Cooling_Towers",
    "Solar_Panels",
    "Astronauts",
    "Vehicles_and_Props",
    "Earth_Background",
]


def parse_args() -> argparse.Namespace:
    argv = sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else []
    p = argparse.ArgumentParser()
    p.add_argument("--output-dir", default=str(Path(__file__).resolve().parent))
    p.add_argument("--blend-name", default="lunar_base_cinematic_3d.blend")
    p.add_argument("--preview", action="store_true")
    p.add_argument("--preview-name", default="lunar_base_preview.png")
    p.add_argument("--export-glb", action="store_true")
    p.add_argument("--glb-name", default="lunar-base.glb")
    return p.parse_args(argv)


def smoothstep(edge0: float, edge1: float, value: float) -> float:
    if edge0 == edge1:
        return 1.0 if value >= edge1 else 0.0
    t = max(0.0, min(1.0, (value - edge0) / (edge1 - edge0)))
    return t * t * (3.0 - 2.0 * t)


def scene_setup():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene
    scene.unit_settings.system = "METRIC"
    scene.render.engine = "CYCLES"
    scene.cycles.samples = 96
    scene.cycles.preview_samples = 24
    scene.cycles.use_adaptive_sampling = True
    scene.cycles.use_denoising = True
    try:
        scene.cycles.denoiser = "OPENIMAGEDENOISE"
    except Exception:
        pass
    scene.render.resolution_x = 2560
    scene.render.resolution_y = 1440
    scene.view_settings.look = "AgX - High Contrast"
    scene.view_settings.exposure = 3.8
    world = bpy.data.worlds.new("Moon_World")
    world.use_nodes = True
    bg = world.node_tree.nodes["Background"]
    bg.inputs[0].default_value = (0.03, 0.03, 0.08, 1.0)
    bg.inputs[1].default_value = 1.8
    scene.world = world
    return scene


def ensure_collection(name: str, parent=None):
    col = bpy.data.collections.get(name) or bpy.data.collections.new(name)
    parent = parent or bpy.context.scene.collection
    if not any(c.name == name for c in parent.children):
        parent.children.link(col)
    return col


def move_to_collection(obj, collection):
    for col in list(obj.users_collection):
        if col != collection:
            col.objects.unlink(obj)
    if collection not in obj.users_collection:
        collection.objects.link(obj)


def assign_material(obj, material):
    if obj.type != "MESH":
        return
    if obj.data.materials:
        obj.data.materials[0] = material
    else:
        obj.data.materials.append(material)


def add_prim(kind, name, collection, location, rotation=(0, 0, 0), scale=(1, 1, 1), **kwargs):
    mesh = bpy.data.meshes.new(f"{name}_Mesh")
    bm = bmesh.new()
    if kind == "cube":
        bmesh.ops.create_cube(bm, size=2.0)
    elif kind == "plane":
        bmesh.ops.create_grid(bm, x_segments=1, y_segments=1, size=1.0)
    elif kind == "grid":
        x_segments = int(kwargs.get("x_subdivisions", 1))
        y_segments = int(kwargs.get("y_subdivisions", 1))
        size = float(kwargs.get("size", 1.0))
        bmesh.ops.create_grid(bm, x_segments=max(1, x_segments), y_segments=max(1, y_segments), size=size / 2.0)
    elif kind == "uv_sphere":
        segments = int(kwargs.get("segments", 16))
        ring_count = int(kwargs.get("ring_count", 8))
        radius = float(kwargs.get("radius", 1.0))
        bmesh.ops.create_uvsphere(bm, u_segments=max(3, segments), v_segments=max(3, ring_count), radius=radius)
    elif kind == "ico_sphere":
        subdivisions = int(kwargs.get("subdivisions", 1))
        radius = float(kwargs.get("radius", 1.0))
        bmesh.ops.create_icosphere(bm, subdivisions=max(0, subdivisions), radius=radius)
    elif kind == "cone":
        vertices = int(kwargs.get("vertices", 32))
        radius1 = float(kwargs.get("radius1", kwargs.get("radius", 1.0)))
        radius2 = float(kwargs.get("radius2", 0.0))
        depth = float(kwargs.get("depth", 2.0))
        bmesh.ops.create_cone(
            bm,
            segments=max(3, vertices),
            radius1=radius1,
            radius2=radius2,
            depth=depth,
        )
    elif kind == "cylinder":
        vertices = int(kwargs.get("vertices", 32))
        radius = float(kwargs.get("radius", 1.0))
        depth = float(kwargs.get("depth", 2.0))
        bmesh.ops.create_cone(
            bm,
            segments=max(3, vertices),
            radius1=radius,
            radius2=radius,
            depth=depth,
        )
    elif kind == "torus":
        major_segments = int(kwargs.get("major_segments", 24))
        minor_segments = int(kwargs.get("minor_segments", 12))
        major_radius = float(kwargs.get("major_radius", 1.0))
        minor_radius = float(kwargs.get("minor_radius", 0.25))
        bmesh.ops.create_torus(
            bm,
            major_segments=max(3, major_segments),
            minor_segments=max(3, minor_segments),
            major_radius=major_radius,
            minor_radius=minor_radius,
        )
    else:
        bm.free()
        raise ValueError(f"Unsupported primitive kind: {kind}")
    bm.to_mesh(mesh)
    bm.free()
    obj = bpy.data.objects.new(name, mesh)
    collection.objects.link(obj)
    obj.location = location
    obj.rotation_euler = rotation
    obj.scale = scale
    obj.name = name
    obj.data.name = f"{name}_Mesh"
    return obj


def add_empty(name, collection, location=(0, 0, 0), rotation=(0, 0, 0)):
    obj = bpy.data.objects.new(name, None)
    obj.location = location
    obj.rotation_euler = rotation
    collection.objects.link(obj)
    return obj


def smooth(obj):
    if obj.type == "MESH":
        for p in obj.data.polygons:
            p.use_smooth = True


def bevel(obj, width=0.06, segments=2):
    mod = obj.modifiers.new("Bevel", "BEVEL")
    mod.width = width
    mod.segments = segments
    mod.limit_method = "ANGLE"


def wnorm(obj):
    mod = obj.modifiers.new("WeightedNormal", "WEIGHTED_NORMAL")
    mod.keep_sharp = True


def mat(name, color, rough=0.5, metal=0.0, spec=0.5):
    m = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    m.use_nodes = True
    bsdf = m.node_tree.nodes["Principled BSDF"]
    bsdf.inputs["Base Color"].default_value = color
    bsdf.inputs["Roughness"].default_value = rough
    bsdf.inputs["Metallic"].default_value = metal
    spec_socket = bsdf.inputs.get("Specular IOR Level") or bsdf.inputs.get("Specular")
    if spec_socket is not None:
        spec_socket.default_value = spec
    return m


ROOT_COLLECTION = "Lunar_Base_Scene"
SUN_VECTOR = Vector((0.64, 0.52, -0.92)).normalized()
FOCUS_POINT = Vector((2.0, 2.0, 4.0))
CAMERA_LOCATION = Vector((-38.0, -74.0, 14.0))
EARTH_LOCATION = Vector((104.0, 98.0, 18.0))


def setup_world_and_render():
    scene = bpy.context.scene
    scene.render.engine = "CYCLES"
    scene.render.resolution_x = 2048
    scene.render.resolution_y = 858
    scene.render.resolution_percentage = 100
    scene.cycles.samples = 128
    scene.cycles.preview_samples = 32
    scene.cycles.use_adaptive_sampling = True
    scene.cycles.use_denoising = True
    scene.cycles.max_bounces = 8
    scene.cycles.diffuse_bounces = 4
    scene.cycles.glossy_bounces = 4
    scene.cycles.transmission_bounces = 8
    scene.cycles.volume_bounces = 2
    scene.view_settings.view_transform = "Filmic"
    for look in ("Medium High Contrast", "High Contrast", "None"):
        try:
            scene.view_settings.look = look
            break
        except Exception:
            pass
    scene.view_settings.exposure = 0.85
    if scene.world is None:
        scene.world = bpy.data.worlds.new("Moon_World")
    world = scene.world
    world.use_nodes = True
    bg = world.node_tree.nodes.get("Background")
    if bg is None:
        bg = world.node_tree.nodes.new("ShaderNodeBackground")
    bg.inputs[0].default_value = (0.005, 0.006, 0.01, 1.0)
    bg.inputs[1].default_value = 0.02


def clear_scene():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    setup_world_and_render()


def ensure_root():
    root = bpy.data.collections.get(ROOT_COLLECTION) or bpy.data.collections.new(ROOT_COLLECTION)
    if root.name not in bpy.context.scene.collection.children:
        bpy.context.scene.collection.children.link(root)
    collections = {"root": root}
    for name in COLLECTIONS:
        col = bpy.data.collections.get(name) or bpy.data.collections.new(name)
        if col.name not in root.children:
            root.children.link(col)
        collections[name] = col
    return collections


def new_material(name: str):
    m = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    for node in list(nt.nodes):
        nt.nodes.remove(node)
    return m


def load_local_image(path: Path, colorspace: str):
    if not path.exists():
        return None
    image = bpy.data.images.load(str(path), check_existing=True)
    try:
        image.colorspace_settings.name = colorspace
    except Exception:
        pass
    image.alpha_mode = "NONE"
    return image


def make_regolith_material():
    m = new_material("MAT_Regolith")
    n = m.node_tree.nodes
    l = m.node_tree.links
    out = n.new("ShaderNodeOutputMaterial")
    bsdf = n.new("ShaderNodeBsdfPrincipled")
    tex = n.new("ShaderNodeTexCoord")
    mapn = n.new("ShaderNodeMapping")
    noise = n.new("ShaderNodeTexNoise")
    tex_mix = n.new("ShaderNodeMixRGB")
    tex_ramp = n.new("ShaderNodeValToRGB")
    color_tex = n.new("ShaderNodeTexImage")
    height_tex = n.new("ShaderNodeTexImage")
    bump = n.new("ShaderNodeBump")
    bump_mix = n.new("ShaderNodeMath")
    ramp = n.new("ShaderNodeValToRGB")
    mapn.inputs["Scale"].default_value = (0.05, 0.05, 0.05)
    noise.inputs["Scale"].default_value = 3.0
    noise.inputs["Detail"].default_value = 9.0
    tex_mix.blend_type = "MULTIPLY"
    tex_mix.inputs["Fac"].default_value = 0.22
    tex_ramp.color_ramp.elements[0].position = 0.12
    tex_ramp.color_ramp.elements[1].position = 0.88
    tex_ramp.color_ramp.elements[0].color = (0.20, 0.20, 0.20, 1.0)
    tex_ramp.color_ramp.elements[1].color = (0.47, 0.46, 0.43, 1.0)
    ramp.color_ramp.elements[0].color = (0.09, 0.09, 0.10, 1.0)
    ramp.color_ramp.elements[1].color = (0.34, 0.33, 0.31, 1.0)
    bsdf.inputs["Roughness"].default_value = 0.94
    bsdf.inputs["Specular IOR Level"].default_value = 0.06
    bump_mix.operation = "MULTIPLY"
    bump_mix.inputs[1].default_value = 0.35
    color_tex.image = load_local_image(TERRAIN_COLOR_PATH, "sRGB")
    height_tex.image = load_local_image(TERRAIN_HEIGHT_PATH, "Non-Color")
    l.new(tex.outputs["Generated"], mapn.inputs["Vector"])
    l.new(mapn.outputs["Vector"], noise.inputs["Vector"])
    l.new(noise.outputs["Fac"], ramp.inputs["Fac"])
    l.new(ramp.outputs["Color"], tex_mix.inputs["Color1"])
    if color_tex.image is not None:
        l.new(tex.outputs["Generated"], color_tex.inputs["Vector"])
        l.new(color_tex.outputs["Color"], tex_ramp.inputs["Fac"])
        l.new(tex_ramp.outputs["Color"], tex_mix.inputs["Color2"])
    else:
        tex_mix.inputs["Color2"].default_value = (0.33, 0.32, 0.30, 1.0)
    l.new(tex_mix.outputs["Color"], bsdf.inputs["Base Color"])
    if height_tex.image is not None:
        l.new(tex.outputs["Generated"], height_tex.inputs["Vector"])
        l.new(height_tex.outputs["Color"], bump_mix.inputs[0])
        l.new(bump_mix.outputs["Value"], bump.inputs["Height"])
    else:
        l.new(noise.outputs["Fac"], bump.inputs["Height"])
    bump.inputs["Strength"].default_value = 0.18
    l.new(bump.outputs["Normal"], bsdf.inputs["Normal"])
    l.new(bsdf.outputs["BSDF"], out.inputs["Surface"])
    return m


def make_white_metal_material():
    m = new_material("MAT_White_Metal")
    n = m.node_tree.nodes
    l = m.node_tree.links
    out = n.new("ShaderNodeOutputMaterial")
    bsdf = n.new("ShaderNodeBsdfPrincipled")
    tex = n.new("ShaderNodeTexCoord")
    mapn = n.new("ShaderNodeMapping")
    noise = n.new("ShaderNodeTexNoise")
    ramp = n.new("ShaderNodeValToRGB")
    bump = n.new("ShaderNodeBump")
    mapn.inputs["Scale"].default_value = (0.25, 0.25, 0.25)
    noise.inputs["Scale"].default_value = 8.0
    ramp.color_ramp.elements[0].color = (0.52, 0.54, 0.56, 1.0)
    ramp.color_ramp.elements[1].color = (0.78, 0.79, 0.77, 1.0)
    bsdf.inputs["Metallic"].default_value = 0.08
    bsdf.inputs["Roughness"].default_value = 0.57
    bsdf.inputs["Specular IOR Level"].default_value = 0.36
    l.new(tex.outputs["Object"], mapn.inputs["Vector"])
    l.new(mapn.outputs["Vector"], noise.inputs["Vector"])
    l.new(noise.outputs["Fac"], ramp.inputs["Fac"])
    l.new(ramp.outputs["Color"], bsdf.inputs["Base Color"])
    l.new(noise.outputs["Fac"], bump.inputs["Height"])
    bump.inputs["Strength"].default_value = 0.03
    l.new(bump.outputs["Normal"], bsdf.inputs["Normal"])
    l.new(bsdf.outputs["BSDF"], out.inputs["Surface"])
    return m


def make_dark_metal_material():
    m = new_material("MAT_Dark_Metal")
    n = m.node_tree.nodes
    l = m.node_tree.links
    out = n.new("ShaderNodeOutputMaterial")
    bsdf = n.new("ShaderNodeBsdfPrincipled")
    tex = n.new("ShaderNodeTexCoord")
    mapn = n.new("ShaderNodeMapping")
    noise = n.new("ShaderNodeTexNoise")
    ramp = n.new("ShaderNodeValToRGB")
    bump = n.new("ShaderNodeBump")
    mapn.inputs["Scale"].default_value = (0.35, 0.35, 0.35)
    noise.inputs["Scale"].default_value = 10.0
    ramp.color_ramp.elements[0].color = (0.07, 0.07, 0.08, 1.0)
    ramp.color_ramp.elements[1].color = (0.22, 0.22, 0.24, 1.0)
    bsdf.inputs["Metallic"].default_value = 0.18
    bsdf.inputs["Roughness"].default_value = 0.55
    l.new(tex.outputs["Object"], mapn.inputs["Vector"])
    l.new(mapn.outputs["Vector"], noise.inputs["Vector"])
    l.new(noise.outputs["Fac"], ramp.inputs["Fac"])
    l.new(ramp.outputs["Color"], bsdf.inputs["Base Color"])
    l.new(noise.outputs["Fac"], bump.inputs["Height"])
    bump.inputs["Strength"].default_value = 0.02
    l.new(bump.outputs["Normal"], bsdf.inputs["Normal"])
    l.new(bsdf.outputs["BSDF"], out.inputs["Surface"])
    return m


def make_panel_material():
    m = new_material("MAT_Solar_Panel")
    n = m.node_tree.nodes
    l = m.node_tree.links
    out = n.new("ShaderNodeOutputMaterial")
    bsdf = n.new("ShaderNodeBsdfPrincipled")
    tex = n.new("ShaderNodeTexCoord")
    mapn = n.new("ShaderNodeMapping")
    checker = n.new("ShaderNodeTexChecker")
    noise = n.new("ShaderNodeTexNoise")
    bump = n.new("ShaderNodeBump")
    mapn.inputs["Scale"].default_value = (9.0, 4.0, 1.0)
    checker.inputs["Scale"].default_value = 12.0
    checker.inputs["Color1"].default_value = (0.02, 0.06, 0.13, 1.0)
    checker.inputs["Color2"].default_value = (0.06, 0.13, 0.24, 1.0)
    noise.inputs["Scale"].default_value = 4.0
    bsdf.inputs["Roughness"].default_value = 0.24
    bsdf.inputs["Specular IOR Level"].default_value = 0.72
    bsdf.inputs["Coat Weight"].default_value = 0.15
    l.new(tex.outputs["Object"], mapn.inputs["Vector"])
    l.new(mapn.outputs["Vector"], checker.inputs["Vector"])
    l.new(mapn.outputs["Vector"], noise.inputs["Vector"])
    l.new(checker.outputs["Color"], bsdf.inputs["Base Color"])
    l.new(noise.outputs["Fac"], bump.inputs["Height"])
    bump.inputs["Strength"].default_value = 0.015
    l.new(bump.outputs["Normal"], bsdf.inputs["Normal"])
    l.new(bsdf.outputs["BSDF"], out.inputs["Surface"])
    return m


def make_visor_material():
    m = new_material("MAT_Visor")
    n = m.node_tree.nodes
    l = m.node_tree.links
    out = n.new("ShaderNodeOutputMaterial")
    mix = n.new("ShaderNodeMixShader")
    transparent = n.new("ShaderNodeBsdfTransparent")
    bsdf = n.new("ShaderNodeBsdfPrincipled")
    noise = n.new("ShaderNodeTexNoise")
    ramp = n.new("ShaderNodeValToRGB")
    bsdf.inputs["Base Color"].default_value = (0.03, 0.05, 0.08, 1.0)
    bsdf.inputs["Roughness"].default_value = 0.1
    bsdf.inputs["Transmission Weight"].default_value = 0.3
    noise.inputs["Scale"].default_value = 2.5
    ramp.color_ramp.elements[0].color = (0.0, 0.0, 0.0, 1.0)
    ramp.color_ramp.elements[1].color = (1.0, 1.0, 1.0, 1.0)
    l.new(noise.outputs["Fac"], ramp.inputs["Fac"])
    l.new(ramp.outputs["Color"], mix.inputs["Fac"])
    l.new(transparent.outputs["BSDF"], mix.inputs[1])
    l.new(bsdf.outputs["BSDF"], mix.inputs[2])
    l.new(mix.outputs["Shader"], out.inputs["Surface"])
    return m


def make_vapor_material():
    m = new_material("MAT_Vapor")
    m.blend_method = "HASHED"
    n = m.node_tree.nodes
    l = m.node_tree.links
    out = n.new("ShaderNodeOutputMaterial")
    mix = n.new("ShaderNodeMixShader")
    transparent = n.new("ShaderNodeBsdfTransparent")
    bsdf = n.new("ShaderNodeBsdfPrincipled")
    noise = n.new("ShaderNodeTexNoise")
    ramp = n.new("ShaderNodeValToRGB")
    noise.inputs["Scale"].default_value = 1.8
    noise.inputs["Detail"].default_value = 9.0
    ramp.color_ramp.elements[0].color = (0.88, 0.88, 0.90, 1.0)
    ramp.color_ramp.elements[1].color = (1.0, 1.0, 1.0, 1.0)
    bsdf.inputs["Base Color"].default_value = (0.95, 0.95, 0.97, 1.0)
    bsdf.inputs["Roughness"].default_value = 0.95
    bsdf.inputs["Transmission Weight"].default_value = 0.55
    l.new(noise.outputs["Fac"], ramp.inputs["Fac"])
    l.new(ramp.outputs["Color"], mix.inputs["Fac"])
    l.new(transparent.outputs["BSDF"], mix.inputs[1])
    l.new(bsdf.outputs["BSDF"], mix.inputs[2])
    l.new(mix.outputs["Shader"], out.inputs["Surface"])
    return m


def make_earth_material():
    m = new_material("MAT_Earth")
    n = m.node_tree.nodes
    l = m.node_tree.links
    out = n.new("ShaderNodeOutputMaterial")
    bsdf = n.new("ShaderNodeBsdfPrincipled")
    tex = n.new("ShaderNodeTexCoord")
    mapn = n.new("ShaderNodeMapping")
    noise_land = n.new("ShaderNodeTexNoise")
    noise_cloud = n.new("ShaderNodeTexNoise")
    ramp_land = n.new("ShaderNodeValToRGB")
    ramp_cloud = n.new("ShaderNodeValToRGB")
    geom = n.new("ShaderNodeNewGeometry")
    dot = n.new("ShaderNodeVectorMath")
    range_node = n.new("ShaderNodeMapRange")
    mix_land = n.new("ShaderNodeMixRGB")
    mix_cloud = n.new("ShaderNodeMixRGB")
    mix_day = n.new("ShaderNodeMixRGB")
    mapn.inputs["Scale"].default_value = (1.2, 1.2, 1.2)
    noise_land.inputs["Scale"].default_value = 1.8
    noise_cloud.inputs["Scale"].default_value = 7.5
    ramp_land.color_ramp.elements[0].color = (0.03, 0.11, 0.26, 1.0)
    ramp_land.color_ramp.elements[1].color = (0.18, 0.34, 0.12, 1.0)
    ramp_cloud.color_ramp.elements[0].color = (0.92, 0.94, 0.98, 1.0)
    ramp_cloud.color_ramp.elements[1].color = (1.0, 1.0, 1.0, 1.0)
    dot.operation = "DOT_PRODUCT"
    dot.inputs[1].default_value = SUN_VECTOR
    range_node.inputs["From Min"].default_value = -0.35
    range_node.inputs["From Max"].default_value = 0.55
    range_node.inputs["To Min"].default_value = 0.0
    range_node.inputs["To Max"].default_value = 1.0
    mix_land.inputs["Color1"].default_value = (0.02, 0.09, 0.22, 1.0)
    mix_land.inputs["Color2"].default_value = (0.18, 0.34, 0.13, 1.0)
    mix_cloud.inputs["Color1"].default_value = (0.0, 0.0, 0.0, 1.0)
    mix_cloud.inputs["Color2"].default_value = (0.95, 0.96, 0.98, 1.0)
    mix_day.inputs["Color1"].default_value = (0.005, 0.012, 0.03, 1.0)
    mix_day.inputs["Color2"].default_value = (0.34, 0.52, 0.77, 1.0)
    bsdf.inputs["Roughness"].default_value = 0.68
    bsdf.inputs["Specular IOR Level"].default_value = 0.55
    l.new(tex.outputs["Generated"], mapn.inputs["Vector"])
    l.new(mapn.outputs["Vector"], noise_land.inputs["Vector"])
    l.new(mapn.outputs["Vector"], noise_cloud.inputs["Vector"])
    l.new(noise_land.outputs["Fac"], ramp_land.inputs["Fac"])
    l.new(ramp_land.outputs["Color"], mix_land.inputs["Color2"])
    l.new(noise_cloud.outputs["Fac"], ramp_cloud.inputs["Fac"])
    l.new(ramp_cloud.outputs["Color"], mix_cloud.inputs["Color2"])
    l.new(geom.outputs["Normal"], dot.inputs[0])
    l.new(dot.outputs["Value"], range_node.inputs["Value"])
    l.new(range_node.outputs["Result"], mix_day.inputs["Fac"])
    l.new(mix_land.outputs["Color"], mix_cloud.inputs["Color1"])
    l.new(mix_cloud.outputs["Color"], mix_day.inputs["Color1"])
    l.new(mix_day.outputs["Color"], bsdf.inputs["Base Color"])
    l.new(bsdf.outputs["BSDF"], out.inputs["Surface"])
    return m


def make_atmosphere_material():
    m = new_material("MAT_Earth_Atmosphere")
    m.blend_method = "BLEND"
    n = m.node_tree.nodes
    l = m.node_tree.links
    out = n.new("ShaderNodeOutputMaterial")
    transparent = n.new("ShaderNodeBsdfTransparent")
    emission = n.new("ShaderNodeEmission")
    fresnel = n.new("ShaderNodeFresnel")
    ramp = n.new("ShaderNodeValToRGB")
    mix = n.new("ShaderNodeMixShader")
    fresnel.inputs["IOR"].default_value = 1.03
    emission.inputs["Color"].default_value = (0.44, 0.70, 1.0, 1.0)
    emission.inputs["Strength"].default_value = 1.8
    ramp.color_ramp.elements[0].position = 0.72
    ramp.color_ramp.elements[0].color = (0.0, 0.0, 0.0, 1.0)
    ramp.color_ramp.elements[1].position = 0.96
    ramp.color_ramp.elements[1].color = (1.0, 1.0, 1.0, 1.0)
    l.new(fresnel.outputs["Fac"], ramp.inputs["Fac"])
    l.new(ramp.outputs["Color"], mix.inputs["Fac"])
    l.new(transparent.outputs["BSDF"], mix.inputs[1])
    l.new(emission.outputs["Emission"], mix.inputs[2])
    l.new(mix.outputs["Shader"], out.inputs["Surface"])
    return m


def build_materials():
    return {
        "regolith": make_regolith_material(),
        "white": make_white_metal_material(),
        "dark": make_dark_metal_material(),
        "panel": make_panel_material(),
        "visor": make_visor_material(),
        "vapor": make_vapor_material(),
        "earth": make_earth_material(),
        "atmosphere": make_atmosphere_material(),
        "suit_white": mat("MAT_Suit_White", (0.88, 0.88, 0.86, 1.0), rough=0.58, metal=0.05),
        "suit_dark": mat("MAT_Suit_Dark", (0.12, 0.12, 0.13, 1.0), rough=0.45, metal=0.08),
        "mid": mat("MAT_Mid_Metal", (0.55, 0.55, 0.57, 1.0), rough=0.38, metal=0.30),
    }


def height_fn(x, y):
    r = math.sqrt(x * x + y * y)
    micro = math.sin(x * 0.06 + 0.8) * 0.14 + math.cos(y * 0.05 - 0.2) * 0.12
    low = math.sin(x * 0.015 + 1.7) * 0.35 + math.cos(y * 0.013 - 0.4) * 0.32
    crater = 0.0
    for i in range(18):
        cx = math.sin(i * 2.37 + 0.9) * 42.0 + math.cos(i * 1.11) * 15.0
        cy = math.cos(i * 1.83 + 0.2) * 38.0 + math.sin(i * 0.81) * 12.0
        radius = 4.0 + (i % 5) * 2.2
        depth = 0.35 + (i % 3) * 0.18
        dx = x - cx
        dy = y - cy
        dist = math.sqrt(dx * dx + dy * dy)
        if dist < radius * 2.5:
            crater -= depth * math.exp(-(dist * dist) / max(radius * radius * 1.5, 0.001))
            crater += math.exp(-((dist - radius) ** 2) / max(radius * 0.72, 0.001)) * 0.18
    pad = smoothstep(18.0, 42.0, r)
    h = (micro * 0.55 + low * 0.7 + crater) * 0.68
    h *= 0.35 + 0.65 * pad
    h += math.sin(r * 0.03) * 0.12
    return h


def build_terrain(collection, material):
    size = 420.0
    terrain = add_prim("grid", "TERRAIN_Lunar_Surface", collection, (0, 0, -0.8), size=size, x_subdivisions=260, y_subdivisions=260)
    terrain_radius = size * 0.42
    fade_start = terrain_radius * 0.84
    skirt_depth = 4.2
    horizon_rise = 1.1
    for v in terrain.data.vertices:
        x = v.co.x
        y = v.co.y
        r = math.hypot(x, y)
        angle = math.atan2(y, x)
        irregular_radius = terrain_radius * (0.97 + 0.05 * math.sin(angle * 3.0) + 0.03 * math.cos(angle * 5.0))
        edge_mask = smoothstep(fade_start, irregular_radius, r)
        horizon_mask = smoothstep(irregular_radius * 0.78, irregular_radius * 0.98, r)
        base = height_fn(x * 0.55, y * 0.55) * 1.7
        v.co.z = base - edge_mask * skirt_depth + horizon_mask * horizon_rise
    bm = bmesh.new()
    bm.from_mesh(terrain.data)
    faces_to_delete = []
    for face in bm.faces:
        center = face.calc_center_median()
        r = math.hypot(center.x, center.y)
        angle = math.atan2(center.y, center.x)
        irregular_radius = terrain_radius * (0.99 + 0.06 * math.sin(angle * 3.0) + 0.03 * math.cos(angle * 5.0))
        if r > irregular_radius:
            faces_to_delete.append(face)
    if faces_to_delete:
        bmesh.ops.delete(bm, geom=faces_to_delete, context="FACES")
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=0.0001)
    bm.to_mesh(terrain.data)
    bm.free()
    smooth(terrain)
    terrain.data.materials.append(material)
    return terrain


def put_material(obj, material):
    if obj.data.materials:
        obj.data.materials[0] = material
    else:
        obj.data.materials.append(material)


def parent_obj(child, parent):
    location = child.location.copy()
    rotation = child.rotation_euler.copy()
    scale = child.scale.copy()
    world_matrix = (
        Matrix.Translation(location)
        @ rotation.to_matrix().to_4x4()
        @ Matrix.Diagonal((scale.x, scale.y, scale.z, 1.0))
    )
    child.parent = parent
    child.matrix_parent_inverse = parent.matrix_world.inverted()
    child.matrix_world = world_matrix


def hard_surface(obj, material, bevel_width=0.03):
    put_material(obj, material)
    smooth(obj)
    bevel(obj, bevel_width, 3)
    wnorm(obj)


def build_base_module(collection, materials, name, location, scale, roof_height=0.0):
    root = add_empty(name + "_ROOT", collection, location=location)
    body = add_prim("cube", name + "_BODY", collection, location, scale=scale)
    hard_surface(body, materials["white"], 0.06)
    parent_obj(body, root)

    trim = add_prim(
        "cube",
        name + "_TRIM",
        collection,
        (location[0], location[1], location[2] + scale[2] * 0.5 + 0.08),
        scale=(scale[0] * 0.88, scale[1] * 0.88, 0.12),
    )
    hard_surface(trim, materials["mid"], 0.03)
    parent_obj(trim, root)

    roof = add_prim(
        "cube",
        name + "_ROOF",
        collection,
        (location[0] + 0.15 * scale[0], location[1], location[2] + scale[2] * 0.5 + 0.2 + roof_height),
        scale=(scale[0] * 0.34, scale[1] * 0.22, 0.24),
    )
    hard_surface(roof, materials["dark"], 0.02)
    parent_obj(roof, root)

    vent = add_prim(
        "cylinder",
        name + "_VENT",
        collection,
        (location[0] - 0.25, location[1] - 0.08, location[2] + scale[2] * 0.5 + 0.55 + roof_height),
        rotation=(math.radians(90), 0, math.radians(15)),
        radius=0.18 * max(scale[0], scale[1]),
        depth=0.8,
        vertices=12,
    )
    hard_surface(vent, materials["dark"], 0.01)
    parent_obj(vent, root)
    return root


def build_main_base(collection, materials):
    root = add_empty("BASE_COMPLEX_ROOT", collection, location=(0, 0, 1.15))
    platform = add_prim("cube", "BASE_PLATFORM", collection, (0, 0, 0.35), scale=(22, 16, 0.24))
    hard_surface(platform, materials["mid"], 0.05)
    parent_obj(platform, root)

    modules = [
        ("BASE_CORE", (0.0, 0.0, 1.85), (5.8, 4.1, 2.8), 0.15),
        ("BASE_LAB", (8.8, 2.4, 1.75), (4.6, 3.3, 2.35), 0.08),
        ("BASE_POWER", (-7.6, 1.8, 1.65), (4.4, 3.2, 2.25), 0.05),
        ("BASE_SERVICE", (3.8, -6.8, 1.45), (3.8, 3.0, 1.95), 0.0),
        ("BASE_STORAGE", (-4.3, -6.2, 1.38), (3.5, 2.8, 1.7), 0.05),
    ]
    for name, loc, scale, roof_height in modules:
        mod = build_base_module(collection, materials, name, loc, scale, roof_height)
        parent_obj(mod, root)

    for name, loc, scale in [
        ("BASE_CORRIDOR_01", (4.1, 1.2, 1.68), (2.8, 0.55, 0.72)),
        ("BASE_CORRIDOR_02", (-3.7, 0.3, 1.55), (2.6, 0.55, 0.72)),
        ("BASE_CORRIDOR_03", (0.8, -4.8, 1.52), (1.8, 0.5, 0.72)),
    ]:
        piece = add_prim("cube", name, collection, loc, scale=scale)
        hard_surface(piece, materials["white"], 0.03)
        parent_obj(piece, root)

    details = [
        ("BASE_DETAIL_A", (1.8, 2.0, 3.9), (0.55, 0.55, 0.85), materials["dark"]),
        ("BASE_DETAIL_B", (-2.1, 1.2, 3.8), (0.40, 0.40, 0.70), materials["dark"]),
        ("BASE_DETAIL_C", (6.9, 1.6, 3.25), (0.40, 0.65, 0.60), materials["mid"]),
        ("BASE_DETAIL_D", (-5.7, -0.8, 3.0), (0.35, 0.35, 0.55), materials["dark"]),
    ]
    for name, loc, scale, material in details:
        d = add_prim("cube", name, collection, loc, scale=scale)
        hard_surface(d, material, 0.02)
        parent_obj(d, root)

    mast = add_prim("cylinder", "BASE_ANTENNA_MAST", collection, (-1.0, 5.3, 4.7), radius=0.12, depth=4.4, vertices=10)
    mast.rotation_euler = (0, math.radians(10), 0)
    hard_surface(mast, materials["dark"], 0.01)
    parent_obj(mast, root)
    dish = add_prim("uv_sphere", "BASE_ANTENNA_DISH", collection, (-0.7, 5.7, 6.7), scale=(1, 1, 0.35), segments=18, ring_count=10)
    hard_surface(dish, materials["mid"], 0.01)
    parent_obj(dish, root)
    cable = add_prim("cylinder", "BASE_CABLE_01", collection, (-0.9, 4.6, 4.2), radius=0.12, depth=2.9, vertices=12)
    cable.rotation_euler = (math.radians(90), 0, math.radians(18))
    hard_surface(cable, materials["dark"], 0.01)
    parent_obj(cable, root)
    return root


def tower_frustum(name, collection, loc, r1, r2, depth, material):
    obj = add_prim("cone", name, collection, loc, radius1=r1, radius2=r2, depth=depth, vertices=40)
    hard_surface(obj, material, 0.02)
    return obj


def build_vapor_plume(collection, materials, name, start, seed):
    rng = random.Random(seed)
    root = add_empty(name + "_ROOT", collection, location=start)
    for i in range(12):
        t = i / 11.0
        puff = add_prim(
            "ico_sphere",
            f"{name}_PUFF_{i:02d}",
            collection,
            (
                start[0] + 0.7 * t + math.sin(t * 8 + seed) * 0.18,
                start[1] + 0.05 * t + math.cos(t * 6 + seed * 0.2) * 0.12,
                start[2] + t * 15.0 + math.sin(t * 4 + seed * 0.1) * 0.22,
            ),
            scale=(0.8 + (1.0 - t) * 0.9 + rng.uniform(-0.08, 0.08),) * 3,
            subdivisions=1,
        )
        put_material(puff, materials["vapor"])
        smooth(puff)
        parent_obj(puff, root)
    return root


def build_cooling_tower(collection, materials, name, loc, scale_xy=1.0, seed=0):
    root = add_empty(name + "_ROOT", collection, location=loc)
    bottom = tower_frustum(name + "_BOTTOM", collection, (loc[0], loc[1], loc[2] + 4.0), 4.6 * scale_xy, 2.2 * scale_xy, 8.0, materials["white"])
    top = tower_frustum(name + "_TOP", collection, (loc[0], loc[1], loc[2] + 12.0), 2.2 * scale_xy, 4.8 * scale_xy, 9.0, materials["white"])
    base = add_prim("cylinder", name + "_BASE_RING", collection, (loc[0], loc[1], loc[2] + 0.12), radius=5.25 * scale_xy, depth=0.42, vertices=28)
    hard_surface(base, materials["mid"], 0.02)
    pad = add_prim("cube", name + "_UTILITY_BASE", collection, (loc[0], loc[1], loc[2] - 0.22), scale=(6.3 * scale_xy, 6.3 * scale_xy, 0.25))
    hard_surface(pad, materials["dark"], 0.04)
    plume = build_vapor_plume(collection, materials, name + "_VAPOR", (loc[0], loc[1], loc[2] + 17.6), seed)
    for obj in (bottom, top, base, pad, plume):
        parent_obj(obj, root)
    return root


def build_solar_array(collection, materials, name, origin, rows, cols, tilt_deg, yaw_deg, spacing=(2.92, 1.78)):
    root = add_empty(name + "_ROOT", collection, location=origin)
    root.rotation_euler = (math.radians(tilt_deg), 0, math.radians(yaw_deg))
    support = add_prim("cube", name + "_SUPPORT", collection, (origin[0], origin[1], origin[2] - 0.55), rotation=(math.radians(tilt_deg), 0, math.radians(yaw_deg)), scale=(cols * 1.45, 0.55, 0.18))
    hard_surface(support, materials["dark"], 0.015)
    parent_obj(support, root)
    for r in range(rows):
        for c in range(cols):
            x = origin[0] + (c - (cols - 1) * 0.5) * spacing[0]
            y = origin[1] + (r - (rows - 1) * 0.5) * spacing[1]
            panel = add_prim("cube", f"{name}_PANEL_{r:02d}_{c:02d}", collection, (x, y, origin[2] + 0.1), rotation=(math.radians(tilt_deg), 0, math.radians(yaw_deg)), scale=(1.22, 0.72, 0.08))
            hard_surface(panel, materials["panel"], 0.02)
            parent_obj(panel, root)
    for dx in (-cols * 1.0, cols * 1.0):
        leg = add_prim("cylinder", f"{name}_LEG_{dx:+.0f}", collection, (origin[0] + dx * 0.35, origin[1] - 0.4, origin[2] - 1.0), radius=0.12, depth=2.4, vertices=12)
        leg.rotation_euler = (math.radians(72), 0, math.radians(yaw_deg))
        hard_surface(leg, materials["mid"], 0.01)
        parent_obj(leg, root)
    return root


def build_astronaut(collection, materials, name, location, yaw_deg, pose="stand"):
    root = add_empty(name + "_ROOT", collection, location=location)
    root.rotation_euler = (0, 0, math.radians(yaw_deg))
    torso = add_prim("cube", name + "_TORSO", collection, (location[0], location[1], location[2] + 1.0), scale=(0.52, 0.36, 0.72))
    hard_surface(torso, materials["suit_white"], 0.05)
    parent_obj(torso, root)
    backpack = add_prim("cube", name + "_BACKPACK", collection, (location[0] - 0.32, location[1], location[2] + 1.0), scale=(0.35, 0.22, 0.5))
    hard_surface(backpack, materials["suit_dark"], 0.04)
    parent_obj(backpack, root)
    helmet = add_prim("uv_sphere", name + "_HELMET", collection, (location[0] + 0.02, location[1], location[2] + 1.55), scale=(1, 1, 1), segments=24, ring_count=12)
    hard_surface(helmet, materials["suit_white"], 0.02)
    parent_obj(helmet, root)
    visor = add_prim("uv_sphere", name + "_VISOR", collection, (location[0] + 0.11, location[1], location[2] + 1.50), scale=(1.0, 0.82, 0.72), segments=24, ring_count=12)
    put_material(visor, materials["visor"])
    smooth(visor)
    parent_obj(visor, root)

    left_upper = add_prim("cylinder", name + "_LEFT_UPPER", collection, (location[0] + 0.13, location[1] - 0.08, location[2] + 0.60), radius=0.11, depth=0.58, vertices=14)
    left_upper.rotation_euler = (math.radians(6), math.radians(4), math.radians(10))
    hard_surface(left_upper, materials["suit_white"], 0.01)
    parent_obj(left_upper, root)
    left_lower = add_prim("cylinder", name + "_LEFT_LOWER", collection, (location[0] + 0.15, location[1] - 0.14, location[2] + 0.08), radius=0.10, depth=0.62, vertices=14)
    left_lower.rotation_euler = (math.radians(10), 0, math.radians(12))
    hard_surface(left_lower, materials["suit_white"], 0.01)
    parent_obj(left_lower, root)
    right_upper = add_prim("cylinder", name + "_RIGHT_UPPER", collection, (location[0] - 0.12, location[1] + 0.05, location[2] + 0.60), radius=0.11, depth=0.58, vertices=14)
    right_upper.rotation_euler = (math.radians(-3), 0, math.radians(-8))
    hard_surface(right_upper, materials["suit_white"], 0.01)
    parent_obj(right_upper, root)
    right_lower = add_prim("cylinder", name + "_RIGHT_LOWER", collection, (location[0] - 0.16, location[1] + 0.10, location[2] + 0.08), radius=0.10, depth=0.62, vertices=14)
    right_lower.rotation_euler = (math.radians(8), 0, math.radians(-10))
    hard_surface(right_lower, materials["suit_white"], 0.01)
    parent_obj(right_lower, root)
    boot_l = add_prim("cube", name + "_BOOT_L", collection, (location[0] + 0.19, location[1] - 0.18, location[2] - 0.16), scale=(0.18, 0.12, 0.10))
    hard_surface(boot_l, materials["suit_dark"], 0.01)
    parent_obj(boot_l, root)
    boot_r = add_prim("cube", name + "_BOOT_R", collection, (location[0] - 0.14, location[1] + 0.10, location[2] - 0.16), scale=(0.18, 0.12, 0.10))
    hard_surface(boot_r, materials["suit_dark"], 0.01)
    parent_obj(boot_r, root)
    left_arm = add_prim("cylinder", name + "_ARM_L", collection, (location[0] + 0.36, location[1] - 0.08, location[2] + 1.18), radius=0.08, depth=0.72, vertices=14)
    left_arm.rotation_euler = (0, math.radians(22 if pose == "stand" else 36), math.radians(28))
    hard_surface(left_arm, materials["suit_white"], 0.01)
    parent_obj(left_arm, root)
    right_arm = add_prim("cylinder", name + "_ARM_R", collection, (location[0] - 0.34, location[1] + 0.05, location[2] + 1.18), radius=0.08, depth=0.72, vertices=14)
    right_arm.rotation_euler = (0, math.radians(-10 if pose == "stand" else 18), math.radians(-30))
    hard_surface(right_arm, materials["suit_white"], 0.01)
    parent_obj(right_arm, root)
    glove_l = add_prim("ico_sphere", name + "_GLOVE_L", collection, (location[0] + 0.65, location[1] - 0.24, location[2] + 0.95), scale=(1.0, 0.75, 0.6), subdivisions=1)
    hard_surface(glove_l, materials["suit_dark"], 0.01)
    parent_obj(glove_l, root)
    glove_r = add_prim("ico_sphere", name + "_GLOVE_R", collection, (location[0] - 0.62, location[1] + 0.22, location[2] + 0.98), scale=(1.0, 0.75, 0.6), subdivisions=1)
    hard_surface(glove_r, materials["suit_dark"], 0.01)
    parent_obj(glove_r, root)

    if pose == "walk":
        root.rotation_euler = (0, 0, math.radians(yaw_deg + 8))
        left_lower.location.z -= 0.08
        right_lower.location.z += 0.04
        left_arm.rotation_euler = (math.radians(8), math.radians(30), math.radians(54))
        right_arm.rotation_euler = (math.radians(-4), math.radians(8), math.radians(-48))
    elif pose == "crouch":
        torso.rotation_euler = (math.radians(15), 0, math.radians(4))
        helmet.location.z -= 0.16
        visor.location.z -= 0.16
        left_upper.rotation_euler = (math.radians(30), 0, math.radians(18))
        right_upper.rotation_euler = (math.radians(10), 0, math.radians(-12))
        left_arm.rotation_euler = (math.radians(28), math.radians(24), math.radians(65))
        right_arm.rotation_euler = (math.radians(18), math.radians(-5), math.radians(-38))
    return root


def build_rover(collection, materials, name, location, yaw_deg):
    root = add_empty(name + "_ROOT", collection, location=location)
    root.rotation_euler = (0, 0, math.radians(yaw_deg))
    body = add_prim("cube", name + "_BODY", collection, (location[0], location[1], location[2] + 0.65), scale=(1.3, 0.75, 0.45))
    hard_surface(body, materials["mid"], 0.05)
    parent_obj(body, root)
    top = add_prim("cube", name + "_TOP", collection, (location[0] - 0.08, location[1], location[2] + 1.02), scale=(0.8, 0.55, 0.24))
    hard_surface(top, materials["white"], 0.03)
    parent_obj(top, root)
    mast = add_prim("cylinder", name + "_MAST", collection, (location[0] + 0.48, location[1], location[2] + 1.45), radius=0.05, depth=1.2, vertices=12)
    hard_surface(mast, materials["dark"], 0.01)
    parent_obj(mast, root)
    sensor = add_prim("ico_sphere", name + "_SENSOR", collection, (location[0] + 0.50, location[1], location[2] + 2.05), scale=(1.0, 0.85, 0.85), subdivisions=1)
    put_material(sensor, materials["visor"])
    smooth(sensor)
    parent_obj(sensor, root)
    wheels = [(-0.92, -0.62), (-0.92, 0.62), (0.0, -0.72), (0.0, 0.72), (0.92, -0.62), (0.92, 0.62)]
    for i, (xo, yo) in enumerate(wheels):
        w = add_prim("cylinder", f"{name}_WHEEL_{i+1}", collection, (location[0] + xo, location[1] + yo, location[2] + 0.26), radius=0.24, depth=0.18, vertices=16)
        w.rotation_euler = (math.radians(90), 0, 0)
        hard_surface(w, materials["suit_dark"], 0.02)
        parent_obj(w, root)
    arm = add_prim("cube", name + "_UTILITY_ARM", collection, (location[0] + 0.95, location[1] - 0.18, location[2] + 0.95), rotation=(math.radians(10), math.radians(6), math.radians(-14)), scale=(0.72, 0.10, 0.10))
    hard_surface(arm, materials["dark"], 0.01)
    parent_obj(arm, root)
    return root


def build_cargo_unit(collection, materials, name, location, scale=(1.0, 1.0, 1.0), yaw_deg=0.0):
    root = add_empty(name + "_ROOT", collection, location=location)
    root.rotation_euler = (0, 0, math.radians(yaw_deg))
    crate = add_prim("cube", name + "_CRATE", collection, (location[0], location[1], location[2] + 0.52), scale=scale)
    hard_surface(crate, materials["white"], 0.04)
    parent_obj(crate, root)
    panel = add_prim("cube", name + "_ACCESS_PANEL", collection, (location[0] + 0.48 * scale[0], location[1], location[2] + 0.56), scale=(0.56, 0.12, 0.36))
    hard_surface(panel, materials["mid"], 0.02)
    parent_obj(panel, root)
    for suffix, xo in [("A", -0.4), ("B", 0.4)]:
        foot = add_prim("cylinder", f"{name}_FOOT_{suffix}", collection, (location[0] + xo * scale[0], location[1] + (-0.32 if suffix == "A" else 0.32) * scale[1], location[2] + 0.14), radius=0.08, depth=0.5, vertices=10)
        foot.rotation_euler = (math.radians(90), 0, 0)
        hard_surface(foot, materials["dark"], 0.01)
        parent_obj(foot, root)
    return root


def build_antenna(collection, materials, name, location, yaw_deg=0.0, height=3.0):
    root = add_empty(name + "_ROOT", collection, location=location)
    root.rotation_euler = (0, 0, math.radians(yaw_deg))
    mast = add_prim("cylinder", name + "_MAST", collection, (location[0], location[1], location[2] + height * 0.5), radius=0.07, depth=height, vertices=10)
    hard_surface(mast, materials["dark"], 0.01)
    parent_obj(mast, root)
    dish = add_prim("uv_sphere", name + "_DISH", collection, (location[0] + 0.2, location[1] + 0.08, location[2] + height * 0.82), scale=(1, 1, 0.28), segments=18, ring_count=10)
    hard_surface(dish, materials["mid"], 0.01)
    parent_obj(dish, root)
    return root


def build_utilities(collection, materials):
    return [
        build_rover_custom(collection, materials, "PROP_ROVER_A", (-14.0, -10.5, 0.35), 16.0),
        build_rover_custom(collection, materials, "PROP_ROVER_B", (8.4, -13.8, 0.34), -28.0),
        build_cargo_unit_custom(collection, materials, "PROP_CARGO_A", (-8.8, -3.5, 0.28), scale=(1.1, 0.9, 0.8), yaw_deg=10.0),
        build_cargo_unit_custom(collection, materials, "PROP_CARGO_B", (15.0, -2.8, 0.28), scale=(0.95, 1.0, 0.75), yaw_deg=-14.0),
        build_cargo_unit_custom(collection, materials, "PROP_CARGO_C", (-21.0, 5.2, 0.28), scale=(1.0, 1.0, 0.7), yaw_deg=35.0),
        build_antenna_custom(collection, materials, "PROP_ANTENNA_A", (19.8, -1.1, 0.35), yaw_deg=4.0, height=3.4),
        build_antenna_custom(collection, materials, "PROP_ANTENNA_B", (-19.2, -6.5, 0.35), yaw_deg=-13.0, height=2.8),
    ]


def build_earth(collection, materials):
    root = add_empty("EARTH_ROOT", collection, location=EARTH_LOCATION)
    earth = add_prim("uv_sphere", "EARTH_Main", collection, EARTH_LOCATION, scale=(18.5, 18.5, 18.5), segments=64, ring_count=32, radius=1.0)
    put_material(earth, materials["earth"])
    smooth(earth)
    parent_obj(earth, root)
    atmosphere = add_prim("uv_sphere", "EARTH_Atmosphere", collection, EARTH_LOCATION, scale=(19.8, 19.8, 19.8), segments=48, ring_count=24, radius=1.0)
    put_material(atmosphere, materials["atmosphere"])
    smooth(atmosphere)
    parent_obj(atmosphere, root)
    return root


def build_camera_and_light(root_collection):
    cam_data = bpy.data.cameras.new("CAM_Lunar_Hero")
    cam_data.lens = 26.0
    cam_data.sensor_width = 36.0
    cam_data.clip_start = 0.1
    cam_data.clip_end = 1000.0
    camera = bpy.data.objects.new("CAMERA_HERO", cam_data)
    camera.location = (-52.0, -86.0, 12.6)
    root_collection.objects.link(camera)
    target = add_empty("CAMERA_TARGET", root_collection, location=(1.5, 0.5, 4.0))
    con = camera.constraints.new("TRACK_TO")
    con.target = target
    con.track_axis = "TRACK_NEGATIVE_Z"
    con.up_axis = "UP_Y"
    cam_data.dof.use_dof = True
    cam_data.dof.focus_object = target
    cam_data.dof.aperture_fstop = 8.0
    bpy.context.scene.camera = camera
    sun_data = bpy.data.lights.new("SUN_Lunar", type="SUN")
    sun_data.energy = 4.6
    sun_data.angle = math.radians(0.18)
    sun = bpy.data.objects.new("SUN_Lunar", sun_data)
    sun.location = (-150.0, 110.0, 175.0)
    sun.rotation_euler = SUN_VECTOR.to_track_quat("-Z", "Y").to_euler()
    root_collection.objects.link(sun)
    return camera, sun


# Preserve references to the new scene builders before older scaffold
# functions with the same names are defined later in the file.
build_terrain_custom = build_terrain
build_main_base_custom = build_main_base
build_cooling_tower_custom = build_cooling_tower
build_solar_array_custom = build_solar_array
build_astronaut_custom = build_astronaut
build_rover_custom = build_rover
build_cargo_unit_custom = build_cargo_unit
build_antenna_custom = build_antenna
build_utilities_custom = build_utilities
build_earth_custom = build_earth
build_camera_and_light_custom = build_camera_and_light


def regolith_mat():
    m = bpy.data.materials.get("MAT_Regolith") or bpy.data.materials.new("MAT_Regolith")
    m.use_nodes = True
    n = m.node_tree.nodes
    l = m.node_tree.links
    n.clear()
    out = n.new("ShaderNodeOutputMaterial")
    bsdf = n.new("ShaderNodeBsdfPrincipled")
    coord = n.new("ShaderNodeTexCoord")
    mapping = n.new("ShaderNodeMapping")
    noise = n.new("ShaderNodeTexNoise")
    bump_noise = n.new("ShaderNodeTexNoise")
    ramp = n.new("ShaderNodeValToRGB")
    bump = n.new("ShaderNodeBump")
    mapping.inputs["Scale"].default_value = (0.25, 0.25, 0.25)
    noise.inputs["Scale"].default_value = 4.5
    noise.inputs["Detail"].default_value = 8.0
    bump_noise.inputs["Scale"].default_value = 12.0
    bump.inputs["Strength"].default_value = 0.35
    bsdf.inputs["Roughness"].default_value = 0.96
    bsdf.inputs["Specular IOR Level"].default_value = 0.22
    ramp.color_ramp.elements[0].position = 0.4
    ramp.color_ramp.elements[0].color = (0.24, 0.23, 0.22, 1.0)
    ramp.color_ramp.elements[1].position = 0.82
    ramp.color_ramp.elements[1].color = (0.62, 0.59, 0.55, 1.0)
    l.new(coord.outputs["Object"], mapping.inputs["Vector"])
    l.new(mapping.outputs["Vector"], noise.inputs["Vector"])
    l.new(noise.outputs["Fac"], ramp.inputs["Fac"])
    l.new(ramp.outputs["Color"], bsdf.inputs["Base Color"])
    l.new(mapping.outputs["Vector"], bump_noise.inputs["Vector"])
    l.new(bump_noise.outputs["Fac"], bump.inputs["Height"])
    l.new(bump.outputs["Normal"], bsdf.inputs["Normal"])
    l.new(bsdf.outputs["BSDF"], out.inputs["Surface"])
    return m


def vapor_mat():
    m = bpy.data.materials.get("MAT_Vapor") or bpy.data.materials.new("MAT_Vapor")
    m.use_nodes = True
    n = m.node_tree.nodes
    l = m.node_tree.links
    n.clear()
    out = n.new("ShaderNodeOutputMaterial")
    bsdf = n.new("ShaderNodeBsdfPrincipled")
    coord = n.new("ShaderNodeTexCoord")
    mapping = n.new("ShaderNodeMapping")
    noise = n.new("ShaderNodeTexNoise")
    ramp = n.new("ShaderNodeValToRGB")
    m.blend_method = "BLEND"
    mapping.inputs["Scale"].default_value = (0.5, 0.5, 1.8)
    noise.inputs["Scale"].default_value = 4.0
    bsdf.inputs["Base Color"].default_value = (0.95, 0.97, 0.99, 1.0)
    bsdf.inputs["Roughness"].default_value = 1.0
    bsdf.inputs["Transmission Weight"].default_value = 0.45
    bsdf.inputs["Alpha"].default_value = 0.12
    ramp.color_ramp.elements[0].position = 0.4
    ramp.color_ramp.elements[0].color = (1.0, 1.0, 1.0, 0.0)
    ramp.color_ramp.elements[1].position = 0.85
    ramp.color_ramp.elements[1].color = (0.92, 0.95, 0.97, 1.0)
    l.new(coord.outputs["Object"], mapping.inputs["Vector"])
    l.new(mapping.outputs["Vector"], noise.inputs["Vector"])
    l.new(noise.outputs["Fac"], ramp.inputs["Fac"])
    l.new(ramp.outputs["Color"], bsdf.inputs["Base Color"])
    l.new(ramp.outputs["Color"], bsdf.inputs["Alpha"])
    l.new(bsdf.outputs["BSDF"], out.inputs["Surface"])
    return m


def star_mat():
    m = bpy.data.materials.get("MAT_Stars") or bpy.data.materials.new("MAT_Stars")
    m.use_nodes = True
    n = m.node_tree.nodes
    l = m.node_tree.links
    n.clear()
    out = n.new("ShaderNodeOutputMaterial")
    emission = n.new("ShaderNodeEmission")
    coord = n.new("ShaderNodeTexCoord")
    mapping = n.new("ShaderNodeMapping")
    noise = n.new("ShaderNodeTexNoise")
    ramp = n.new("ShaderNodeValToRGB")
    noise.inputs["Scale"].default_value = 180.0
    ramp.color_ramp.elements[0].position = 0.965
    ramp.color_ramp.elements[0].color = (0.0, 0.0, 0.0, 1.0)
    ramp.color_ramp.elements[1].position = 0.995
    ramp.color_ramp.elements[1].color = (1.0, 1.0, 1.0, 1.0)
    emission.inputs["Color"].default_value = (0.95, 0.97, 1.0, 1.0)
    emission.inputs["Strength"].default_value = 2.0
    l.new(coord.outputs["Generated"], mapping.inputs["Vector"])
    l.new(mapping.outputs["Vector"], noise.inputs["Vector"])
    l.new(noise.outputs["Fac"], ramp.inputs["Fac"])
    l.new(ramp.outputs["Color"], emission.inputs["Color"])
    l.new(emission.outputs["Emission"], out.inputs["Surface"])
    m.blend_method = "BLEND"
    return m


def earth_mat():
    m = bpy.data.materials.get("MAT_Earth") or bpy.data.materials.new("MAT_Earth")
    m.use_nodes = True
    n = m.node_tree.nodes
    l = m.node_tree.links
    n.clear()
    out = n.new("ShaderNodeOutputMaterial")
    bsdf = n.new("ShaderNodeBsdfPrincipled")
    emission = n.new("ShaderNodeEmission")
    mix = n.new("ShaderNodeMixShader")
    coord = n.new("ShaderNodeTexCoord")
    mapping = n.new("ShaderNodeMapping")
    land_noise = n.new("ShaderNodeTexNoise")
    cloud_noise = n.new("ShaderNodeTexNoise")
    land_ramp = n.new("ShaderNodeValToRGB")
    cloud_ramp = n.new("ShaderNodeValToRGB")
    bump_noise = n.new("ShaderNodeTexNoise")
    bump = n.new("ShaderNodeBump")
    mapping.inputs["Rotation"].default_value = (0.0, 0.0, math.radians(70.0))
    land_noise.inputs["Scale"].default_value = 2.5
    land_noise.inputs["Detail"].default_value = 6.0
    cloud_noise.inputs["Scale"].default_value = 10.0
    cloud_noise.inputs["Detail"].default_value = 8.0
    bump_noise.inputs["Scale"].default_value = 8.0
    bump.inputs["Strength"].default_value = 0.22
    bsdf.inputs["Base Color"].default_value = (0.12, 0.28, 0.56, 1.0)
    bsdf.inputs["Roughness"].default_value = 0.48
    bsdf.inputs["Specular IOR Level"].default_value = 0.65
    emission.inputs["Color"].default_value = (0.45, 0.65, 1.0, 1.0)
    emission.inputs["Strength"].default_value = 0.16
    land_ramp.color_ramp.elements[0].position = 0.46
    land_ramp.color_ramp.elements[0].color = (0.08, 0.20, 0.55, 1.0)
    land_ramp.color_ramp.elements[1].position = 0.68
    land_ramp.color_ramp.elements[1].color = (0.11, 0.28, 0.10, 1.0)
    cloud_ramp.color_ramp.elements[0].position = 0.58
    cloud_ramp.color_ramp.elements[0].color = (0.85, 0.88, 0.92, 0.0)
    cloud_ramp.color_ramp.elements[1].position = 0.88
    cloud_ramp.color_ramp.elements[1].color = (1.0, 1.0, 1.0, 1.0)
    l.new(coord.outputs["Generated"], mapping.inputs["Vector"])
    l.new(mapping.outputs["Vector"], land_noise.inputs["Vector"])
    l.new(mapping.outputs["Vector"], cloud_noise.inputs["Vector"])
    l.new(mapping.outputs["Vector"], bump_noise.inputs["Vector"])
    l.new(land_noise.outputs["Fac"], land_ramp.inputs["Fac"])
    l.new(land_ramp.outputs["Color"], bsdf.inputs["Base Color"])
    l.new(bump_noise.outputs["Fac"], bump.inputs["Height"])
    l.new(bump.outputs["Normal"], bsdf.inputs["Normal"])
    l.new(cloud_noise.outputs["Fac"], cloud_ramp.inputs["Fac"])
    l.new(bsdf.outputs["BSDF"], mix.inputs[1])
    l.new(emission.outputs["Emission"], mix.inputs[2])
    mix.inputs["Fac"].default_value = 0.12
    l.new(mix.outputs["Shader"], out.inputs["Surface"])
    return m


def terrain_height(x, y):
    r = math.sqrt(x * x + y * y)
    h = (
        math.sin(x * 0.045) * math.cos(y * 0.05) * 1.5
        + math.sin(x * 0.12 + 0.8) * math.cos(y * 0.08 - 0.5) * 0.7
        + math.sin(x * 0.26 + 1.4) * math.cos(y * 0.19 + 0.7) * 0.28
        + math.sin(x * 0.54 - 0.2) * math.cos(y * 0.43 + 1.2) * 0.14
    )
    if r < 200:
        h = h * ((r / 200.0) ** 3.4 * 0.01) - 18.0
    if r > 250:
        h += (r - 250.0) * 0.006
    craters = [
        (-105, 72, 20, 2.8),
        (118, -46, 16, 2.4),
        (-65, -96, 28, 3.8),
        (88, 84, 13, 1.9),
        (-162, -35, 34, 4.2),
        (131, 40, 18, 2.7),
        (-98, 118, 14, 2.1),
        (35, -132, 24, 3.2),
    ]
    for cx, cy, radius, depth in craters:
        d = math.sqrt((x - cx) ** 2 + (y - cy) ** 2)
        if d < radius:
            t = d / radius
            h -= depth * (1.0 - t * t)
            if t > 0.82:
                h += depth * ((t - 0.82) / 0.18) * 0.6
    return h


def build_terrain(collection, material=None):
    terrain = add_prim("grid", "TERRAIN_Regolith", collection, (0, 0, 0), x_subdivisions=180, y_subdivisions=180, size=320)
    for v in terrain.data.vertices:
        v.co.z = terrain_height(v.co.x, v.co.y)
    smooth(terrain)
    assign_material(terrain, material or regolith_mat())
    wnorm(terrain)
    return terrain


def decorate_terrain(collection):
    rock_material = mat("MAT_Rock", (0.36, 0.34, 0.32, 1.0), 0.95, 0.0, 0.2)
    for idx, (x, y, z, sx, sy, sz) in enumerate([
        (-176, 110, 2.6, 4.4, 2.3, 2.6),
        (-141, -118, 1.8, 2.8, 1.7, 1.4),
        (168, 96, 2.9, 3.1, 2.1, 2.0),
        (132, -122, 2.4, 4.2, 2.5, 2.8),
        (-72, 144, 2.1, 2.9, 1.9, 1.8),
        (76, -152, 2.5, 3.6, 2.0, 2.4),
    ]):
        rock = add_prim("ico_sphere", f"TERRAIN_Rock_{idx:02d}", collection, (x, y, z), scale=(sx, sy, sz), subdivisions=1, radius=1.0)
        assign_material(rock, rock_material)
        bevel(rock, 0.04, 1)
        smooth(rock)


def platform(collection, root):
    pad = add_prim("cylinder", "BASE_Landing_Pad", collection, (0, 0, 0.65), scale=(1, 1, 0.18), vertices=64, radius=34, depth=0.7)
    pad.parent = root
    assign_material(pad, mat("MAT_Pad", (0.52, 0.52, 0.50, 1.0), 0.72, 0.08, 0.4))
    ring = add_prim("torus", "BASE_Road_Ring", collection, (0, 0, 1.05), rotation=(math.radians(90), 0, 0), major_radius=26, minor_radius=0.5, major_segments=64, minor_segments=20)
    ring.parent = root
    assign_material(ring, mat("MAT_RoadLine", (0.82, 0.66, 0.20, 1.0), 0.45, 0.02, 0.5))
    inner = add_prim("cylinder", "BASE_Center_Platform", collection, (0, 0, 1.15), scale=(1, 1, 0.12), vertices=48, radius=17, depth=0.45)
    inner.parent = root
    assign_material(inner, mat("MAT_Platform", (0.62, 0.62, 0.62, 1.0), 0.7, 0.05, 0.45))


def base_module(collection, name, location, scale, material, root, kind="cube", rotation=(0, 0, 0), bw=0.08):
    obj = add_prim(kind, name, collection, location, rotation=rotation, scale=scale)
    obj.parent = root
    assign_material(obj, material)
    bevel(obj, bw, 3)
    wnorm(obj)
    smooth(obj)
    return obj


def build_main_base(collection):
    root = add_empty("MAIN_BASE_Root", collection, (0, 0, 0.9))
    white = mat("MAT_Base_Paint", (0.82, 0.82, 0.80, 1.0), 0.56, 0.02, 0.5)
    gray = mat("MAT_Base_Gray", (0.65, 0.66, 0.67, 1.0), 0.56, 0.04, 0.5)
    dark = mat("MAT_Dark_Metal", (0.22, 0.24, 0.26, 1.0), 0.42, 0.24, 0.55)
    glass = mat("MAT_Base_Glass", (0.45, 0.70, 0.80, 1.0), 0.12, 0.0, 0.7)
    glass.blend_method = "BLEND"
    platform(collection, root)
    for name, location, scale, material, kind, bw in [
        ("BASE_Core_A", (0, 0, 6.2), (13.6, 8.8, 5.6), white, "cube", 0.11),
        ("BASE_Core_B", (-16.8, -2.0, 5.2), (8.8, 6.8, 4.8), gray, "cube", 0.11),
        ("BASE_Core_C", (16.0, 1.2, 5.0), (9.6, 7.4, 4.8), gray, "cube", 0.11),
        ("BASE_Lab_A", (-4.3, 14.5, 4.4), (10.5, 6.2, 4.2), white, "cube", 0.10),
        ("BASE_Lab_B", (10.8, 13.0, 4.2), (9.4, 5.8, 4.0), white, "cube", 0.10),
        ("BASE_Power_Block", (18.5, -10.0, 4.0), (8.0, 5.6, 4.0), gray, "cube", 0.10),
        ("BASE_Service_Block", (-19.0, 10.8, 3.8), (8.2, 5.2, 3.8), gray, "cube", 0.10),
        ("BASE_Utility_Pod", (3.2, -14.6, 2.8), (5.0, 3.8, 3.2), dark, "cube", 0.08),
        ("BASE_Connector_A", (-8.8, 5.8, 3.1), (5.8, 2.0, 2.2), dark, "cube", 0.05),
        ("BASE_Connector_B", (6.2, 6.0, 3.0), (5.6, 2.0, 2.2), dark, "cube", 0.05),
        ("BASE_Connector_C", (-2.0, -8.8, 2.8), (4.8, 2.0, 2.0), dark, "cube", 0.05),
        ("BASE_Short_Module", (26.5, 5.5, 3.2), (5.0, 4.0, 3.0), white, "cube", 0.08),
        ("BASE_Annex", (-28.0, -6.0, 3.0), (5.2, 4.0, 3.0), white, "cube", 0.08),
    ]:
        base_module(collection, name, location, scale, material, root, kind=kind, bw=bw)
    for name, location, scale, material, kind, rot, bw in [
        ("BASE_Roof_Vent_A", (-18.2, 10.5, 7.8), (1.2, 1.2, 1.4), dark, "cylinder", (0, 0, 0), 0.04),
        ("BASE_Roof_Vent_B", (12.0, 14.1, 7.5), (1.0, 1.0, 1.2), dark, "cylinder", (0, 0, 0), 0.04),
        ("BASE_Roof_Vent_C", (5.2, -14.8, 5.8), (0.9, 0.9, 1.0), dark, "cylinder", (0, 0, 0), 0.04),
        ("BASE_Antenna_Mast", (18.2, 2.4, 10.8), (0.18, 0.18, 4.2), gray, "cylinder", (0, 0, 0), 0.02),
        ("BASE_Comms_Dish", (18.8, 2.4, 14.7), (1.8, 1.8, 0.7), gray, "uv_sphere", (math.radians(90), 0, math.radians(25)), 0.03),
        ("BASE_Sensor_Dome", (-3.2, 13.6, 7.0), (1.3, 1.3, 1.0), glass, "uv_sphere", (0, 0, 0), 0.03),
    ]:
        base_module(collection, name, location, scale, material, root, kind=kind, rotation=rot, bw=bw)
    walkway = add_prim("cube", "BASE_Walkway", collection, (0, 0, 2.0), scale=(22.0, 2.0, 0.45))
    walkway.parent = root
    assign_material(walkway, dark)
    bevel(walkway, 0.03, 2)
    return root


def build_tower(collection, name, loc, root):
    shell = mat(f"MAT_{name}_Shell", (0.80, 0.80, 0.78, 1.0), 0.42, 0.04, 0.5)
    inner = mat(f"MAT_{name}_Inner", (0.08, 0.08, 0.08, 1.0), 0.82, 0.0, 0.5)
    tower = add_prim("cylinder", f"{name}_Shell", collection, (loc[0], loc[1], 19.0), vertices=40, radius=7.0, depth=30.0)
    tower.parent = root
    assign_material(tower, shell)
    bevel(tower, 0.08, 3)
    inner_t = add_prim("cylinder", f"{name}_Inner", collection, (loc[0], loc[1], 19.0), vertices=40, radius=6.2, depth=30.4)
    inner_t.parent = root
    assign_material(inner_t, inner)
    add = vapor_mat()
    for level in range(48):
        z = 35.5 + level * 0.95
        for side in (-1, 1):
            puff = add_prim(
                "ico_sphere",
                f"{name}_Vapor_{level:03d}_{side:+d}",
                collection,
                (loc[0] + side * 0.7 + (RNG.random() - 0.5) * 2.0, loc[1] + (RNG.random() - 0.5) * 2.0, z),
                scale=(0.55 + level * 0.04, 0.55 + level * 0.04, 0.65 + level * 0.05),
                subdivisions=1,
                radius=1.0,
            )
            puff.parent = root
            puff.rotation_euler = Euler((RNG.random() * math.pi, RNG.random() * math.pi, RNG.random() * math.pi))
            assign_material(puff, add)


def build_cooling_towers(collection):
    root = add_empty("COOLING_TOWERS_Root", collection, (0, 0, 0))
    build_tower(collection, "TOWER_A", (-30.0, 42.0, 0.0), root)
    build_tower(collection, "TOWER_B", (-12.0, 45.0, 0.0), root)
    return root


def solar_module(collection, name, loc, yaw, root):
    group = add_empty(name, collection, loc)
    group.parent = root
    pole = add_prim("cylinder", f"{name}_Pole", collection, (loc[0], loc[1], loc[2] + 1.85), scale=(0.22, 0.22, 1.85), vertices=10, radius=0.5, depth=3.7)
    pole.parent = group
    assign_material(pole, mat("MAT_Solar_Pole", (0.42, 0.42, 0.43, 1.0), 0.48, 0.18, 0.5))
    hinge = add_prim("uv_sphere", f"{name}_Hinge", collection, (loc[0], loc[1], loc[2] + 3.8), scale=(0.28, 0.28, 0.28), segments=16, ring_count=8, radius=0.5)
    hinge.parent = group
    assign_material(hinge, mat("MAT_Solar_Hinge", (0.35, 0.35, 0.36, 1.0), 0.35, 0.22, 0.5))
    face = add_prim("cube", f"{name}_Face", collection, (loc[0], loc[1], loc[2] + 4.8), rotation=(math.radians(-15), 0, math.radians(yaw)), scale=(4.4, 0.10, 2.6))
    face.parent = group
    assign_material(face, mat("MAT_Solar_Panel", (0.08, 0.20, 0.55, 1.0), 0.22, 0.06, 0.72))
    bevel(face, 0.03, 2)
    frame = add_prim("cube", f"{name}_Frame", collection, (loc[0], loc[1], loc[2] + 4.8), rotation=(math.radians(-15), 0, math.radians(yaw)), scale=(4.55, 0.18, 2.75))
    frame.parent = group
    assign_material(frame, mat("MAT_Solar_Frame", (0.35, 0.36, 0.37, 1.0), 0.35, 0.20, 0.5))
    bevel(frame, 0.03, 2)
    cell = add_prim("cube", f"{name}_CellGrid", collection, (loc[0], loc[1], loc[2] + 4.82), rotation=(math.radians(-15), 0, math.radians(yaw)), scale=(4.18, 0.02, 2.32))
    cell.parent = group
    assign_material(cell, mat("MAT_Solar_Cell", (0.06, 0.15, 0.32, 1.0), 0.18, 0.02, 0.75))


def build_solar_panels(collection):
    root = add_empty("SOLAR_Root", collection, (0, 0, 0))
    for idx, (x, y, z, yaw) in enumerate([
        (-46, 26, 0.2, 8),
        (-30, 30, 0.2, 6),
        (-13, 31, 0.2, 2),
        (7, 31, 0.2, -3),
        (24, 29, 0.2, -6),
        (41, 26, 0.2, -10),
        (-55, -11, 0.2, 10),
        (-36, -15, 0.2, 5),
        (18, -18, 0.2, -4),
        (40, -18, 0.2, -9),
        (58, -12, 0.2, -13),
        (64, 9, 0.2, -7),
    ]):
        solar_module(collection, f"PANEL_Array_{idx:02d}", (x, y, z), yaw, root)
    return root


def build_rover(collection, name, loc, yaw, root):
    group = add_empty(name, collection, loc, (0, 0, math.radians(yaw)))
    group.parent = root
    body = mat(f"{name}_Body", (0.66, 0.64, 0.58, 1.0), 0.46, 0.12, 0.5)
    dark = mat(f"{name}_Dark", (0.16, 0.17, 0.18, 1.0), 0.55, 0.18, 0.5)
    blue = mat(f"{name}_Blue", (0.10, 0.22, 0.52, 1.0), 0.25, 0.12, 0.7)
    body_obj = add_prim("cube", f"{name}_Body", collection, (loc[0], loc[1], loc[2] + 1.2), scale=(3.2, 1.45, 0.9))
    body_obj.parent = group
    assign_material(body_obj, body)
    bevel(body_obj, 0.1, 3)
    deck = add_prim("cube", f"{name}_Deck", collection, (loc[0], loc[1], loc[2] + 2.05), scale=(2.65, 0.9, 0.12))
    deck.parent = group
    assign_material(deck, blue)
    bevel(deck, 0.03, 2)
    mast = add_prim("cylinder", f"{name}_Mast", collection, (loc[0] - 0.9, loc[1], loc[2] + 2.8), scale=(0.08, 0.08, 1.0), vertices=8, radius=0.5, depth=2.0)
    mast.parent = group
    assign_material(mast, dark)
    for idx, (wx, wy) in enumerate([(-2.3, -1.55), (-2.3, 1.55), (0.0, -1.55), (0.0, 1.55), (2.3, -1.55), (2.3, 1.55)]):
        wheel = add_prim("cylinder", f"{name}_Wheel_{idx:02d}", collection, (loc[0] + wx, loc[1] + wy, loc[2] + 0.45), rotation=(math.radians(90), 0, 0), scale=(0.55, 0.55, 0.55), vertices=16, radius=1.0, depth=0.5)
        wheel.parent = group
        assign_material(wheel, dark)
    return group


def build_vehicle_props(collection):
    root = add_empty("VEHICLES_Root", collection, (0, 0, 0))
    build_rover(collection, "PROP_Rover_A", (-42, 14, 0.7), 14, root)
    build_rover(collection, "PROP_Rover_B", (52, -7, 0.7), -28, root)
    cargo = mat("MAT_Cargo", (0.72, 0.70, 0.66, 1.0), 0.68, 0.05, 0.5)
    for idx, (x, y, z, sx, sy, sz) in enumerate([
        (-14, -24, 0.7, 1.6, 1.0, 1.0),
        (-10, -23, 0.7, 1.2, 0.9, 1.0),
        (16, 20, 0.7, 1.5, 1.0, 1.1),
        (21, 17, 0.7, 1.0, 0.9, 0.9),
    ]):
        crate = add_prim("cube", f"PROP_Cargo_{idx:02d}", collection, (x, y, z), scale=(sx, sy, sz))
        crate.parent = root
        assign_material(crate, cargo)
        bevel(crate, 0.05, 2)
    mast = add_prim("cylinder", "PROP_Antenna_Mast", collection, (-22, 5, 4.0), scale=(0.12, 0.12, 1.9), vertices=8, radius=0.5, depth=3.8)
    mast.parent = root
    assign_material(mast, mat("MAT_Antenna", (0.48, 0.48, 0.49, 1.0), 0.46, 0.22, 0.5))
    dish = add_prim("torus", "PROP_Antenna_Dish", collection, (-21.4, 5.1, 5.1), rotation=(math.radians(80), 0, math.radians(18)), scale=(0.9, 0.9, 0.9), major_radius=1.2, minor_radius=0.13, major_segments=32, minor_segments=12)
    dish.parent = root
    assign_material(dish, mat("MAT_Antenna_Dish", (0.68, 0.68, 0.70, 1.0), 0.4, 0.24, 0.5))
    return root


def build_astronaut(collection, name, loc, yaw, root, pose):
    g = add_empty(name, collection, loc, (0, 0, math.radians(yaw)))
    g.parent = root
    suit = mat(f"{name}_Suit", (0.92, 0.90, 0.84, 1.0), 0.58, 0.08, 0.5)
    trim = mat(f"{name}_Trim", (0.78, 0.62, 0.15, 1.0), 0.46, 0.12, 0.5)
    pack = mat(f"{name}_Pack", (0.55, 0.55, 0.56, 1.0), 0.44, 0.18, 0.5)
    visor = mat(f"{name}_Visor", (0.05, 0.06, 0.07, 1.0), 0.06, 0.12, 0.95)
    torso = add_prim("cylinder", f"{name}_Torso", collection, (loc[0], loc[1], loc[2] + 1.55), scale=(0.52, 0.52, 0.72), vertices=14, radius=0.5, depth=1.5)
    torso.parent = g
    assign_material(torso, suit)
    helmet = add_prim("uv_sphere", f"{name}_Helmet", collection, (loc[0], loc[1], loc[2] + 2.58), scale=(0.58, 0.58, 0.58), segments=24, ring_count=16, radius=0.5)
    helmet.parent = g
    assign_material(helmet, suit)
    visor_obj = add_prim("uv_sphere", f"{name}_Visor", collection, (loc[0], loc[1] + 0.18, loc[2] + 2.54), scale=(0.35, 0.47, 0.28), segments=18, ring_count=10, radius=0.5)
    visor_obj.parent = g
    assign_material(visor_obj, visor)
    backpack = add_prim("cube", f"{name}_Backpack", collection, (loc[0] - 0.68, loc[1], loc[2] + 1.55), scale=(0.28, 0.46, 0.62))
    backpack.parent = g
    assign_material(backpack, pack)
    for idx, side in enumerate([-1, 1]):
        upper = add_prim("cylinder", f"{name}_Upper_{idx}", collection, (loc[0] + side * 0.18, loc[1], loc[2] + 0.72), rotation=(math.radians(6), 0, 0), scale=(0.14, 0.14, 0.66), vertices=10, radius=0.5, depth=1.3)
        upper.parent = g
        assign_material(upper, suit)
        boot = add_prim("cube", f"{name}_Boot_{idx}", collection, (loc[0] + side * 0.28, loc[1] + 0.1, loc[2] - 0.03), scale=(0.18, 0.28, 0.12))
        boot.parent = g
        assign_material(boot, trim)
    if pose == "kneel":
        g.rotation_euler = Euler((math.radians(5), 0, math.radians(18)))
    elif pose == "walk":
        g.rotation_euler = Euler((0, 0, math.radians(-12)))
    return g


def build_astronauts(collection):
    root = add_empty("ASTRONAUTS_Root", collection, (0, 0, 0))
    build_astronaut(collection, "ASTRO_A", (-39, 18, 0.8), 16, root, "walk")
    build_astronaut(collection, "ASTRO_B", (38, 10, 0.8), -18, root, "stand")
    build_astronaut(collection, "ASTRO_C", (8, -18, 0.8), 132, root, "kneel")
    return root


def build_earth(collection):
    root = add_empty("EARTH_Root", collection, EARTH_LOCATION)
    earth = add_prim("uv_sphere", "EARTH_Main", collection, EARTH_LOCATION, scale=(31.0, 31.0, 31.0), segments=64, ring_count=32, radius=1.0)
    earth.parent = root
    assign_material(earth, earth_mat())
    smooth(earth)
    halo = add_prim("uv_sphere", "EARTH_Halo", collection, EARTH_LOCATION, scale=(33.0, 33.0, 33.0), segments=48, ring_count=24, radius=1.0)
    halo.parent = root
    halo_mat = mat("MAT_Earth_Halo", (0.40, 0.60, 1.0, 1.0), 0.0, 0.0, 0.0)
    halo_mat.blend_method = "BLEND"
    halo_bsdf = halo_mat.node_tree.nodes["Principled BSDF"]
    halo_bsdf.inputs["Transmission Weight"].default_value = 0.75
    halo_bsdf.inputs["Alpha"].default_value = 0.05
    halo_bsdf.inputs["Emission Strength"].default_value = 0.5
    assign_material(halo, halo_mat)
    smooth(halo)
    return root


def build_starfield(collection):
    sky = add_prim("uv_sphere", "STAR_SkyDome", collection, (0, 0, 0), scale=(900, 900, 900), segments=64, ring_count=32, radius=1.0)
    sky.scale.x = -900
    assign_material(sky, star_mat())
    smooth(sky)
    return sky


def build_camera(scene):
    cam_data = bpy.data.cameras.new("CAM_Hero")
    cam = bpy.data.objects.new("CAM_Hero", cam_data)
    scene.collection.objects.link(cam)
    cam.location = (150.0, -182.0, 86.0)
    cam_data.lens = 24.0
    cam_data.sensor_width = 36.0
    target = bpy.data.objects.new("CAM_Target", None)
    target.location = (0.0, 0.0, 3.0)
    scene.collection.objects.link(target)
    c = cam.constraints.new("TRACK_TO")
    c.target = target
    c.track_axis = "TRACK_NEGATIVE_Z"
    c.up_axis = "UP_Y"
    return cam


def build_sun(scene):
    sun_data = bpy.data.lights.new("SUN_Main", type="SUN")
    sun_data.energy = 220.0
    sun = bpy.data.objects.new("SUN_Main", sun_data)
    scene.collection.objects.link(sun)
    sun.rotation_euler = SUN_VECTOR.to_track_quat("-Z", "Y").to_euler()
    return sun


def build_scene():
    return build_scene_custom()


def build_scene_custom():
    clear_scene()
    scene = bpy.context.scene
    root = bpy.data.collections.get(ROOT_COLLECTION) or bpy.data.collections.new(ROOT_COLLECTION)
    if root.name not in scene.collection.children:
        scene.collection.children.link(root)
    collections = {"root": root}
    for name in COLLECTIONS:
        collections[name] = bpy.data.collections.get(name) or bpy.data.collections.new(name)
        if collections[name].name not in root.children:
            root.children.link(collections[name])

    materials = build_materials()
    build_terrain_custom(collections["Terrain"], materials["regolith"])
    build_main_base_custom(collections["Main_Base_Buildings"], materials)
    build_cooling_tower_custom(collections["Cooling_Towers"], materials, "TOWER_A", (-23.0, 18.5, 1.15), scale_xy=1.0, seed=SEED + 11)
    build_cooling_tower_custom(collections["Cooling_Towers"], materials, "TOWER_B", (-14.8, 17.0, 1.15), scale_xy=0.95, seed=SEED + 23)

    build_solar_array_custom(collections["Solar_Panels"], materials, "SOLAR_FOREGROUND_LEFT", (-43.5, -18.0, 0.55), rows=2, cols=4, tilt_deg=20.0, yaw_deg=6.0)
    build_solar_array_custom(collections["Solar_Panels"], materials, "SOLAR_FOREGROUND_RIGHT", (35.0, -14.8, 0.52), rows=2, cols=4, tilt_deg=18.0, yaw_deg=-10.0)
    build_solar_array_custom(collections["Solar_Panels"], materials, "SOLAR_MID_LEFT", (-18.0, -28.0, 0.50), rows=2, cols=3, tilt_deg=16.0, yaw_deg=15.0)
    build_solar_array_custom(collections["Solar_Panels"], materials, "SOLAR_MID_RIGHT", (20.5, -28.8, 0.50), rows=2, cols=3, tilt_deg=15.0, yaw_deg=-18.0)

    build_astronaut_custom(collections["Astronauts"], materials, "ASTRO_01", (-15.5, -5.8, 0.35), 48.0, pose="walk")
    build_astronaut_custom(collections["Astronauts"], materials, "ASTRO_02", (11.0, -6.2, 0.34), -42.0, pose="stand")
    build_astronaut_custom(collections["Astronauts"], materials, "ASTRO_03", (23.8, 3.5, 0.34), 172.0, pose="crouch")

    build_utilities_custom(collections["Vehicles_and_Props"], materials)
    build_earth_custom(collections["Earth_Background"], materials)
    build_camera_and_light_custom(root)
    build_antenna_custom(collections["Vehicles_and_Props"], materials, "BASE_BEACON", (2.5, 7.4, 3.0), yaw_deg=32.0, height=2.2)
    build_cargo_unit_custom(collections["Vehicles_and_Props"], materials, "BASE_SERVICE_CRATE", (-2.0, 6.8, 0.25), scale=(0.75, 0.75, 0.6), yaw_deg=8.0)
    return scene


def save_scene(path: Path):
    path.parent.mkdir(parents=True, exist_ok=True)
    bpy.ops.wm.save_as_mainfile(filepath=str(path))


def export_glb(path: Path):
    path.parent.mkdir(parents=True, exist_ok=True)
    hidden_objects = []
    for obj in bpy.data.objects:
        if obj.name.startswith("EARTH_") or "_VAPOR_" in obj.name:
            hidden_objects.append((obj, obj.hide_get()))
            obj.hide_set(True)

    terrain = bpy.data.objects.get("TERRAIN_Lunar_Surface")
    original_material = None
    terrain_modifier = None
    if terrain and terrain.type == "MESH":
        if terrain.data.materials:
            original_material = terrain.data.materials[0]
            terrain.data.materials[0] = regolith_mat()
        terrain_modifier = terrain.modifiers.new("WEB_Decimate", "DECIMATE")
        terrain_modifier.ratio = 0.08
        terrain_modifier.use_collapse_triangulate = True

    bpy.ops.export_scene.gltf(
        filepath=str(path),
        export_format="GLB",
        use_visible=True,
        export_apply=True,
        export_texcoords=True,
        export_normals=True,
        export_yup=True,
        export_cameras=False,
    )
    if terrain and terrain_modifier:
        terrain.modifiers.remove(terrain_modifier)
        if original_material is not None:
            terrain.data.materials[0] = original_material
    for obj, was_hidden in hidden_objects:
        obj.hide_set(was_hidden)


def render_preview(scene, path: Path):
    scene.render.filepath = str(path)
    scene.render.resolution_x = 1600
    scene.render.resolution_y = 670
    scene.cycles.samples = 48
    scene.cycles.preview_samples = 12
    bpy.ops.render.render(write_still=True)


def final_main():
    args = parse_args()
    scene = build_scene()
    blend_path = Path(args.output_dir) / args.blend_name
    if args.preview:
        render_preview(scene, Path(args.output_dir) / args.preview_name)
    save_scene(blend_path)
    if args.export_glb:
        export_glb(Path(args.output_dir) / args.glb_name)
    print(f"Saved scene to {blend_path}")


if __name__ == "__main__":
    final_main()
