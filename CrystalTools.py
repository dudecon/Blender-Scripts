#-------
# File CrystalTools.py
# Makes "crystal" solids
#-------

from math import sqrt, sin, cos, tan, pi
from random import random

#################################################
#Blender interface for scripts, and blender specific imports
#################################################

import bpy
import bmesh
import mathutils
from mathutils import Vector

Rotation = mathutils.Matrix.Rotation

# this is the minimum distance things need to be from eachother
MINDISTANCE = 0.0001
# It would be nice to not need this. Maybe scale the figure to compensate?

#
def makeblendermesh(name, PointList, EdgeList = None, FaceList = None):
    mesh_data = bpy.data.meshes.new(name)
    '''Generates a blender mesh datablock from a list of points.
    '''
    verts = PointList
    
    if (not ( EdgeList or FaceList )): return None
    if EdgeList: edges = EdgeList
    else: edges = []
    if FaceList: faces = FaceList
    else: faces = []
    mesh_data.from_pydata(verts, edges, faces)
    mesh_data.update(calc_edges=True)
    return mesh_data
#
def makeblendercachedob(name,mesh_data):
    '''Generates an object from a mesh datablock.
    Inserts the object in the current scene.
    '''
    mesh_object = bpy.data.objects.new(name, mesh_data)
    bpy.context.scene.objects.link(mesh_object)
    return mesh_object
#
def makeblendermeshob(name, PointList, EdgeList = None, FaceList = None):
    '''Generates a mesh object and datablock.
    '''
    mesh = makeblendermesh(name, PointList, EdgeList, FaceList)
    mesh_object = makeblendercachedob(name, mesh)
    return mesh_object
#
def makeblendercleanmeshob(name, PointList, EdgeList = None, FaceList = None):
    '''Generates a mesh object and datablock.
    Automatically remove doubled verticies.
    '''
    mesh_object = makeblendermeshob(name, PointList, EdgeList, FaceList)
    bpy.context.scene.objects.active = mesh_object
    bpy.ops.object.mode_set(mode='EDIT')
    bpy.ops.mesh.remove_doubles(threshold=MINDISTANCE)
    bpy.ops.object.mode_set(mode='OBJECT')
    return mesh_object

# These are mostly to remind me how to do these transformations
def setobjectposition(ob,pos):
    ob.location = pos
#
def setobjectrotation(ob,rot):
    ob.rotation_euler = rot
#
def setobjectsize(ob,size):
    ob.scale = size
#
def make_parent(parent_object,childlist):
    for child in childlist:
        child.parent = parent_object
    
#################################################
#################################################
# main crystal stuff
#################################################
#################################################

#################################################
# Vector utility functions
#################################################

def point_to_plane(point, plane_point, plane_normal):
    '''Return the projection of the point onto the plane along the normal.
    
    point is the point to project
    plane_point is any point on the plane
    plane_normal is the normal of the plane
        (does not need to be a unit vector)
    '''
    difference = plane_point - point
    projection = difference.project(plane_normal)
    new_point = point + projection
    return new_point

def rotate(point, axis1, axis2, angle):
    '''Returns the point rotated around the axis by the angle.
    
    The axis is defined by axis1 and axis2.
        Order matters.
        All points are Vectors.
    The angle is in radians???
    '''
    current_radius = point - axis1
    axis = axis2 - axis1
    rotation_matrix = Rotation(angle, 3, axis)
    new_radius = current_radius * rotation_matrix
    new_point = new_radius + axis1
    return new_point

def n_gon(point_list):
    ''' Return a list of faces comprising an n-gon. Quads prioritized.
    
    point_list is a list of the indexes of the points that
    should comprise the n-gon, in the order desired (right hand rule).
    
    For best results, the points should be planar.
    
    NOTE: This function is depreciated, as Blender now supports native n-gons
    simply put all the points into the "face" list and away you go!
    '''
    # recursion!
    def recurse_faces(plist, faces):
        ''' Return the faces, walk down plist until there are none left.
        '''
        if len(plist) < 3: return
        elif len(plist) == 3:
            # make a tri
            faces += [[plist[0], plist[1], plist[2]]]
        else:
            # make a quad
            faces += [[plist[0], plist[1], plist[-2], plist[-1]]]
        recurse_faces(plist[1:-1], faces)
        return
    face_list = []
    recurse_faces(point_list,face_list)
    return face_list

def ray_to_plane(ray_point, ray_vector, plane_point, normal_vector,
                 limit_direction=False, limit_distance=False,
                 check_normal=False):
    """ Return the point where the ray intersects the plane.
    
    ray_point is point where the ray originates.
    ray_vector is the direction of the ray
        (also used for distance, if limit_distance is enabled)
    plane_point is any point on the plane
    normal_vector is the normal vector of the plane
        (does not need to be a unit vector)
    limit_direction to True only looks toward where ray_vector points.
    limit_distance to True limits the search to within ray_vector's length.
    check_normal to True only finds planes with normals facing the
    same direction as ray_vector.
    
    If there is no point of intersection (with all of the chosen limitations)
    return None.
    """
    difference = ray_point - plane_point
    denominator = normal_vector.dot(ray_vector)
    # the plane and the vector are paralell
    if denominator == 0:
        #print("plane and line are paralell")
        #print("norm =", normal_vector)
        #print("ray =", ray_vector)
        return None
    
    # the plane and the vector are facing eachother
    if (check_normal and (denominator <= 0) ):
        #print("wrong normality")
        return None
    
    # find the scaling factor for ray_vector to reach the plane
    distance = -normal_vector.dot(difference)/denominator
    
    # the plane is in the wrong direction
    if limit_direction and (distance <= 0):
        #print("wrong direction")
        return None
    # the plane is too far away
    if limit_distance and (distance > ray_vector.magnitude):
        #print("intersect is too far away")
        return None
    # add the scaled vector to the starting point to get the
    # point on the plane.
    point_on_plane = ray_point + (distance * ray_vector)
    return point_on_plane

#################################################
# Crystal face-generating code
#################################################

def nearest_plane(start_point, direction, boundary_planes, ignore_indicies,
                  adjacent_plane=None):
    '''Return the closest point, and the index of the plane on which it lies.
    
    start_point is the position to start searching from
    direction is the vector to search along
    boundary_planes is the list of planes to check
        (currently, all planes use a single vector for both the
        point and the normal)
    ignore_indicies is the list of planes to skip when checking for intersects
    adjacent_plane is the plane paralell to "direction" 
        and is used to resolve ties when intercepts coincide.
        see "sharpest angle" in the comments below
    
    note that it currently ignores:
    planes in the opposite direction, and 
    planes with normals facing toward the point.
    '''
    # found_points is a list of points that have been found
    # to intersect direction from start_point.
    # format: [(distance, point, plane index),...]
    found_points = []
    # build a list of the closest planes
    for check_idx in range(len(boundary_planes)):
        # except the faces that we should ignore
        if check_idx in ignore_indicies: continue
        # the plane to find the intercept on
        current_plane = boundary_planes[check_idx]
        # find the intercept, in the right direction
        check_point = ray_to_plane(start_point, direction,
                     current_plane, current_plane,
                     limit_direction=True, check_normal=True)
        # if it didn't intercept, try the next face
        if check_point == None: continue
        # if you got a point, find how far away it is
        check_vector = check_point - start_point
        check_distance = check_vector.magnitude
        # then add the data to the list
        found_points += [(check_distance, check_point, check_idx)]
    # if you didn't find any points, give up. All hope is lost!
    if len(found_points) == 0: return (None, None)
    # if you found at least one point
    # find the closest point to current_point
    #   this will sort by the first item in the tuple
    found_points.sort()
    # in case several points are all closest
    closest_distance = found_points[0][0]
    closest_points = []
    for point in found_points:
        # put only those points with the same closest approach
        # in the list of closest points
        if point[0] <= closest_distance + MINDISTANCE:
            this_plane = boundary_planes[point[2]]
            new_direction = adjacent_plane.cross(this_plane)
            figure_of_merit = direction.dot(new_direction)
            closest_points += [(figure_of_merit, point)]
        else:
            break
    # sort the points by the dot product
    closest_points.sort()
    # the face we want is the one with the smallest dotproduct
    # because this means it has the most opposed normal vector
    point_we_want = closest_points[0][1]
    #point_we_want = found_points[0]
    nearest_point = point_we_want[1]
    nearest_index = point_we_want[2]
    # we're done!
    return nearest_point, nearest_index

def included_edge_point(planes):
    '''Return starting info for the solid.

    In order to traverse all the faces in a solid, we need to start
    somewhere. We begin with the plane that lies closest the origin,
    because we're guranteed that at least that plane will be used.

    The edge-finder uses a rather inefficient method that requires
    a starting point and a plane. This means that we need to work our way
    from having no idea where we are to being in the intersection of
    two planes, and knowing what they are.
    
    The starting info is: starting_point, plane_index, and starting_index.
    
    plane_index is the closest plane, and the first one to encircle
    other_plane is the index of the first plane to search along
    intercept_point is the point to start searching at

    starting_point should lie on the intersection of the planes indicated
    by plane_index and starting_index
    '''
    # distances is [(distance, plane index), ...]
    distances = []
    # record the closest point for each plane
    for idx in range(len(planes)):
        plane = planes[idx]
        dist = plane.magnitude
        distances += [(dist,idx)]
    # sort uses the first item in the tuple
    distances.sort()
    # this is the index of the closest plane
    #   That is, the one with the shortest definition vector
    plane_index = distances[0][1]
    # and the point that is closest to the origin
    plane_norm = planes[plane_index]
    # now to find another point on the plane,
    # so we can set up a vector to search along.
    # First find the axis with the smallest quantity of the normal vector.
    norm_comp = [[abs(plane_norm[0]),0], 
              [abs(plane_norm[1]),1], 
              [abs(plane_norm[2]),2]]
    norm_comp.sort()
    shortest_axis = norm_comp[0][1]
    # Now make a unit vector along this axis,
    # go that distance from the point we got earlier,
    # and project the other_point onto the plane!
    offset = [0,0,0]
    offset[shortest_axis] = 1.0
    other_point = plane_norm + Vector(offset)
    other_point = point_to_plane(other_point, plane_norm, plane_norm)
    # now we can find the closest plane in this direction
    direction_to_check = other_point - plane_norm
    # search all the planes for the nearest point along this vector
    intercept_point, other_plane = nearest_plane(plane_norm,
                                                direction_to_check,
                                                planes,
                                                [plane_index],
                                                plane_norm)
    # and that's all folks!
    return (plane_index, other_plane, intercept_point)
    

def plane_edges(starting_point, plane_index, starting_index, boundary_planes):
    """Return a list of ccw points where plane intersects boundary_planes.
    Also return a list of the indicies of the boundary_planes contacted, in
    order of contact.
    
    starting_point is a point on the intersection of plane and
    starting
    plane_index is the index of the plane to encircle
    starting_index is the index of the plane to start with
    boundary_planes is the list of planes
    
    All of the planes are a single vector used to define both
    the position and the normal of the plane.
    
    If the faces do not form a complete boundary, return None.
    """
    # Make a copy so that we can compare to the starting point if necessary
    current_point = starting_point.copy()
    current_index = starting_index
    boundary_points = []
    # These planes will not be checked, since each one should only
    # intersect once.
    # we put "plane_index" in here because we should never contact ourselves
    # we should never contact ourselves ANYWAY... but somehow we keep doing so
    # Why does this happen???
    planes_contacted = [starting_index, plane_index]
    plane = boundary_planes[plane_index]

    iterations = 0
    while True:
        # we need to find our starting plane again to close the loop
        # but we also should ignore it at first, so we don't re-find it too soon
        # see above... why DOES this happen?
        if iterations == 2: planes_contacted.pop(0)
        current_plane = boundary_planes[current_index]
        # what direction to look for the next intersect
        direction = plane.cross(current_plane)
        if direction.magnitude == 0:
            print("zero magnitude direction!")
            print("reference plane index", plane_index)
            print("current plane index", current_index)
            print("starting plane index", starting_index)
            print("contacted so far", planes_contacted)
        # check all the faces for intersections
        current_point, current_index = nearest_plane(current_point, direction,
                                                     boundary_planes, 
                                                     planes_contacted,
                                                     current_plane)
        # if you didn't find any points, give up. All hope is lost!
        if current_point == None:
            print("failed on plane", plane_index, "starting along", starting_index)
            return (None, None)
        # add the current point to the list of points
        boundary_points += [current_point]
        #add the current index to the list of indexes to ignore
        planes_contacted += [current_index]
        # if current_index is where we started, we're done!
        if current_index == starting_index: break
        iterations += 1
    
    # If we got out, the loop is complete, having
    # returned to the starting plane.
    # Remove itself, since this doesn't tell us anything new
    planes_contacted.pop(0)
    return (boundary_points, planes_contacted)

def make_solid_from_points(plane_inputs, label = None):
    """Create a solid from a list of points (the "figure").
    
    points is a list of face normal/position vectors
        should not be vectors! [(x, y, z), ...]
    label is what to call the mesh
    """
    # container for the face boundaries
    planes = []
    # container for the points
    points = []
    # convert the point tuples into vectors
    # use them as the bounding plane normals and locations
    for plane_position in plane_inputs:
        cur_point = Vector(plane_position)
        planes += [cur_point]
    # list of faces, 3 or more points each. Use point indicies.
    faces = []
    # Initialize the face walk
    starting_plane, nearest_plane_idx, nearest_point = \
                    included_edge_point(planes)
    # planes to make, populated when making the nearest plane, and each
    # plane after it.
    # Store which faces are contacted, where, and from what plane.
    # This ensures that only relevant planes are checked, as the edges
    # propagate from one plane to another.
    # It is quite possible that some planes will never be contacted.
    planes_to_make = [(starting_plane, nearest_point, nearest_plane_idx)]
    # keep going until you run out of new planes to traverse.
    for this_info in planes_to_make:
        # Set up the current plane, and the starting plane, and point.
        this_plane_idx = this_info[0]
        start_point = this_info[1]
        start_plane = this_info[2]
        # Find the edge points of the plane.  Should never be "None".
        these_points, found_planes = plane_edges(start_point,
                                                 this_plane_idx,
                                                 start_plane, planes)        
        # If it is ever "None" something is wrong,
        # probably the starting planes are non-water-tight.
        if these_points is None:
            print("No Points Found")
            #print("planes to make", planes_to_make)
            #print("points so far", points)
            continue
        # the list of the indexes of the new points
        # these don't start at zero if there are already
        # points in the list from previous faces
        number_of_points_so_far = len(points)
        point_indicies = [i for i in range(number_of_points_so_far, 
                                           number_of_points_so_far +
                                           len(these_points))]
        # we need to find at least three points
        # otherwise, how do we make a face?
        if len(point_indicies) < 3:
            print("Too Few Points Found")
            #print("planes to make", planes_to_make)
            #print("points so far", points)
            return None
        # the new face, added to the old
        faces += [point_indicies]
        
        # the old way of doing things, also safer?
        #print(point_indicies)
        #faces += n_gon(point_indicies)
        
        # add the new points to the old
        points += these_points
        # process all the planes that were contacted this time around
        for idx in range(len(found_planes)):
            # find the index of the found plane
            plane_idx = found_planes[idx]
            # check if it is already on the list of planes to make
            make = True
            for info in planes_to_make:
                if info[0] == plane_idx:
                    make = False
                    break
            # If it isn't on the list, add this plane to the list of
            # planes to make.
            if make:
                # Offset by one, since the plane in question
                # uses the next point to start at.
                # (the other loop will be going backward!)
                if idx + 1 == len(these_points): point_idx = 0
                else: point_idx = idx + 1
                planes_to_make += [(plane_idx,
                                    these_points[point_idx],
                                    this_plane_idx)]
    if label is None:
        label = "{} sided solid".format(len(faces))
    # If all of that worked, tell Blender to make the mesh object.
    # use the clean version, since we will have lots of duplicate points
    # at some point, I should keep track of which faces are associated with
    # which points so that we can do this during processing
    # it would also possibly speed up face finding generation?
    ob = makeblendercleanmeshob(label, points, FaceList = faces)
    # Note the faces that were used
    used_points = [i[0] for i in planes_to_make]
    return ob, used_points

#################################################
# Utility functions
#################################################

def make_random_solid_from_points(points, rand_magnitude):
    # make a randomized copy using the points as a base figure
    # this will keep the face angles, but randomize their positions
    # rand_magnitude is from 0.0 (no variation) to 1.0 (up to double the size)
    #   but actually any float should work fine
    random_points = []
    for point in points:
        # from -1 to 1
        rand_cent = (random() - 0.5) * 2.0
        # 1 +- rand_magnitude
        scale_factor = 1.0 + (rand_cent * rand_magnitude)
        scaled_point = point * scale_factor
        random_points += [scaled_point]
    #make the solid
    ob, used_points = make_solid_from_points(random_points)
    return ob

def make_solid_from_figure(source_ob = None):
    # Create a solid from a point defined plane figure
    if source_ob is None:
        source_ob = bpy.context.active_object
    points_raw = source_ob.data.vertices
    points = [i.co for i in points_raw]
    #points = [(4,0,0),(-4,0,0),(0,0,-1),(0.2,-1,1),(0,1,1)]
    ob, used_points = make_solid_from_points(points)
    # set the new object to the same position, rotation, size as the original
    ob.location = source_ob.location
    ob.rotation_euler = source_ob.rotation_euler
    ob.scale = source_ob.scale
    return ob

def make_figure_from_mesh_data(source_ob = None):
    # Create a definition figure from the faces of
    # an existing mesh object
    if source_ob is None:
        source_ob = bpy.context.active_object
    # working bmesh
    bm = bmesh.new()
    # populate bmesh from target
    bm.from_mesh(source_ob.data)
    # grab the faces
    faces_raw = bm.faces
    figure_points = []
    for face in bm.faces:
        normal_vec = face.normal
        # any point will do, but let's use the best one!
        a_point = face.calc_center_median_weighted()
        scaled_normal = normal_vec.dot(a_point)*normal_vec
        figure_points += [scaled_normal]
    label = "{} vector figure".format(len(figure_points))
    AllEdges = [(0,1),(1,2),(2,3),(3,0),(2,0),(1,3)]
    ob = makeblendermeshob(label, figure_points, EdgeList = AllEdges)
    ob.location = source_ob.location
    ob.rotation_euler = source_ob.rotation_euler
    ob.scale = source_ob.scale
    return ob

def move_center(source_ob = None, new_center = None):
    '''Move the plane figure center
    source_ob is the old object to draw point data from
    new_center is the new center location
        If there's no center given, use the last created point
    '''
    # So that there are some edges to click on and visualize
    AllEdges = [(0,1),(1,2),(2,3),(3,0),(2,0),(1,3)]
    if source_ob == None:
        source_ob = bpy.context.active_object
    points_raw = source_ob.data.vertices
    source_points = [i.co for i in points_raw]
    if new_center is None:
        # Uncomment the following to use the cursor to re-position the center
        #cursor = bpy.context.scene.cursor_location
        #new_center = cursor - ob.location
        # currently, use the last point created as the new center
        new_center = source_points.pop(-1)
    points = []
    # find the new face vectors
    for point in source_points:
        new_point = ray_to_plane(new_center, point, point, point) - new_center
        points += [new_point]
    ob = makeblendermeshob("newcenter", points, EdgeList = AllEdges)
    #ob.location = Vector(cursor)
    ob.location = source_ob.location + new_center
    ob.rotation_euler = source_ob.rotation_euler
    ob.scale = source_ob.scale
    return ob
    
# Handy for generating lots of sub-fragments of crystals
def move_and_generate():
    original_ob = bpy.context.active_object
    fig_ob = move_center(original_ob)
    solid_ob = make_solid_from_figure(fig_ob)
    fig_ob.parent = solid_ob
    fig_ob.location = (0,0,0)
    bpy.context.scene.objects.active = original_ob

def make_multiple_solids():
    all_sources = bpy.context.selected_objects
    for source in all_sources:
        make_solid_from_figure(source)

def generate_adjacent_figures():
    ''' generates a set of voronoi cells with equal weights
    centered on each vertex in the source object

    WARNING: This can take really quite a long time to run!
    '''
    
    # set up the proto figure
    largest_dim = 1.5
    # make a cube, the proto-figure is to make sure
    # that the figure is bounded
    proto_fig_start = [Vector((largest_dim,0,0)), 
                       Vector((0,largest_dim,0)), 
                       Vector((0,0,largest_dim))]
    proto_figure = []
    # mirror the starting vectors
    for vert in proto_fig_start:
        proto_figure += [vert, -vert]
    # get the positions from the active object's vertex locations
    source_ob = bpy.context.active_object
    points_raw = source_ob.data.vertices
    source_points = [i.co for i in points_raw]
    for origin in source_points:
        points = []
        points += proto_figure
        for other in source_points:
            if other == origin: continue
            face = (other - origin) / 2.0
            points += [face]
        ob = makeblendermeshob("adjacent figure", points, EdgeList = [(0,1)])
        ob.location = origin
        
def make_cluster_from_figure(num_of_chunks, dupe_per_chunk, rand_magnitude):
    '''Generate a group of similar objects from a single figure

    num_of_chunks is the number of aligned groups
    dupe_per_chunk is the number of randomized objects per group

    The selected object must be a proto-"figure" mesh for this to work properly
    '''
    source_ob = bpy.context.active_object
    points_raw = source_ob.data.vertices
    source_points = [i.co for i in points_raw]
    for chunk_num in range(num_of_chunks):
        # generate the rotation stuff
        rot_i = random() * 4.0
        rot_j = random() * 4.0
        rot_k = random() * 4.0
        this_rotation = (1.0, rot_i, rot_j, rot_k)
        rand_cent = (random() - 0.5)
        rand_scale = 1.0 + (rand_cent * rand_magnitude)
        scale = (rand_scale,rand_scale,rand_scale)
        for dupe_num in range(dupe_per_chunk):
            new_ob = make_random_solid_from_points(source_points,
                                                   rand_magnitude)
            new_ob.rotation_mode = 'QUATERNION'
            new_ob.rotation_quaternion = this_rotation
            new_ob.scale = scale
    
if __name__ == "__main__":
    # do the necessary stuff
    #print('testing the script')
    #make_figure_from_mesh_data()
    #make_solid_from_figure()
    make_solid_from_figure(make_figure_from_mesh_data())
    #make_multiple_solids()
    #move_center()
    #move_and_generate()
    #generate_adjacent_figures()
    #make_cluster_from_figure(2, 3, 0.2)
    #print('Finished!')

# Notes
# Envelope breach bug exists where where more than 8 faces share a vertex.
