try:
    from maya import cmds
except ImportError:
    print("Must be in a maya environment!")
    raise

from rig.components.baseRig import BaseRig

class RootRig(BaseRig):

    def __init__(self, joints):
        if not joints:
            joints = [self.create_root_joint()]
        super(RootRig, self).__init__(joints)
        self.root = joints[0]
    
    def create_root_joint(self):
        """
        :return str root: created joint
        """
        # Get a name for the root joint, and create one
        # at the origin
        root_name = self.naming.compose_name(node_type='joint', role='def', description='root')
        root_jnt = cmds.joint(root_name, p=(0, 0, 0))
        
        # Don't draw root joint
        cmds.setAttr(root_jnt, 'drawStyle', 2)

        return root_jnt
        
