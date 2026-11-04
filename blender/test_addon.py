"""blender -b --python test_addon.py -- addon.py head.glb out.png : registers the addon, imports the head, renders a front view."""
import sys, os, importlib.util, math
import bpy
from mathutils import Vector
addon, glb, out = sys.argv[sys.argv.index('--') + 1:][:3]
spec = importlib.util.spec_from_file_location("head_wrap_ai", addon)
m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m); m.register()
sc = bpy.context.scene
sc.hw.glb = glb
sc.hw.script = os.path.join(os.path.dirname(addon), "nonexistent.py")
try:
    bpy.ops.headwrap.run()
except RuntimeError as e:
    print("RUN: clear error OK:", str(e).strip()[:80])  # a missing script is reported, not a crash
print("IMPORT:", bpy.ops.headwrap.import_glb())
col = bpy.data.collections["HeadWrap"]
objs = [o for o in col.objects if o.type == 'MESH']
print("MESHES:", [(o.name, len(o.data.polygons), [s.material.name if s.material else None for s in o.material_slots]) for o in objs])
mn = Vector((1e9,) * 3); mx = Vector((-1e9,) * 3)
for o in objs:
    for v in o.bound_box:
        w = o.matrix_world @ Vector(v); mn = Vector(map(min, mn, w)); mx = Vector(map(max, mx, w))
c = (mn + mx) / 2; size = (mx - mn).length
cam = bpy.data.objects.new("cam", bpy.data.cameras.new("cam")); sc.collection.objects.link(cam)
cam.location = c + Vector((0, -size * 1.3, 0)); cam.rotation_euler = (math.pi / 2, 0, 0); sc.camera = cam
sc.render.engine = 'BLENDER_WORKBENCH'; sc.display.shading.light = 'FLAT'; sc.display.shading.color_type = 'TEXTURE'
sc.render.resolution_x = sc.render.resolution_y = 800; sc.render.filepath = out
bpy.ops.render.render(write_still=True)
print("DONE", out)
