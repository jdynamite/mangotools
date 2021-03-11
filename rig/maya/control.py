try:
    from maya import cmds, mel
except ImportError:
    print("Must be in a maya environment!")
    raise

# native
import os
import json
import pickle
from six import string_types

from rig.config import naming
from rig.utils import dataIO
from rig.maya import get_logger
from rig.maya.base import MayaBaseNode
from rig.maya.curve import create_from_points

log = get_logger(__name__)

class Control(MayaBaseNode):
    """
    Convenience class for common control operations,
    like assigning control shapes, colors, etc

    :param str name:
    :param tuple|list position:
    :param str align_to:
    :param str parent:
    """
    NODETYPE = MayaBaseNode.CONFIG.CONTROL
    COL_TO_INT = dict(red=13, yellow=17, blue=6, green=7)
    INT_TO_COL = {v: k for k, v in COL_TO_INT.items()} 
    EXT = '.shapes'

    def __init__(self, 
                 name,
                 role=None, 
                 descriptor=None, 
                 region=None, 
                 side=None):
  
        super(Control, self).__init__(name,
                                      node_type=self.NODETYPE, 
                                      role=role, 
                                      descriptor=descriptor, 
                                      region=region, 
                                      side=side)
        
        # Try to populate naming properties
        if not any([role, descriptor, region, side]):
            self.decompose_name()

        # Tag object as controller
        if not cmds.controller(query=True, isController=True):
            cmds.controller(name)

    @classmethod
    def create(cls,
               name=None,
               descriptor=None,
               role=None,
               region=None,
               side=None,
               position=(0,0,0),
               space='world',
               snap_to=None,
               color='yellow',
               shape='circle'):
        """
        Create a new controller in maya and instance as class
        """
        if not name:
            name = cls.compose_name(node_type=cls.NODETYPE, descriptor=descriptor, role=role, region=region, side=side)
        
        name = cmds.createNode("transform", name=name)
        
        control = cls(name, descriptor=descriptor, role=role, region=region, side=side)
        
        if snap_to:
            control.snap_to(snap_to)
        else:
            control.set_position(position, space=space)
        
        control.set_shape(shape)
        control.color = color

        return control

    @classmethod
    def list_shapes(cls):
        """
        List available shapes in control library
        """
        shapes = dataIO.load(cls.CONFIG.CONTROL_SHAPES_FILE)
        for shape in shapes:
            print(shape)

    @classmethod
    def get_default_path(cls, filename=None):
        """
        Get default directory where control shapes for this scene can be saved
        :param str filename: name for file, not including directory
        :return str path: path to file
        """
        scene_path = cmds.file(query=True, sceneName=True)
        scene_dir, scene_name = os.path.dirname(scene_path)
        
        if filename and isinstance(filename, string_types):
            if not filename.endswith(cls.EXT):
                filename += cls.EXT
            return os.path.join(scene_dir, filename)
        else:            
            return os.path.join(scene_dir, scene_name.split('.')[0] + cls.EXT)

    @classmethod
    def set_shapes(cls, objects, shape):
        if type(objects) not in [list, tuple]:
            return
        objects = [o for o in objects if isinstance(o, cls)]
        map(lambda o: o.set_shape(shape), objects)

    @classmethod
    def mirror_shape(cls):
        """
        Mirror control shapes based on selection
        """
        sel = cmds.ls(selection=True) or []

        if len(sel) != 2:
            err = "Please select two curves. Driver -> Driven"
            raise RuntimeError(err)

        driver = sel[0]
        driven = sel[1]

        driver_shapes = cmds.listRelatives(driver, shapes=True, noIntermediate=True) or []
        driven_shapes = cmds.listRelatives(driven, shapes=True, noIntermediate=True) or []

        if not len(driver_shapes) or not len(driven_shapes):
            err = "Couldn't find any shapes attached to one or both objects."
            raise RuntimeError(err)
        
        # Format template for accessing cv's
        cv = "{0}.cv[{1}]"

        for driver_shape, driven_shape in zip(driver_shapes, driven_shapes):
            cvs = cmds.getAttr("{0}.cp".format(driver_shape), s=1)
            cvs_driven = cmds.getAttr("{0}.cp".format(driven_shape), s=1)

            if cvs != cvs_driven:
                raise RuntimeError()

            for i in range(cvs):
                driver_cv = cv.format(driver_shape, str(i))
                driven_cv = cv.format(driven_shape, str(i))

                driver_pos = cmds.xform(driver_cv, query=True, worldSpace=True, translation=True)
                driven_pos = [driver_pos[0] * -1, driver_pos[1], driver_pos[2]]
                cmds.xform(driven_cv, worldSpace=True, translation=driven_pos)

    @classmethod
    def get_controls(cls):
        """
        Get all controls in scene as class instances
        """
        return [cls(c) for c in cmds.controllers(allControllers=True)]

    @classmethod
    def save_shapes(cls):
        """
        Save scene control shapes onto file relative to current scene
        """
        shapes_data = {}

        for ctrl in cls.get_controls():
            if ctrl not in shapes_data:
                    shapes_data[ctrl] = {}
        
            for shape in ctrl.shapes:
                if shape not in shapes_data[ctrl]:
                    shapes_data[ctrl][shape] = {}

                curve_info = cmds.createNode("curveInfo")
                input_plug = "{0}.inputCurve".format(curve_info)
                shape_plug = "{0}.worldSpace[0]".format(shape)
                cmds.connectAttr(shape_plug, input_plug)

                knots = "{0}.knots".format(curve_info)
                deg = "{0}.degree".format(shape)
                cvs = "{0}.cv[*]".format(shape)

                degree = cmds.getAttr(deg)
                period = cmds.getAttr("{0}.f".format(shape))
                positions = cmds.getAttr(cvs)

                # check empty positions
                for pos in positions:
                    if all(p == 0 for p in pos):
                        cmds.select(shape)
                        mel.eval('doBakeNonDefHistory( 1, {"prePost"});')
                        cmds.select(clear=True)
                        positions = cmds.getAttr(cvs)
                        degree = cmds.getAttr(deg)
                        period = cmds.getAttr("{0}.f".format(shape))
                        break

                knots = cmds.getAttr(knots)[0]

                if period > 0:
                    for i in range(degree):
                        positions.append(positions[i])

                knots = knots[:len(positions) + degree - 1]
                shapes_data[ctrl][shape]['knots'] = knots
                shapes_data[ctrl][shape]['period'] = period
                shapes_data[ctrl][shape]['positions'] = positions
                shapes_data[ctrl][shape]['degree'] = degree

                cplug = "{0}.overrideEnabled"
                shapes_data[ctrl][shape]['color'] = 'yellow'
                for obj in [ctrl, shape]:
                    if cmds.getAttr(cplug.format(obj)):
                        color = "{0}.overrideColor".format(obj)
                        shapes_data[ctrl][shape]['color'] = cmds.getAttr(color)

                cmds.delete(curve_info)
        
        with open(cls.get_default_path(), 'rb') as control_file:
            pickle.dump(shapes_data, control_file, pickle.HIGHEST_PROTOCOL)

    @classmethod
    def load_shapes(cls):
        path = cmds.fileDialog(mode=0, directoryMask="*.shapes")
        success = "Successfuly loaded shape {0} for {1}."
        err = "{0} does not exist, skipping."

        with open(path, 'rb') as ctrl_file:
            shapes_data = pickle.load(ctrl_file)

        for obj in shapes_data:
            if not cmds.objExists(obj):
                log.error(err.format(obj))
                continue

            # parent does exist
            # delete shapes from obj
            cmds.delete(cmds.listRelatives(obj, s=True, type="nurbsCurve"))

            # initialize object as curve
            con = cls.compose(descriptor=obj, side=cls.CONFIG.LEFT)

            for shape in shapes_data[obj]:
                shape = shapes_data[obj][shape]
                pos = shape['positions']
                dg = shape['degree']
                knots = shape['knots']
                color = shape['color']
                period = shape['period']

                p = True if period > 0 else False
                con.color = color
                curve = cmds.curve(degree=dg, point=pos, knot=knots, per=p)
                con.get_shape_from(curve, destroy=True, replace=False)
                log.info(success.format(shape, obj))

    @property
    def color(self):
        numeric = cmds.getAttr('{}.overrideColor'.format(self.long_name))
        return self.INT_TO_COL.get(numeric, numeric)

    @color.setter
    def color(self, val):
        """
        Sets colors for shapes under this control
        :param str|int val: color to set for this object's shapes
        """
        err = "Must pass an int or string for colors"
        assert isinstance(val, string_types) or isinstance(val, int), err
        col = self.COL_TO_INT[val] if isinstance(val, string_types) else val
        cmds.setAttr("{}.overrideEnabled".format(self.long_name), 1)
        cmds.setAttr("{}.overrideColor".format(self.long_name), col)

    @property
    def null(self):
        """
        Get furthest ancestor that is a null to this object
        """
        p = cmds.listRelatives(self.long_name, parent=True)
        
        if p and self.CONFIG.NULL in p[0]:
            p = MayaBaseNode(p[0])
            old_p = p
        else:
            log.debug("Parent {} is not a null".format(p))
            return None

        while p and self.CONFIG.NULL in p.short_name:
            old_p = p
            p = old_p.parent
        
        return old_p

    @property
    def parent(self):
        return self.null
    
    @parent.setter
    def parent(self, new_parent):
        if isinstance(new_parent, MayaBaseNode):
            new_parent = new_parent.long_name

        if not self.null:
            try:
                cmds.parent(self.long_name, new_parent)
                log.debug("Parented {} under {}".format(self.nice_name, new_parent))
                self._parent = new_parent
            except RuntimeError:
                msg = "Failed to parent {} under {}".format(self.short_name, new_parent)
                log.warning(msg, exc_info=True)
        
        elif new_parent != self.null.parent:
            log.debug("Parenting null {} to parent: {}".format(self.null.nice_name, new_parent))
            self.null.parent = new_parent

    def set_shape(self, new_shape, replace=True):
        """
        Sets a new shape under this object
        :param str shape: shape to set for this object
        :param bool replace: 
        """

        if new_shape.lower() == 'circle':
            circle = cmds.circle(constructionHistory=False)[0]
            self.get_shape_from(circle, destroy=True, replace=replace)
        else:
            # call from prebuilt control shapes saved out to a file
            controlDict = dataIO.load(self.CONFIG.CONTROL_SHAPES_FILE)
            for child_shape in controlDict[new_shape]["shapes"]:
                positions = controlDict[new_shape]["shapes"][child_shape]["positions"]
                degree = controlDict[new_shape]["shapes"][child_shape]["degree"]
                curve = create_from_points(positions, degree, self.nice_name + "_temp")
                self.get_shape_from(curve, destroy=True, replace=replace)

    def set_position(self, position, space='world'):
        """
        Overloaded method, sets position on parent null/offset group
        if one exists
        """
        if self.null:
            world = space.lower() == 'world'
            position = tuple(position)
            cmds.xform(self.null, worldSpace=world, translation=position)
        else:
            super(Control, self).set_position(position, space)


    def set_rotation(self, rotation, space='world'):
        """
        Overloaded method, sets rotation on parent null/offset group
        if one exists
        """
        if self.null:
            world = space.lower() == 'world'
            cmds.xform(self.null, worldSpace=world, rotation=rotation)
        else:
            super(Control, self).set_rotation(rotation, space)

    def mirror(self):
        """
        Returns the mirrored control, aligned to opposite side
        if an object exists there
        """

        sideLower = self.side.lower()
        otherSide = ""
        align_to = ""

        mirror_map_left = {"left": "right", "lf": "rt", "l": "r"}
        mirror_map_right = {"right": "left", "rt": "lf", "r": "l"}

        if sideLower in mirror_map_left.keys():
            otherSide = list(mirror_map_left[sideLower])

        elif sideLower in mirror_map_right.keys():
            otherSide = list(mirror_map_right[sideLower])

        for i, char in enumerate(self.side):
            if char.isupper():
                otherSide[i] = otherSide[i].upper()

        if not len(otherSide):
            raise RuntimeError("Could not find opposite side.")

        otherSide = "".join(otherSide)

        if cmds.objExists(self.aligned_to):
            align_to = self.align_to.replace(self.side, otherSide)
        else:
            align_to = "world"

        newName = self.name.replace(self.side, otherSide)

        return type(self)(name=newName, position=self.position, align_to=align_to, shape=self.shape)

    def set_to_origin(self):
        """
        Pops control/null to origin
        """

        if cmds.objExists(self.null):
            target = self.null
        else:
            target = self.long_name

        cmds.xform(target, cp=True)
        temp_grp = cmds.group(em=True, n='temp_grp_#')
        cmds.delete(cmds.pointConstraint(temp_grp, target))
        cmds.delete(temp_grp)

    def get_shape_from(self, obj, destroy=True, replace=True):
        """
        Copies the shape(s) from passed object, with the option
        to destroy that object or not, and the option to replace
        all existing shapes
        """
        if not destroy:
            obj = cmds.duplicate(obj, rc=True, name="temp_shape_#")

        if replace:
            if self.shapes:
                log.info("Deleting shapes: {}".format(self.shapes))
                cmds.delete(self.shapes)

        cmds.parent(obj, self.long_name)
        cmds.xform(obj, objectSpace=True, translation=(0, 0, 0), ro=(0, 0, 0), scale=(1, 1, 1))
        obj_shapes = cmds.listRelatives(obj, shapes=True)

        for shape in obj_shapes:
            cmds.parent(shape, self.long_name, relative=True, shape=True)
            cmds.rename(shape, "%sShape#" % self.short_name)

        cmds.delete(obj)

    def offset(self, n=1):
        """
        Creates null or offset groups above this control
        :param int n: number of offsets to create above
        """
        i = 0
        while n > i:
            self.insert_parent()
            i += 1
    
    def insert_parent(self):
        """
        """
        # Record current parent
        orig_par = self.parent # could be None
        
        # Get naming flags
        name_args = self.as_dict()
        name_args.update(dict(node_type=self.CONFIG.NULL))
        null_name = self.compose_name(**name_args)
        
        log.debug("New null name is: {}".format(null_name))
        dup = MayaBaseNode(cmds.duplicate(self.short_name, name=null_name)[0])
        
        if dup.shapes:
            cmds.delete(dup.shapes)
        
        # Parent this control under duplicate
        self.parent = dup
        
        # Parent duplicate under my original parent
        if orig_par:
            dup.parent = orig_par

    def drive_constrained(self, obj, p=False, r=False, s=False, o=False):
        """
        Establish driving relationships between control and another object
        p = position, r = rotation, s = scale, o = maintain offset
        """
        if not cmds.objExists(obj):
            return
        if s:
            cmds.scaleConstraint(self.name, obj, mo=o)

        if p and r:
            cmds.parentConstraint(self.name, obj, mo=o)

        elif p and not r:
            cmds.pointConstraint(self.name, obj, mo=o)

        elif r and not p:
            cmds.orientConstraint(self.name, obj, mo=o)

    def drive_parented(self, obj):
        """
        parent obj to control directly
        """
        if isinstance(obj, string_types):
            if cmds.objExists(obj):
                cmds.parent(obj, self.name)
            else:
                err = "Couldn't find passed obj: {0}"
                raise RuntimeError(err.format(obj))

    def space_switch(self, spaces, aliases=None):
        """
        Add space switches to this control object
        
        :param list spaces: A list of spaces
        """

        # Arg check
        assert isinstance(spaces, list), "Pass spaces as a list"

        err = "One or more passed spaces does not exist."
        assert all(cmds.objExists(o) for o in spaces), err

        spaces = [MayaBaseNode(n) for n in spaces]
        
        parent_con = MayaBaseNode(cmds.parentConstraint(spaces, self.null, maintainOffset=True)[0])

        # Figure out how the attribute of weights looks like
        # add SPACES display attr in control
        if not aliases:
            prefixes = [n.nice_name.split(self.delimiter)[0] for n in spaces]
            enum_names = [n.nice_name.lstrip(prefix) for prefix, n in zip(prefixes, spaces)]
        else:
            enum_names = aliases

        # Attr names refers to the attributes on the parent constraint
        attr_names = [s.nice_name + 'W' + str(i) for i,s in enumerate(spaces)]

        # This dictionary maps space's short names to the parent constraint attributes
        attr_dict = {k.short_name:v for k,v in zip(spaces, attr_names)}

        # Add attributes in this control for spaces
        self.add_attr('SPACE', at='enum', enumName='-' * 10, h=False, k=True)
        self.add_attr('spaces', at='enum', enumName=':'.join(enum_names), h=False, k=True)

        # Lock displayable space enum
        cmds.setAttr(self.plug('SPACE'), lock=True)

        spaces_set = set(spaces)
        
        # Connect spaces through set driven keys
        for enum_name, space in zip(enum_names, spaces):
            cmds.setAttr(self.plug('spaces'), enum_names.index(enum_name))
            
            for other_space in spaces_set.difference([space]):
                parent_con.set_attr(attr_dict[other_space.short_name], 0)
                attr = attr_dict[other_space.short_name]
                cmds.setDrivenKeyframe(parent_con.plug(attr), cd=self.plug('spaces'))

            attr = attr_dict[space.short_name]
            parent_con.set_attr(attr_dict[space.short_name], 1)
            cmds.setDrivenKeyframe(parent_con.plug(attr), cd=self.plug('spaces'))