from rig.config import Config
from rig.config.naming import Naming
from six import string_types

try:
    from maya import cmds
    from rig.maya import dag
except ImportError:
    print("Must be in a maya environment!")
    raise


class BaseRig(object):
    """
    Base rig component, implements abstract methods
    """
    CONFIG = Config
    NAMING = Naming
    
    def __init__(self, joints, descriptor=None, color=None):
        if isinstance(joints, string_types):
            print("This is a str type")
            self.joints = cmds.listRelatives(joints, allDescendents=True)
        else:
            self.joints = joints
        self.naming = BaseRig.NAMING
        self.descriptor = descriptor
        self.color = color
    
    def install(self):
        """
        Install rig
        """
        raise NotImplementedError()

    def connect(self):
        """
        Drive deformer joints
        """
        raise NotImplementedError()
    
    def uninstall(self):
        """
        Disconnect and clear
        """
        raise NotImplementedError()