"""
Definition for base node class
"""

try:
    from maya import cmds
    from maya.api import OpenMaya as om
except ImportError:
    print("Must be in a maya environment!")
    raise

from rig.config.naming import Naming
from rig.maya import dag, linAlg, get_logger


log = get_logger(__name__)

class MayaBaseNode(Naming):
    """
    Base class to handle dag nodes in maya

    :param str|Naming name: Name of node to instance a class for
    :keyword str node_type:
    :keyword str descriptor:
    :keyword str role:
    :keyword str region:
    :keyword str side:
    """

    def __init__(self,                
                 name, 
                 node_type=None, 
                 role=None, 
                 descriptor=None, 
                 region=None, 
                 side=None):
        
        if isinstance(name, type(self)):
            name = name.short_name

        assert cmds.objExists(name), "{} doesn't exist".format(name)
        
        # instance naming related class properties
        super(MayaBaseNode, self).__init__(name, 
                                           node_type=node_type,
                                           role=role,
                                           descriptor=descriptor,
                                           region=region,
                                           side=side)

        self._list = dag.get_list(name)
        self._mobject = dag.get_mobjects(name, self._list)[0]
        self._dag = dag.get_dag_paths(name, self._list)[0]
        self._transform_set = dag.get_function_sets(name, fn=om.MFnTransform)[0]
    
    @classmethod
    def from_selection(cls):
        """
        Instantiate object from selection
        """
        sel = cmds.ls(sl=True)
        if sel:
            sel = sel[0]
            return cls(sel)
        else:
            raise RuntimeError("Nothing is selected.")

    def set_position(self, position, space='world'):
        """
        Sets this object's position in desired space (local or world),
        calls cmds.xform
        :param tuple position:
        :param str space:
        """
        world = space.lower() == 'world'
        position = tuple(position)
        cmds.xform(self.long_name, worldSpace=world, translation=position)

    def set_rotation(self, rotation, space='world'):
        """
        Set this object's rotation in desired space (local or world),
        calls cmds.xform
        :param tuple rotation:
        :param str space:
        """
        world = space.lower() == 'world'
        cmds.xform(self.long_name, worldSpace=world, ro=rotation)

    def snap_to(self, node, rotate=True, translate=True):
        """
        Align this object with another
        :param str|MayaBaseObject node: the object to snap to
        :param bool rotate: Whether to do align orientation
        :param bool translate: Whether to align position
        """
        if isinstance(node, type(self)):
            node = node.long_name
        
        assert cmds.objExists(node), "{} doesn't exist".format(node)
        
        linAlg.snap(self.long_name, node, rotate=rotate, translate=translate)

    def plug(self, attr):
        """
        Get an attribute plug from this object
        :param str attr: attribute name
        """
        # Clear any trailing colons just in case
        attr = attr.lstrip('.')

        # Join long name and attribute with a dot
        return '.'.join([self.long_name, attr])
    
    def add_attr(self, attr, **kwargs):
        """
        Add attribute to this node
        """
        if cmds.objExists(self.plug(attr)):
            raise RuntimeError("Attribute {} already exists".format(attr))
        
        cmds.addAttr(self.long_name, longName=attr, **kwargs)
    
    def set_attr(self, attr, value, **kwargs):
        """
        Set value to attr for this node
        """
        cmds.setAttr(self.plug(attr), value, **kwargs)

    @classmethod
    def from_sel(cls):
        """
        Return class instances based on selection
        """
        sel = cmds.ls(selection=True, long=True)
        if not sel:
            return
        else:
            return [cls(o) for o in sel]

    @property
    def name(self):
        return self.short_name

    @name.setter
    def name(self, new_name):
        if new_name == self._name:
            log.warning("New name: {} is the same as the old name: {}".format(new_name, self._name))
            return
        else:
            new_name = self.short_name.replace(self.nice_name, new_name)
            self._name = new_name
            log.debug("New name: {}".format(new_name))
            cmds.rename(self.long_name, new_name)

    @property
    def position(self):
        """
        Get position of object, returns in world space
        """
        return self._transform_set.translation(om.MSpace.kWorld)

    @property
    def parent(self):
        """
        Get parent object of this node, as a class instance
        """
        par = cmds.listRelatives(self.long_name, parent=True)
        if par:
            return type(self)(par[0])
        else:
            return None
    
    @parent.setter
    def parent(self, par):
        if isinstance(par, MayaBaseNode):
            par = par.long_name
        
        try:
            cmds.parent(self.long_name, par)
            log.debug("Parented {} under {}".format(self.nice_name, par))
            self._parent = par
        except RuntimeError:
            msg = "Failed to parent {} under {}".format(self.short_name, par)
            log.warning(msg, exc_info=True)
    
    @property
    def world_matrix(self):
        """
        :returns MMatrix matrix: world matrix
        """
        return dag.get_matrix(self.long_name, 'world')[0]
    
    @property
    def object_matrix(self):
        """
        :returns MMatrix matrix: object matrix
        """
        return dag.get_matrix(self.long_name, 'object')[0]

    @property
    def namespace(self):
        """
        :returns str namespace: 
        """
        short_name = self.short_name
        if ':' in short_name:
            return short_name.rsplit(':', 1)
        else:
            return ''
    
    @namespace.setter
    def namespace(self, ns):
        if ns == self.namespace:
            return
        else:
            cmds.rename(self.short_name, self.short_name.replace(self.namespace, ns))
    
    @property
    def nice_name(self):
        """
        :returns str niceName: short path name without namespace
        """
        short_name = self.short_name
        if ':' in short_name:
            return short_name.split(':')[-1]
        else:
            return short_name
    
    @property
    def long_name(self):
        """
        :returns str long_name: full path name
        """
        return self._dag.fullPathName()
    
    @property
    def short_name(self):
        """
        :returns str short_name: partial path (last token of full path)
        """
        return self._dag.partialPathName()

    @property
    def shapes(self):
        """
        :returns list shapes: shapes under this object
        """
        return cmds.listRelatives(self.long_name, 
                                  children=True, 
                                  shapes=True, 
                                  noIntermediate=True) or []
    
    @property
    def shape(self):
        """
        :returns shape: returns immediate shape if one exists, else None
        """
        shapes = self.shapes
        
        if shapes:
            return shapes[0]
        else:
            return None