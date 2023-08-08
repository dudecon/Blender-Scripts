# Numeric Control importer for Blender
# Released to the Public Domain by Paul Spooner
# Designed for importing my laser engraver files for editing

import bpy
from bpy import context as C
from pathlib import Path
from mathutils import Vector

FILEIN = '//Eagle Swoop Optimum.nc'

VERBOSE = True
VARIABLEPOWER = False


NCdata = ""
fp = Path(bpy.path.abspath(FILEIN))
try:
    f = open(fp, 'r')
    NCdata = f.read()
    f.close()
    if VERBOSE: print('File Loaded')
except:
    if VERBOSE: print('exception found while loading file')

if VERBOSE: print("data is", len(NCdata), "characters long")

def multisplit(text, tokens):
    results = []
    while len(text):
        nxtT = len(text)
        for t in tokens:
            found = text.find(t, 1)
            if found >= 0: nxtT = min(nxtT, found)
        results.append(text[:nxtT].strip())
        if nxtT < len(text): text = text[nxtT:]
        else: text = ""
    return results

def get_tokens(line):
    NCTokens = ("X", "Y", "F", "S", "M", "G")
    token_results = {}
    splits = multisplit(line.strip(), NCTokens)
    for seg in splits:
        if seg[0] in NCTokens:
            try:
                token_results[seg[0]] = float(seg[1:].strip())
            except:
                pass
    return token_results

def areSamePosition(p1, p2):
    if p1["X"] != p2["X"]: return False
    if p1["Y"] != p2["Y"]: return False
    return True

numPoints = 0
splines = []
spline  = []
X = 0.
Y = 0.
S = 0

NC_lines = NCdata.splitlines()

for NCLine in NC_lines:
    line_tokens = get_tokens(NCLine)
    if "X" in line_tokens: X = line_tokens["X"]
    if "Y" in line_tokens: Y = line_tokens["Y"]
    if "S" in line_tokens: S = line_tokens["S"]
    if ("X" in line_tokens) or ("Y" in line_tokens):
        p = {"X": X, "Y": Y}
    else:
        # no new position info, so continue processing
        continue
    if "S" in line_tokens:
        S = int(line_tokens["S"])
        if (S != 0) and VARIABLEPOWER: p["S"] = S
    if S == 0:
        if len(spline) > 1:
            # we need at least two points for a valid spline
            splines.append(spline)
            numPoints += 1
        else:
            # no new point data, so don't increment point data
            pass
        # either way, start a new spline
        spline = [p]
    else:
        # just add the point data to the existing spline
        spline.append(p)
        numPoints += 1

if VERBOSE: print('collected',numPoints,'points in',len(splines),'splines.')

verts = []
edges = []
faces = []

for grp in splines:
    for i, curpoint in enumerate(grp):
        curpos = curpoint
        X = curpos['X']
        Y = curpos['Y']
        verts.append(Vector((X, Y, 0)))
        if i > 0:
            lastvert = len(verts)
            edges.append((lastvert-1, lastvert-2))

if VERBOSE: print('number of verticies to generate', len(verts))

name = FILEIN.split('.')[0].strip('/')
mesh = bpy.data.meshes.new(name=name)
mesh.from_pydata(verts, edges, faces)
obj = bpy.data.objects.new(name, mesh)

layer = C.view_layer
layer_collection = C.layer_collection or layer.active_layer_collection
scene_collection = layer_collection.collection
scene_collection.objects.link(obj)
obj.select_set(True)
layer.objects.active = obj

