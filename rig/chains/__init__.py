"""
Define base class for chains, on top of which rigs can be
installed for functionality

Chains themselves have rigs to be placed more easily.

At install time, these temp rigs are removed
"""
try:
    from maya import cmds
except ImportError:
    print("Must be in a maya environment!")
    raise

from rig.config import Config
from rig.config.naming import Naming


class Chain(object):

    def __init__(self, name, root_joint=None):
        self.config = Config
        self.naming = Naming
        self.joints = list()
        
        if not root_joint:
            jnt_name = Naming(name)
            jnt_name.node_type = 'joint'
            root_joint = self.create_joint(name)
    
    def create_joint(self, name, position=(0, 0, 0)):
        """
        Create a joint at specified location
        """
        # Clear selection
        cmds.sl(clear=True)
        
        # Create joint
        new_joint = cmds.joint(name, p=position)
        self.joints.append(new_joint)
        return new_joint
    
    def rig_chain(self, solver='rp'):
        """
        """
        pass
