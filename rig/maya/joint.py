import re
from collections import defaultdict

try:
    from maya import cmds
    MAYA_AVAILABLE = True
except ImportError:
    MAYA_AVAILABLE = False


def get_joints():
    """
    Gets all joints in scene

    :returns tuple(list, dict): returns a tuple containing a list of
        joints and a default dictionary with sided joints
    """

    if not MAYA_AVAILABLE:
        raise RuntimeError("Not in a maya environment")

    # Init dictionary for joints w/ sides
    sided_joints = defaultdict(str)

    # Get all joints
    joints = cmds.ls(type='joint')

    # Find right-sided joints
    side_matcher = re.compile(r'_r\d?', flags=re.IGNORECASE)
    rjoints = filter(lambda v: side_matcher.search(v), joints)

    # Fill side dictionary
    for jnt in rjoints:
        for sub in ['_l', '_L']:
            ljoint = side_matcher.sub(sub, jnt)
            if cmds.objExists(ljoint):
                sided_joints[jnt] = ljoint
                sided_joints[ljoint] = jnt

    return joints, sided_joints