bl_info = {
    "name": "Head Wrap AI",
    "author": "POMXARK",
    "version": (0, 1, 0),
    "blender": (3, 3, 0),
    "location": "View3D > Sidebar > Head Wrap",
    "description": "Thin front-end of head-wrap-ai: runs headwrap.py and shows the head glb in the viewport",
    "category": "Import-Export",
}
# No pipeline logic here (it lives in headwrap.py): the panel only runs the command line and imports the result.
import os
import subprocess
import bpy
from bpy.props import StringProperty, EnumProperty


class HW_Props(bpy.types.PropertyGroup):
    python: StringProperty(name="Python", default="python3", description="Interpreter with the pipeline packages")
    script: StringProperty(name="headwrap.py", subtype='FILE_PATH', default="//headwrap.py")
    glb: StringProperty(name="Head glb", subtype='FILE_PATH', default="//work/hero1_eye.glb")
    cmd: EnumProperty(name="Step", items=[('status', 'status', ''), ('texture', 'texture', ''), ('build', 'build', ''),
                                          ('game', 'game', ''), ('all', 'all', '')], default='status')


class HW_OT_run(bpy.types.Operator):
    bl_idname = "headwrap.run"
    bl_label = "Run headwrap.py"
    bl_description = "Run the selected step of headwrap.py and show its last lines"

    def execute(self, ctx):
        p = ctx.scene.hw
        script = bpy.path.abspath(p.script)
        if not os.path.exists(script):
            self.report({'ERROR'}, "headwrap.py not found: " + script)
            return {'CANCELLED'}
        r = subprocess.run([p.python, script, p.cmd], cwd=os.path.dirname(script), capture_output=True, text=True)
        out = (r.stdout + r.stderr).strip().splitlines()
        print("\n".join(out))
        self.report({'INFO' if r.returncode == 0 else 'ERROR'}, " | ".join(out[-3:]) or "no output")
        return {'FINISHED'} if r.returncode == 0 else {'CANCELLED'}


class HW_OT_import(bpy.types.Operator):
    bl_idname = "headwrap.import_glb"
    bl_label = "Import head"
    bl_description = "Import the head glb (replaces the previous Head Wrap collection)"

    def execute(self, ctx):
        path = bpy.path.abspath(ctx.scene.hw.glb)
        if not os.path.exists(path):
            self.report({'ERROR'}, "glb not found: " + path)
            return {'CANCELLED'}
        old = bpy.data.collections.get("HeadWrap")
        if old:
            for o in list(old.objects):
                bpy.data.objects.remove(o, do_unlink=True)
            bpy.data.collections.remove(old)
        before = set(bpy.data.objects)
        bpy.ops.import_scene.gltf(filepath=path)
        col = bpy.data.collections.new("HeadWrap")
        ctx.scene.collection.children.link(col)
        for o in set(bpy.data.objects) - before:
            for c in list(o.users_collection):
                c.objects.unlink(o)
            col.objects.link(o)
        self.report({'INFO'}, "%d objects imported" % len(col.objects))
        return {'FINISHED'}


class HW_PT_panel(bpy.types.Panel):
    bl_label = "Head Wrap"
    bl_idname = "HW_PT_panel"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "Head Wrap"

    def draw(self, ctx):
        p, l = ctx.scene.hw, self.layout
        for k in ("python", "script", "cmd"):
            l.prop(p, k)
        l.operator("headwrap.run", icon='PLAY')
        l.separator()
        l.prop(p, "glb")
        l.operator("headwrap.import_glb", icon='IMPORT')


CLASSES = (HW_Props, HW_OT_run, HW_OT_import, HW_PT_panel)


def register():
    for c in CLASSES:
        bpy.utils.register_class(c)
    bpy.types.Scene.hw = bpy.props.PointerProperty(type=HW_Props)


def unregister():
    del bpy.types.Scene.hw
    for c in reversed(CLASSES):
        bpy.utils.unregister_class(c)


if __name__ == "__main__":
    register()
