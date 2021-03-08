"""
Ideally I'd like to setup project configurations
from a web app framework.

That could ease management of projects and project configurations,
like naming conventions.

For now, this base config and default naming class can serve our
general purpose.
"""

import re
import os
import sqlite3
from collections import OrderedDict

def get_control_lib(file_name):
    """
    Returns an expected path for controls file
    :param str file_name:
    """
    path = re.split(r'/|\\', os.path.dirname(__file__))
    
    # Add a separator to windows drives (c: -> c:\)
    # otherwise ignored by os.path.join
    if path[0].endswith(':'):
        path[0] = path[0] + os.sep
    
    # Add file name
    path.extend([file_name])
    
    return os.path.join(*path)

class Config(object):
    """
    A config can describe the naming, and naming
    structure for a project or show

    This base config defines default values
    """
    PROJECT = "default"
    
    # Controls
    CONTROL_FILE = "controls.ctrl"
    CONTROL_SHAPES_FILE = get_control_lib(CONTROL_FILE)
    
    # Sides
    LEFT = 'l'
    RIGHT = 'r'
    CENTER = 'c'
    
    # Regions
    TOP = 'tp'
    BOTTOM = 'bt'
    OUTSIDE = 'ot'
    INSIDE = 'in'
    
    # Delimeter separating tokens in names
    DELIMITER = '_'

    # Node type token
    JOINT = 'jnt'
    CONTROL = 'ctrl'
    GROUP = 'grp'
    IK_HANDLE = 'ikh'
    GEO = 'geo'
    NULL = 'null'

    SIDES = dict(
        left = LEFT,
        right = RIGHT,
        center = CENTER
    )
    REGIONS = dict(
        top = TOP,
        bottom = BOTTOM,
        outside = OUTSIDE,
        inside = INSIDE
    )

    NODETYPES = dict(
        joint = JOINT,
        control = CONTROL,
        group = GROUP,
        null = NULL,
        ikHandle = IK_HANDLE,
        mesh = GEO,
        geo = GEO
    )

    # Define the order of concatenation for names
    TokenOrder = OrderedDict([
        ('node_type', NODETYPES),
        ('role', {}), 
        ('descriptor', {}),
        ('region', REGIONS),
        ('side', SIDES)
    ])

    