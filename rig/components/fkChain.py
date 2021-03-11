"""
Given a chain of joints, create a simple control for each
"""
try:
    from maya import cmds
except (ImportError, ModuleNotFoundError):
    print("Must be in a maya environment!")
    raise

from rig.components.baseRig import BaseRig
from rig.maya.base import MayaBaseNode
from rig.maya.control import Control


class FkChain(BaseRig):

    def __init__(self, joints, shape='sphere', **kwargs):
        super(FkChain, self).__init__(joints, **kwargs)
        self.shape = shape
    
    def install(self):
        """
        Given some joints, drive them with controls replicating
        their same chain structure - and skip over any roll joints
        """
        ancestor = None
        controls = list()

        for jnt in self.joints:
            jnt = MayaBaseNode(jnt)
            side = jnt.side
            desc = self.descriptor or jnt.descriptor
            ctrl = Control.create(descriptor=desc, role='fk', side=side, snap_to=jnt.long_name, shape=self.shape)
            
            if not self.color:
                print(side)
                if side == 'l':
                    ctrl.color = 'blue'
                elif side == 'r':
                    ctrl.color = 'red'
            else:
                ctrl.color = self.color

            # Offset once
            ctrl.offset(n=1)
            
            # Parent null under ancestor
            if ancestor:
                ctrl.parent = ancestor
            
            ancestor = ctrl
            controls.append(ctrl)

        self.controls = controls

    def connect(self):
        constraints = list()
        for con, jnt in zip(self.controls, self.joints):
            constraint = cmds.parentConstraint(con.long_name, jnt, maintainOffset=False)
            constraints.append(constraint)
        self.constraints = constraints