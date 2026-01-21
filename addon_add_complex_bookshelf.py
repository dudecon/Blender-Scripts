bl_info = {
    "name": "Complex Bookshelf",
    "author": "Paul Spooner",
    "version": (0, 1),
    "blender": (2, 80, 0),
    "location": "View3D > Add > Mesh > Complex Bookshelf",
    "description": "Adds a complicated Bookshelf",
    "warning": "",
    "doc_url": "",
    "category": "Add Mesh",
}


import bpy
from bpy.types import Operator
from bpy.props import (
    BoolProperty,
    EnumProperty,
    FloatProperty,
    IntProperty,
)
from bpy_extras.object_utils import AddObjectHelper, object_data_add
from mathutils import Vector
import random
from random import random as rand

# this bookshelf populates via recursion
# each zone is the max x and z, followed by the min x and z.
# these values are strict bounds, IE they must account for thickness before passing
# to the next layer.

subdivtypes = []
attempt_horizontal_on_failure = False

def horiz(mn, thk, verts, zone):
    znright = zone[0]
    zntop = zone[1]
    znleft = zone[2]
    znbtm = zone[3]
    zwd = znright - znleft
    if zwd < mn: return 0
    zht = zntop - znbtm
    if zht < mn * 2.618 + thk: return 0
    pairs = 0
    # test for space for two shelves
    if zht > mn * 3.618 + thk * 2:
        pairs = 2
        tol = min((zht - (mn + thk*2))/2 - mn, mn*2.618)
        ht = mn + rand()*tol + thk/2
        zval = zntop - ht
        verts += [Vector((znleft, 0, zval)),
        Vector(( znright, 0, zval)),]
        zval = znbtm + ht
        verts += [Vector((znleft, 0, zval)),
        Vector(( znright, 0, zval)),]
        subzone = (znright, zntop-ht-thk/2, znleft, znbtm+ht+thk/2)
        subtype = random.choice(subdivtypes)
        newpairs = subtype(mn, thk, verts, subzone)
        if newpairs: pairs += newpairs
        elif attempt_horizontal_on_failure: pairs += horiz(mn, thk, verts, subzone)
    else: # just one shelf in the middle
        pairs = 1
        tol = (zht - (mn*2 + thk))
        ht = mn + rand()*tol + thk/2
        zval = znbtm + ht
        verts += [Vector((znleft, 0, zval)),
        Vector(( znright, 0, zval)),]
    
    return pairs

def pin(mn, thk, verts, zone):
    znright = zone[0]
    zntop = zone[1]
    znleft = zone[2]
    znbtm = zone[3]
    zwd = znright - znleft
    if zwd < mn * 3.618 + thk * 2: return 0
    zht = zntop - znbtm
    if zht < mn * 3.618 + thk * 2: return 0
    xcent = znleft + zwd/2
    zcent = znbtm + zht/2
    pairs = 4
    tol = min(zwd,zht) - thk * 2 - mn*3
    coff = (mn + rand()*tol + thk)/2
    tblkp = ((1,0),(0,1))
    lh, rh = random.choice(tblkp)
    #top leg
    verts += [Vector((znleft*lh + (xcent-coff+thk/2)*rh, 0, zcent + coff)),
    Vector((znright*rh + (xcent+coff-thk/2)*lh, 0, zcent + coff)),]
    #btm leg
    verts += [Vector((znleft*rh + (xcent-coff+thk/2)*lh, 0, zcent - coff)),
    Vector((znright*lh + (xcent+coff-thk/2)*rh, 0, zcent - coff)),]
    #left leg
    verts += [Vector((xcent - coff , 0, znbtm*lh + (zcent-coff+thk/2)*rh)),
    Vector((xcent - coff, 0, zntop*rh + (zcent+coff-thk/2)*lh)),]
    #right leg
    verts += [Vector((xcent + coff , 0, zntop*lh + (zcent+coff-thk/2)*rh)),
    Vector((xcent + coff, 0, znbtm*rh + (zcent-coff+thk/2)*lh)),]
    subzones = []
    #center subdiv
    subzones.append((xcent+coff-thk/2, zcent+coff-thk/2, xcent-coff+thk/2, zcent-coff+thk/2))
    #left subdiv
    subzones.append((xcent-coff-thk/2, zntop*rh + (zcent+coff-thk/2)*lh,
    znleft, znbtm*lh + (zcent-coff+thk/2)*rh))
    #right subdiv
    subzones.append((znright, zntop*lh + (zcent+coff-thk/2)*rh,
    xcent+coff+thk/2, znbtm*rh + (zcent-coff+thk/2)*lh))
    #top subdiv
    subzones.append(( znright*rh + (xcent+coff-thk/2)*lh, zntop,
    znleft*lh + (xcent-coff+thk/2)*rh , zcent+coff+thk/2))
    #bottom subdiv
    subzones.append(( znright*lh + (xcent+coff-thk/2)*rh, zcent-coff-thk/2,
    znleft*rh + (xcent-coff+thk/2)*lh ,znbtm ))
    for subzone in subzones:
        subtype = random.choice(subdivtypes)
        newpairs = subtype(mn, thk, verts, subzone)
        if newpairs: pairs += newpairs
        elif attempt_horizontal_on_failure: pairs += horiz(mn, thk, verts, subzone)
    return pairs

def add_object(self, context):
    global subdivtypes, attempt_horizontal_on_failure
    minspacing = self.min_shelf_height
    width = self.width
    heiht = self.height
    depth = self.depth
    thick = self.shelf_thickness
    random.seed(self.randseed)
    
    subdivtypes = []
    if self.horizontal_shelves: subdivtypes.append(horiz)
    if self.pinwheel_shelves: subdivtypes.append(pin)
    attempt_horizontal_on_failure = self.force_horizontal
    if len(subdivtypes) == 0:
        self.horizontal_shelves = True
        subdivtypes.append(horiz)
    
    verts = []
    edges = [(0,1),(2,3)] #sides
    faces = []
    #uprights at the end
    verts += [Vector((-0.5 * width + thick/2, 0, 0)),
        Vector((-0.5 * width + thick/2, 0, heiht)),
        Vector(( 0.5 * width - thick/2, 0, 0)),
        Vector(( 0.5 * width - thick/2, 0, heiht)),]
    # note the time before starting the recursive 
    pairs = horiz(minspacing, thick, verts, (0.5 * width-thick, heiht, -0.5 * width+thick, minspacing/2))
    for i in range(2,2+pairs):
        edges += [(i*2, i*2+1)]

    mesh = bpy.data.meshes.new(name="Complex Bookshelf Mesh")
    mesh.from_pydata(verts, edges, faces)
    # useful for development when the mesh may be invalid.
    # mesh.validate(verbose=True)
    ob = object_data_add(context, mesh, operator=self)
    bpy.ops.object.modifier_add(type='SCREW')
    bpy.context.object.modifiers[0].screw_offset = depth
    bpy.context.object.modifiers[0].axis = 'Y'
    bpy.context.object.modifiers[0].angle = 0
    bpy.context.object.modifiers[0].steps = 1
    bpy.context.object.modifiers[0].render_steps = 1
    if pairs < 1000:
        bpy.ops.object.modifier_add(type='SOLIDIFY')
        bpy.context.object.modifiers[1].thickness = thick
        bpy.context.object.modifiers[1].offset = 0
        if pairs < 250:
            bpy.ops.object.modifier_add(type='BEVEL')
            bpy.context.object.modifiers[2].width = thick/4
            bpy.ops.object.shade_flat()
            #bpy.context.object.data.use_auto_smooth = True


class OBJECT_OT_add_object(Operator, AddObjectHelper):
    """Create a complex Bookshelf"""
    bl_idname = "mesh.add_recurse_bookshelf"
    bl_label = "Add Complex Bookshelf"
    bl_options = {'REGISTER', 'UNDO'}
    
    
    width: FloatProperty(
        name="Bookshelf Width",
        description="The Bookshelf Width",
        soft_min=0.0, soft_max=20.0,
        min=0.0, max=10_000.0,
        default=4.0,
        subtype='DISTANCE',
        unit='LENGTH',
    )
    
    height: FloatProperty(
        name="Bookshelf Height",
        description="The total Bookshelf height",
        soft_min=0.0, soft_max=50.0,
        min=0.0, max=10_000.0,
        default=6.0,
        subtype='DISTANCE',
        unit='LENGTH',
    )
    
    depth: FloatProperty(
        name="Bookshelf Depth",
        description="The total Bookshelf depth",
        soft_min=0.0, soft_max=10.0,
        min=0.0, max=10_000.0,
        default=2.0,
        subtype='DISTANCE',
        unit='LENGTH',
    )
    
    shelf_thickness: FloatProperty(
        name="Shelf Thickness",
        description="The thickness of each shelf",
        soft_min=0.0, soft_max=0.3,
        min=0.0, max=1_000.0,
        default=0.10,
        subtype='DISTANCE',
        unit='LENGTH',
    )
    
    min_shelf_height: FloatProperty(
        name="Shelf Min Height",
        description="The minimum spacing of each shelf",
        soft_min=0.0, soft_max=1.0,
        min=0.0, max=1_000.0,
        default=0.40,
        subtype='DISTANCE',
        unit='LENGTH',
    )
    
    randseed: IntProperty(
        name="Randomization Seed",
        description="The seed for the random number generator",
        min=1, max=2147483647,
        default=1,
    )
    
    horizontal_shelves: BoolProperty(
        name="Horizontal",
        description="Enable horizontal shelves",
        default=True,
    )
    
    force_horizontal: BoolProperty(
        name="horiz force",
        description="always try to fill with horizontal shelves",
        default=True,
    )
    
    pinwheel_shelves: BoolProperty(
        name="Pinwheel",
        description="Enable pinwheel shelves",
        default=True,
    )
    
    def draw(self, _context):
        layout = self.layout
        
        col = layout.column(align=True)
        col.label(text="Dimensions")
        col.prop(self, "height", text="height")
        col.prop(self, "width", text="width")
        col.prop(self, "depth", text="depth")
        
        col = layout.column(align=True)
        col.label(text="Spacing and thickness of Shelves")
        col.prop(self, "min_shelf_height", text="spacing")
        col.prop(self, "shelf_thickness", text="thickness")
        
        col = layout.column(align=True)
        col.prop(self, "randseed", text="seed")
        col.prop(self, "force_horizontal", text="horiz fallback")
        col.prop(self, "horizontal_shelves", text="horiz recur")
        col.prop(self, "pinwheel_shelves", text="pinwheel recur")

    def execute(self, context):

        add_object(self, context)

        return {'FINISHED'}


# Registration

def add_object_button(self, context):
    self.layout.operator(
        OBJECT_OT_add_object.bl_idname,
        text="Add Complex Bookshelf",
        icon='PLUGIN')


# This allows you to right click on a button and link to documentation
def add_object_manual_map():
    url_manual_prefix = "https://docs.blender.org/manual/en/latest/"
    url_manual_mapping = (
        ("bpy.ops.mesh.add_object", "scene_layout/object/types.html"),
    )
    return url_manual_prefix, url_manual_mapping


def register():
    bpy.utils.register_class(OBJECT_OT_add_object)
    bpy.utils.register_manual_map(add_object_manual_map)
    bpy.types.VIEW3D_MT_mesh_add.append(add_object_button)


def unregister():
    bpy.utils.unregister_class(OBJECT_OT_add_object)
    bpy.utils.unregister_manual_map(add_object_manual_map)
    bpy.types.VIEW3D_MT_mesh_add.remove(add_object_button)


if __name__ == "__main__":
    register()
