try:
    from maya import cmds
except ImportError:
    print("Must be in a maya environment!")
    raise

from rig.maya.dag import get_positions

def create_line(objects, attach=True, attachParents=[], name=""):
    """
    Creates a line between objects, that optionally
    attaches to each
    """
    print("Attach is: {}".format(attach))
    positions = get_positions(objects)
    curve = create_from_points(positions, name=name, degree=1)

    # Rig CVs to each object
    if attach:
        if not attachParents:
            attachParents = objects[:]
        
        print("Attaching...")
        cvs = get_cvs(curve)
        
        for i in range(len(objects)):
            cluster = cmds.cluster(cvs[i])
            cmds.parentConstraint(objects[i], cluster, maintainOffset=True)
    
    return curve

def get_cvs(curve):
    """
    Given a curve, return its CVs (flattened)
    :param str curve: name of curve object
    :returns list cvs: list of component cvs
    """
    return cmds.ls("{0}.cv[*]".format(curve), flatten=True)


def get_cv_positions(cvs):
    """
    Given some components, query their position
    in world space
    :param list cvs:
    :returns list positions:
    """
    positions = list()

    for cv in cvs:
        ws = cmds.xform(cv, query=True, worldSpace=True, translation=True)
        positions.append(ws)

    return positions


def create_from_points(points, degree=1, name="curve#"):
    knotList = [0]

    if degree == 1:
        knotList.extend(range(1, len(points)))
    if degree == 3:
        knotList.extend([0])
        knotList.extend(range(len(points) - 2))
        knotList.extend([knotList[-1], knotList[-1]])

    curve = cmds.curve(degree=degree, point=points, knot=knotList)
    curve = cmds.rename(curve, name)

    return curve


def reorient(curve, downAxis):
    x = 0
    y = 0
    z = 0
    if downAxis == "x" or "-x":
        z = z + 90
    elif downAxis == "y" or "-y":
        y = 90
    else:
        x = x + 90
    cmds.rotate(x, y, z, get_cvs(curve))