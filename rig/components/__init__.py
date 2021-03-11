try:
    from maya import cmds
except ImportError:
    print("Must be in a maya environment!")

from rig.config.naming import Naming
from rig.maya.base import MayaBaseNode
from rig.maya import dag

compose = MayaBaseNode.compose_name


def make_space_grp(driver, name=None, parent='grp_spaces'):
    """
    Make a space group that is driven through a parent offset matrix
    by the passed in argument: driver
    """

    if not isinstance(driver, MayaBaseNode):
        driver = MayaBaseNode(driver)

    if not name:
        name = Naming(driver.nice_name)
        name.node_type = 'space'
        name.role = None
        name = str(name)
    
    if not cmds.objExists(name):
        space = MayaBaseNode(cmds.group(empty=True, name=name))
    else:
        space = MayaBaseNode(name)

    cmds.connectAttr(driver.plug('worldMatrix[0]'), 
                     space.plug('offsetParentMatrix'))

    if cmds.objExists(parent):
        space.parent = parent
    
    return space
    

def add_no_roll_joints(start_jnt, end_jnt, n=3, source_axis="X", target_axis="X"):
    """
    Add n number of roll joints between start and end joints, that negate
    some portion of the twist of start_jnt, and are parented to start_jnt

    .. note::
        This solution will flip when driver goes past 180,
        for a non-flip, use custom nodes or weighted orients with IKs

    :param str|MayaBaseNode start_jnt:
    :param str|MayaBaseNode end_jnt:
    :param int n: number of joints to create
    :returns tuple(roll_joints, new_nodes): newly created joints and nodes
    """
    roll_joints = list()
    new_nodes = list()

    assert n >= 3, "You need at least 3 joints"

    if not isinstance(start_jnt, MayaBaseNode):
        start_jnt = MayaBaseNode(start_jnt)
    
    if not isinstance(end_jnt, MayaBaseNode):
        end_jnt = MayaBaseNode(end_jnt)

    # Calculate step, we want a joint at the beginning and end
    step =  1.0 / (n - 1)

    # Get a vector from start to end
    a, b = dag.get_positions([start_jnt.long_name, end_jnt.long_name])

    target_vector = b - a
    side = start_jnt.side
    descriptor = start_jnt.descriptor

    # Create twist extractor
    local_mtx = cmds.createNode('multMatrix')
    cmds.connectAttr(start_jnt.plug('worldMatrix[0]'), local_mtx + '.matrixIn[0]')
    
    # Hold inverse matrix of start joint
    hold_mtx = cmds.createNode('holdMatrix')
    cmds.connectAttr(start_jnt.plug('worldInverseMatrix[0]'), hold_mtx + '.inMatrix')
    cmds.connectAttr(hold_mtx + '.outMatrix', local_mtx + '.matrixIn[1]')
    
    # Disconnect input to cache value
    cmds.disconnectAttr(start_jnt.plug('worldInverseMatrix[0]'), hold_mtx + '.inMatrix')

    # Decompose result matrix
    twist_dcm = cmds.createNode('decomposeMatrix')
    cmds.connectAttr(local_mtx + '.matrixSum', twist_dcm + '.inputMatrix')

    # Output quaternion to an inverse quat to 'negate' the parent's twist about axis
    quat_inv = cmds.createNode('quatInvert')
    cmds.connectAttr(twist_dcm + '.outputQuat', quat_inv + '.inputQuat')

    # Connect the inverse to a quatToEuler so we can connect it to joint's rotation
    quat_to_euler = cmds.createNode('quatToEuler')
    cmds.setAttr(quat_to_euler + '.inputQuatW', 1)
    cmds.connectAttr(quat_inv + '.outputQuat{}'.format(source_axis), 
                     quat_to_euler + '.inputQuat{}'.format(source_axis))
    
    new_nodes.extend([local_mtx, hold_mtx, twist_dcm, quat_inv, quat_to_euler])
    source_axis = source_axis.upper()
    target_axis = target_axis.upper()

    for i in range(n):
        num = str(i+1).zfill(2)
        
        # Create a roll extraction joint
        jnt_name = compose(node_type="joint", role="roll", descriptor=descriptor + num, side=side)
        new_jnt = MayaBaseNode(cmds.joint(name=jnt_name))
        new_jnt.snap_to(start_jnt.long_name, rotate=True, translate=True)
        new_jnt.set_position(a + (target_vector * (step * i)))
        new_jnt.parent = start_jnt.long_name
        
        # Freeze rotations
        cmds.makeIdentity(new_jnt.long_name, r=True, apply=True)
        roll_joints.append(new_jnt)

        # Multiply result by a factor, so we don't twist all the way
        # this creates some conversion nodes, but quaternion slerp crashes maya
        mdl = cmds.createNode("multDoubleLinear")
        cmds.connectAttr(quat_to_euler + '.outputRotate{}'.format(source_axis), mdl + '.input1')
        cmds.setAttr(mdl + '.input2', 1 - (step * i))
        
        # Connect result
        cmds.connectAttr(mdl + '.output', new_jnt.long_name + '.rotate{}'.format(target_axis))
        
        # Store nodes
        new_nodes.append(mdl)
        
    
    return roll_joints, new_nodes


def add_roll_joints(start_jnt, end_jnt, n=2, source_axis="X", target_axis="X"):
    """
    Add n number of roll joints between start and end joints, that gain some
    proportion of the twist of the end_joint, and are parented to start_jnt

    .. note::
        This solution will flip when driver goes past 180,
        for a non-flip, use custom nodes or weighted orients with IKs

    :param str|MayaBaseNode start_jnt:
    :param str|MayaBaseNode end_jnt:
    :param int n:
    :returns list roll_joints: newly created joints
    """
    roll_joints = list()
    new_nodes = list()

    if not isinstance(start_jnt, MayaBaseNode):
        start_jnt = MayaBaseNode(start_jnt)
    
    if not isinstance(end_jnt, MayaBaseNode):
        end_jnt = MayaBaseNode(end_jnt)

    # Calculate step
    step =  1.0 / n

    # Get a vector from start to end
    a, b = dag.get_positions([start_jnt.long_name, end_jnt.long_name])

    target_vector = b - a
    side = start_jnt.side
    descriptor = start_jnt.descriptor

    # Create twist extractor
    # First, create a multMatrix node to set our target in local space
    local_mtx = cmds.createNode('multMatrix')
    cmds.connectAttr(end_jnt.plug('worldMatrix[0]'), local_mtx + '.matrixIn[0]')
    cmds.connectAttr(start_jnt.plug('worldInverseMatrix[0]'), local_mtx + '.matrixIn[1]')

    # Decompose result
    local_dcm = cmds.createNode('decomposeMatrix')
    cmds.connectAttr(local_mtx + '.matrixSum', local_dcm + '.inputMatrix')

    # Convert it to degrees
    quat_to_euler = cmds.createNode('quatToEuler')
    cmds.setAttr(quat_to_euler + '.inputQuatW', 1)
    cmds.connectAttr(local_dcm + '.outputQuat{}'.format(source_axis), 
                     quat_to_euler + '.inputQuat{}'.format(source_axis))

    new_nodes.extend([local_mtx, local_dcm, quat_to_euler])

    source_axis = source_axis.upper()
    target_axis = target_axis.upper()

    for i in range(1, n+1):
        # Compose a name for the new joint
        num = str(i).zfill(2)
        jnt_name = compose(node_type='joint', role='roll', descriptor=descriptor + num, side=side)

        # Create roll joint and snap to location
        new_jnt = MayaBaseNode(cmds.joint(name=jnt_name))
        new_jnt.snap_to(start_jnt.long_name)
        new_jnt.set_position(a + (target_vector * (step * i)))

        # Freeze joint rotations
        cmds.makeIdentity(new_jnt, r=True, apply=True)
        cmds.setAttr(new_jnt.plug('displayLocalAxis'), 1)

        # Parent under start_jnt and append to result
        new_jnt.parent = start_jnt.long_name
        roll_joints.append(new_jnt.long_name)

        # Multiply result by a factor, so we don't twist all the way
        # this creates some conversion nodes, but quaternion slerp crashes maya
        mdl = cmds.createNode("multDoubleLinear")
        cmds.connectAttr(quat_to_euler + '.outputRotate{}'.format(source_axis), mdl + '.input1')
        cmds.setAttr(mdl + '.input2', step * i)
        
        # Connect result
        cmds.connectAttr(mdl + '.output', new_jnt.long_name + '.rotate{}'.format(target_axis))
        
        # Store nodes
        new_nodes.extend([quat_to_euler])

    
    return roll_joints, new_nodes


def drive_constrained(drivers, driven, prefix="ikfkSwitch"):
    pass

def drive_blended_mtx(driver_a, driver_b, driven, prefix="ikfkSwitch", blend_attr="ctrl_ikfkSwitch_arm_l.ikFk"):
    """
    Given two drivers, drive a third joint
    with a blend matrix node

    .. note::
        First driver will be used as input matrix,
        and second one as the target matrix
    """

    if not isinstance(driver_a, MayaBaseNode):
        driver_a = MayaBaseNode(driver_a)
    
    if not isinstance(driver_b, MayaBaseNode):
        driver_b = MayaBaseNode(driver_b)
    
    if not isinstance(driven, MayaBaseNode):
        driven = MayaBaseNode(driven)

    side = driver_a.side
    desc = driver_a.descriptor

    # Blend matrix node to use for later
    blend_mtx = compose(node_type="blendMtx", role=prefix, descriptor=desc, side=side)
    blend_mtx = cmds.createNode("blendMatrix", name=blend_mtx)

    # Create a mult matrix node to input the inverse of the driven's parent
    driven_par = driven.parent

    # Multiply driven parent's world inverse * driver A's world mat
    mult_a = compose(node_type="multMtx", role=prefix, descriptor=desc, side=side)
    mult_a = cmds.createNode("multMatrix", name=mult_a)
    cmds.connectAttr(driver_a.plug('worldMatrix[0]'), mult_a + '.matrixIn[0]')
    cmds.connectAttr(driven_par.plug('worldInverseMatrix[0]'), mult_a + '.matrixIn[1]')
    cmds.connectAttr(mult_a + '.matrixSum', blend_mtx + '.inputMatrix')
    
    # And do the same with driver B
    mult_b = compose(node_type="multMtx", role=prefix, descriptor=desc, side=side)
    mult_b = cmds.createNode("multMatrix", name=mult_b)
    cmds.connectAttr(driver_b.plug('worldMatrix[0]'), mult_b + '.matrixIn[0]')
    cmds.connectAttr(driven_par.plug('worldInverseMatrix[0]'), mult_b + '.matrixIn[1]')
    cmds.connectAttr(mult_b + '.matrixSum', blend_mtx + '.target[0].targetMatrix')

    # Zero out output rotation by multiplying this result times the inverse of the driver

    # First, create a hold matrix to store the driver's inverse matrix
    hold_mtx = compose(node_type="holdMtx", role=prefix, descriptor="{}DrvnParentInv".format(desc))
    hold_mtx = cmds.createNode("holdMatrix", name=hold_mtx)
    cmds.connectAttr(driven.plug('inverseMatrix'), hold_mtx + '.inMatrix')
    
    # Now snip it (it's ok, the values will hold)
    cmds.disconnectAttr(driven.plug('inverseMatrix'), hold_mtx + '.inMatrix')

    # Get result in local space
    mult_local_mtx = compose(node_type="multMtx", role=prefix, descriptor="{}LocalRot".format(desc), side=side)
    mult_local_mtx = cmds.createNode("multMatrix", name=mult_local_mtx)
    cmds.connectAttr(blend_mtx + '.outputMatrix', mult_local_mtx + '.matrixIn[0]')
    cmds.connectAttr(hold_mtx + '.outMatrix', mult_local_mtx +'.matrixIn[1]')

    # Decompose result rotation
    decompose_rot = compose(node_type="dcm", role=prefix, descriptor="{}LocalRot".format(desc), side=side)
    decompose_rot = cmds.createNode("decomposeMatrix", name=decompose_rot)
    cmds.connectAttr(mult_local_mtx + '.matrixSum', decompose_rot + '.inputMatrix')

    # Drive rotation
    cmds.connectAttr(decompose_rot + '.outputRotate', driven.plug('rotate'))

    # Decompose translates
    decompose_pos = compose(node_type="dcm", role=prefix, descriptor="{}LocalPos".format(desc), side=side)
    decompose_pos = cmds.createNode("decomposeMatrix", name=decompose_pos)
    cmds.connectAttr(blend_mtx + '.outputMatrix', decompose_pos + '.inputMatrix')

    # Drive translate
    cmds.connectAttr(decompose_pos + '.outputTranslate', driven.plug('translate'))

    if blend_attr:
        cmds.connectAttr(blend_attr, blend_mtx + '.target[0].weight')