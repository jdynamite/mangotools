import math
from six import string_types

try:
    from maya import cmds
    from maya.api import OpenMaya as om
except ImportError:
    print("Must be in a maya environment!")
    raise


def get_list(nodes, msel=None):
    """
    Get an MSelectionList filled with nodes
    :param str|list nodes: list or single node
    :return list: MObjects representing nodes
    """
    nodes = _process_nodes(nodes)
    
    if not msel:
        msel = om.MSelectionList()
    
    for node in nodes:
        if cmds.objExists(node):
            msel.add(node)
    
    return msel

def get_dag_paths(nodes, msel=None):
    """
    Get dag paths related to nodes
    :param str|list nodes: list or single node
    :returns dagPaths: list of dagPaths
    """
    msel = get_list(nodes, msel)
    if msel.length == 1:
        return msel.getDagPath(0)
    else:
        return [msel.getDagPath(i) for i in range(msel.length())]

def get_mobjects(nodes, msel=None):
    """
    Get MObjects from maya nodes
    :param str|list nodes: list or single node
    :returns MObjects:
    """
    msel = get_list(nodes, msel)
    if msel.length == 1:
        return msel.getDependNode(0)
    return [msel.getDependNode(i) for i in range(msel.length())]

def get_function_sets(nodes, fn=om.MFnTransform):
    """
    Get an OpenMaya function set that can be given dag paths as input
    :param OpenMaya function set:
    :return list function_sets:
    """
    return list(map(lambda d: fn(d), get_dag_paths(nodes)))

def get_matrix(nodes, space='world'):
    """
    Get matrix from each node, in the provided space
    :param str space:
    :return list(MMatrix) matrices:
    """
    nodes = _process_nodes(nodes)
    matrices = list()
    world = space == 'world'
    
    for node in nodes:
        mat = cmds.xform(node, query=True, matrix=True, worldSpace=world, objectSpace=not world)
        matrices.append(om.MMatrix(mat))
    
    return matrices

def _process_nodes(nodes):
    """
    Convenience function to process node arguments,
    and verify they exist in the scene
    
    :param str|list nodes:
    :returns list nodes:
    :raises: RuntimeError when a node can't be found in the scene
    """
    if isinstance(nodes, string_types):
        nodes = [nodes]
    for node in nodes:
        if not cmds.objExists(node):
            raise RuntimeError("{} doesn't exist.".format(node))
    return nodes

def _process_space(space):
    """
    Get an MSpace constant based on a string or MSpace input
    :returns om.MSpace space: constant
    """
    print(space)
    
    if isinstance(space, string_types):
        space = space.lower()
        return om.MSpace.kWorld if space == 'world' else om.MSpace.kObject
    else: 
        return space

def get_positions(nodes, space=om.MSpace.kWorld, asPoints=False):
    """
    Get positions of nodes in desired space,
    if space is not equal to 'world', will use object space

    :param list|str nodes:
    :param str|MSpace space:
    :param bool asPoints: 
        Whether or not to return values as MPoints, default is MVector 
        The biggest difference is MPoints supply an extra 4th value,
        and operating with matrices has different behaviors if
        dealing with points or vectors.
    :returns positions:
    :rtype: MVector or MPoint when asPoints is True
    """
    # Ensure space is an MSpace constant
    space = _process_space(space)
    
    # Get MFnTransforms for each node
    transforms = get_function_sets(nodes, fn=om.MFnTransform)
    
    # Return their translation
    vectors = list(map(lambda t: t.translation(space), transforms))

    if not asPoints:
        return vectors
    else:
        return [om.MPoint(vec.x, vec.y, vec.z) for vec in vectors]

def get_rotations(nodes, space=om.MSpace.kWorld, asQuaternion=False):
    """
    Get positions of nodes in desired space,
    if space is not equal to 'world', will use object space

    :param list|str nodes:
    :param str|MSpace space:
    :param bool asQuaternion:
        Whether or not to return values as MQuaternion or degrees
    :returns rotations:
    :rtype: list of degrees, or an MQuaternion when asQuaternion is True
    """
    # Get matrices
    mat = get_matrix(nodes, space)

    # Create a MTransformationMatrix for each
    transforms = [om.MTransformationMatrix(m) for m in mat]
    
    result = list(map(lambda t: t.rotation(asQuaternion=asQuaternion), transforms))

    # Return their values
    if asQuaternion:
        return result
    else:
        return [[math.degrees(r) for r in eulers] for eulers in result]