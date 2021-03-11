try:
    from maya import cmds
    from maya.api import OpenMaya as om
except ImportError:
    print("Must be in a maya environment!")
    raise

import logging
from rig.maya import dag, get_logger
log = get_logger(__name__)

def get_pole_vector(A, B, C, factor=2):
    """
    Given three joitns (ex: shoulder, elbow, wrist),
    creates a locator at a convenient position for a poleVector control

    :param jointA: starting joint
    :param jointB: middle joint
    :param jointC: end joint
    """
    # Create a locator
    loc = cmds.spaceLocator(name="poleVector_temp")

    # Get joint positions
    positions = dag.get_positions([A, B, C], space='world')

    # Get their middle position
    middle = get_avg_pos([A, C])
    
    # Get a vector aiming down the first joint to the third one    
    downAxis = positions[2] - positions[0]
    downAxis.normalize()
    
    # Get a vector aiming from the middle position, to the middle joint
    aimAxis = positions[1] - middle
    distanceToMid = aimAxis.length()
    aimAxis.normalize()

    # Get orthogonal vectors to form a basis that will describe orientation
    upAxis = aimAxis ^ downAxis
    downAxis = aimAxis ^ upAxis
    
    # Now we can build an orthonormal basis
    matRotation = om.MMatrix()
    
    matRotation.setElement(0, 0, aimAxis.x)
    matRotation.setElement(0, 1, aimAxis.y)
    matRotation.setElement(0, 2, aimAxis.z)

    matRotation.setElement(1, 0, upAxis.x)
    matRotation.setElement(1, 1, upAxis.y)
    matRotation.setElement(1, 2, upAxis.z)

    matRotation.setElement(2, 0, downAxis.x)
    matRotation.setElement(2, 1, downAxis.y)
    matRotation.setElement(2, 2, downAxis.z)

    # Get a rotation from it
    rotation = om.MTransformationMatrix(matRotation).rotation()

    # Get a matrix describing the average position between joitns
    mat = om.MTransformationMatrix(om.MMatrix())
    mat.translateBy(middle, om.MSpace.kWorld)

    # Orient to orthonormal basis
    mat.rotateBy(rotation, om.MSpace.kWorld)

    # Move by twice the distance from mid point to mid joint, in object space
    mat.translateBy(om.MVector(distanceToMid*factor, 0.0, 0.0), om.MSpace.kObject)

    # Finally, apply matrix to locator
    cmds.xform(loc, matrix=mat.asMatrix(), worldSpace=True)


def get_avg_pos(nodes, asPoints=False):
    """
    Gets average position between objects
    :param str|list nodes:
    :return position:
    """
    # Get positions from nodes
    positions = dag.get_positions(nodes, asPoints=asPoints)

    # Create an MVector to hold our result
    result = om.MVector()

    # Do sum of positions, then divide them by number of positions
    # to get average position, or mid point from origin
    for pos in positions:
        result += pos
    
    result /= len(positions)

    return result

def average_in_axis(nodes, axis='x', space=om.MSpace.kObject):
    """
    Averages objects' position in a given axis
    :param str|list nodes:
    :param str axis:
    :param str|MSpace space:

    .. note::
        This action is not undoable
    """
    # Make sure space is an MSpace constant
    space = dag._process_space(space)

    # Ensure axis input is always lower case
    axis = axis.lower()

    # Get MFnTransform objects from nodes
    transforms = dag.get_function_sets(nodes, fn=om.MFnTransform)

    # Store their positions in a list
    positions = [t.translation(space) for t in transforms]

    # And add them up to calc the average position in axis

    # The following line works, because vectors and points in the maya api
    # have properties named after axes. For example, MVector.x, or MPoint.z
    avg = sum([getattr(position, axis) for position in positions]) / len(positions)
    
    for mTransform, pos in zip(transforms, positions):
        if axis == 'x':
            newPosition = om.MVector(avg, pos.y, pos.z)
        if axis == 'y':
            newPosition = om.MVector(pos.x, avg, pos.z)
        if axis == 'z':
            newPosition = om.MVector(pos.x, pos.y, avg)

        mTransform.setTranslation(newPosition, space)


def zero(obj):
    """
    Zeroes local transforms of obj
    """
    trans_obj = dag.get_function_sets(obj)[0]
    trans_obj.setTransformation(om.MTransformationMatrix(om.MMatrix.kIdentity))


def snap(A, B, rotate=True, translate=True):
    """
    Snaps A onto B, with the option to only do rotation,
    translation, or both
    """
    # Get parent of A
    par_a = cmds.listRelatives(A, parent=True)
    mat_a = om.MMatrix()
    
    # If object A has a parent, we need its world mat
    # to apply transformation in object space later
    if par_a:
        mat_a = dag.get_matrix(par_a[0], space='world')[0]

    # Compare matrices in case we're already at the same spot
    mat_world_a, mat_world_b = dag.get_matrix([A, B], space='world')
    trans_matrix_a = om.MTransformationMatrix(mat_world_a)
    trans_matrix_b = om.MTransformationMatrix(mat_world_b)
    
    if trans_matrix_a.isEquivalent(trans_matrix_b):
        log.error("{0} is already aligned to {1}".format(A, B))
        return

    # Apply B's transformation in the space of A
    result = mat_world_b * mat_a.inverse()
    trans_result = om.MTransformationMatrix(result)

    mat_local_a = dag.get_matrix(A, space='object')[0]
    result_a = om.MTransformationMatrix(mat_local_a)
    
    if translate:
        result_a.setTranslation(trans_result.translation(om.MSpace.kTransform), 
                                om.MSpace.kTransform)
    
    if rotate:
        result_a.setRotation(trans_result.rotation())
    
    # Apply result to A
    xform_a = dag.get_function_sets(A, fn=om.MFnTransform)[0]
    xform_a.setTransformation(result_a)