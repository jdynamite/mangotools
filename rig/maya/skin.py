import os
import re
import pickle
from functools import partial

from rig.maya import getMayaWin

try:
    # TODO: convert calls to api 2.0
    import maya.OpenMaya as om
    import maya.OpenMayaAnim as omanim
    import maya.cmds as cmds
    
    from PySide2 import QtGui, QtCore, QtWidgets
except ImportError:
    raise



def show():
    dialog = SkinWeightsDialog(parent=getMayaWin())
    dialog.show()

class SkinWeightsDialog(QtWidgets.QDialog):
    """
    Dialog to import/export skin weights, and remap influences
    if necessary. Run SkinWeightsDialog.show() to start
    """

    def __init__(self, parent=None):
        super(SkinWeightsDialog, self).__init__(parent)
        self.setWindowTitle("Skin import/export")
        self.setObjectName("skinUI")
        self.setModal(False)
        self.setFixedSize(200, 80)

        vbox = QtWidgets.QVBoxLayout(self)

        btn = QtWidgets.QPushButton("Import")
        btn.released.connect(SkinCluster.createAndImport)
        vbox.addWidget(btn)

        btn = QtWidgets.QPushButton("Export")
        btn.released.connect(SkinCluster.export)
        vbox.addWidget(btn)


class WeightsRemapDialog(QtWidgets.QDialog):
    """
    Dialog to remap weights to different influences
    """

    def __init__(self, parent=None):
        super(WeightsRemapDialog, self).__init__(parent)
        self.setWindowTitle("Remap weights")
        self.setObjectName("remapWeightsUI")
        self.setModal(True)
        self.resize(600, 400)
        self.mapping = {}

        mainVBox = QtWidgets.QVBoxLayout(self)

        label = QtWidgets.QLabel("The following influences have no match with import file")
        label.setWordWrap(True)

        mainVBox.addWidget(label)

        hbox = QtWidgets.QHBoxLayout()
        mainVBox.addLayout(hbox)

        vbox = QtWidgets.QVBoxLayout()
        hbox.addLayout(vbox)
        vbox.addWidget(QtWidgets.QLabel("Unmapped influences"))
        self.existingInfluences = QtWidgets.QListWidget()
        vbox.addWidget(self.existingInfluences)

        vbox = QtWidgets.QVBoxLayout()
        hbox.addLayout(vbox)
        vbox.addWidget(QtWidgets.QLabel("Available imported influences"))
        widget = QtWidgets.QScrollArea()
        self.importedInfluenceLayout = QtWidgets.QVBoxLayout(widget)
        vbox.addWidget(widget)

        hbox = QtWidgets.QHBoxLayout()
        mainVBox.addLayout(hbox)
        hbox.addStretch()
        btn = QtWidgets.QPushButton("Ok")
        btn.released.connect(self.accept)
        hbox.addWidget(btn)

    def setInfl(self, importedInfluences, existingInfluences):
        infs = list(existingInfluences)
        infs.sort()
        self.existingInfluences.addItems(infs)
        width = 200

        for infl in importedInfluences:
            row = QtWidgets.QHBoxLayout()
            self.importedInfluenceLayout.addLayout(row)

            label = QtWidgets.QLabel(infl)

            row.addWidget(label)

            toggle_btn = QtWidgets.QPushButton(">")
            toggle_btn.setMaximumWidth(30)
            row.addWidget(toggle_btn)

            label = QtWidgets.QLabel('')
            label.setMaximumWidth(width)
            label.setSizePolicy(QtWidgets.QSizePolicy.Fixed,
                                QtWidgets.QSizePolicy.Fixed)
            row.addWidget(label)

            toggle_btn.released.connect(
                partial(self.setInfluence_mapping, src=infl, label=label))

        self.importedInfluenceLayout.addStretch()

    def setInfluence_mapping(self, src, label):
        selected_infl = self.existingInfluences.selectedItems()

        if not selected_infl:
            return

        dst = selected_infl[0].text()
        label.setText(dst)
        self.mapping[src] = dst

        # Remove from the list
        index = self.existingInfluences.indexFromItem(selected_infl[0])
        item = self.existingInfluences.takeItem(index.row())

        del item


class SkinCluster(object):
    """
    Skin cluster class to manage skinCluster weights
    """

    FILE_EXT = ".weights"
    WGT_DIR = "data"
    MESH_SUFFIX = ["_REN", "_GEO", "_MESH", "_ren", "_geo", "_mesh"]

    def __init__(self, mesh=None, weights_path=None):
        self.skinCluster = None
        self.meshShape = None
        self.mesh = mesh
        self.weights_path = weights_path
        self.mobject = om.MObject()

        if self.weights_path is None:
            self.weights_path = SkinCluster.getDefaultPath()

        if self.mesh is None:
            try:
                self.mesh = cmds.ls(sl=True)[0]
            except:
                raise RuntimeError("No mesh found.")

        elif not cmds.objExists(self.mesh):
            raise RuntimeError("{} doesn't seem to exist.".format(self.mesh))

        self.meshShape = SkinCluster.getShape(self.mesh)

        if self.meshShape is None:
            raise RuntimeError("Could not find a shape attached to {}".format(self.mesh))

        self.skinCluster = SkinCluster.getSkin(self.meshShape)

        if self.skinCluster is None:
            raise ValueError("No skin attached to {}.".format(self.mesh))

        # Get skinCluster MObject and attach to MFnSkinCluster
        # store into data member dictionary

        msel = om.MSelectionList()
        msel.add(self.skinCluster)
        msel.getDependNode(0, self.mobject)

        self.fn = omanim.MFnSkinCluster(self.mobject)
        self.data = {'weights': {}, 'blendWeights': [],
                     'name': self.skinCluster}
        self.getData()

    @classmethod
    def pretty_name(cls, mesh, skin):
        """
        Rename a skinCluster node based on the mesh it's driving
        :param str mesh:
        :param str skin:
        """

        for suffix in cls.MESH_SUFFIX:
            if mesh.endswith(suffix):
                cmds.rename(skin, mesh.replace(suffix, "_sc"))
                return

        cmds.rename(skin, mesh + "_sc")

    @classmethod
    def get_joints(cls, skinCluster):
        """
        """
        if skinCluster is None:
            return None

        if not cmds.objExists(skinCluster) or not cmds.nodeType(skinCluster) == 'skinCluster':
            raise RuntimeError("%s is not a skinCluster" % skinCluster)

        influences = cmds.skinCluster(skinCluster, query=True, weightedInfluence=True)
        joints = list()

        for i in influences:
            if cmds.nodeType(i) == "joint":
                joints.append(i)

        return joints

    @classmethod
    def export(cls, mesh=None, path=None):
        """
        """
        skin = SkinCluster(mesh, path)
        skin.exportWeights(path)

    @classmethod
    def createAndImport(cls, mesh=None, path=None):
        """
        Create a skinCluster and import data from path
        :param str mesh: mesh name to create a skin cluster for
        :param str path: 
        """
        skinCluster = None

        if mesh is None:
            try:
                mesh = cmds.ls(sl=True)[0]
            except:
                raise RuntimeError("No mesh selected or passed in.")

        if path is None:
            path = os.path.join(cls.getDefaultPath(), mesh + cls.FILE_EXT)

        elif not path.endswith(cls.FILE_EXT):
            path += cls.FILE_EXT

        with open(path, 'rb') as weights_file:
            data = pickle.load(weights_file)

        importedVtx = len(data['blendWeights'])
        meshCount = cmds.polyEvaluate(mesh, vertex=True)

        if meshCount != importedVtx:
            raise RuntimeError("Imported vtx count did not match that of {}.".format(mesh))

        if SkinCluster.getSkin(mesh):
            skinCluster = SkinCluster(mesh)
            data = cls.remapJoints(data)

        else:
            data = cls.remapJoints(data)
            joints = data['weights'].keys()
            cmds.skinCluster(joints, mesh, tsb=True, nw=2, n=data['name'])
            skinCluster = SkinCluster(mesh)

        skinCluster.setData(data)
        print("Imported weights successfully from {}.".format(path))

    @classmethod
    def getDefaultPath(cls):
        """
        Get expected path for weights file
        :returns str: path to directory, based on scene location
        """
        # Maya seems to return forward slashes no matter the OS
        path = re.split(r'/|\\', os.path.dirname(cmds.file(query=True, sceneName=True)))
        
        # Add a separator to windows drives (c: -> c:\)
        # otherwise ignored by os.path.join
        if path[0].endswith(':'):
            path[0] = path[0] + os.sep

        # Add weights directory
        path.extend([cls.WGT_DIR])

        return os.path.join(*path)

    @classmethod
    def getSkin(cls, meshShape):
        """
        Get skinCluster node as string, from mesh
        :param str meshShape: node or shape of mesh
        :returns: name of skinCluster, if found,
            otherwise returns None
        """

        meshShape = cls.getShape(meshShape)
        skins = cmds.ls(type="skinCluster")
        for skin in skins:
            try:
                if meshShape in cmds.skinCluster(skin, query=True, g=True):
                    return skin
            except:
                return None
        return None

    @classmethod
    def removeNamespaceFrom(cls, string):
        if ':' in string and '|' in string:
            tokens = string.split('|')
            result = [s.split(':')[-1] for s in tokens]

            return '|'.join(result)

        elif ':' in string:
            return string.split(':')[-1]

        else:
            return string

    @classmethod
    def getShape(cls, mesh, intermediate=False):
        mesh_type = cmds.nodeType(mesh)

        if mesh_type == 'transform':
            shapes = cmds.listRelatives(mesh, shapes=True, path=True) or []

            for shape in shapes:
                is_interm = cmds.getAttr("{}.intermediateObject".format(shape))

                if intermediate and is_interm and cmds.listConnections(shape, source=False):
                    return shape

                elif not intermediate and not is_interm:
                    return shape

            if len(shapes):
                return shapes[0]

        elif mesh_type in ['nurbsCurve', 'mesh', 'nurbsSurface']:
            return mesh

        return None

    @classmethod
    def remapJoints(cls, data):
        joints = data['weights'].keys()

        unused_imports = []
        no_match = set([cls.removeNamespaceFrom(x)
                        for x in cmds.ls(type='joint')])

        for j in joints:
            if j in no_match:
                no_match.remove(j)
            else:
                unused_imports.append(j)

        if unused_imports and no_match:
            dialog = WeightsRemapDialog(getMayaWin())
            dialog.setInfl(unused_imports, no_match)
            dialog.exec_()

            for src, dst in dialog.mapping.items():
                data['weights'][dst] = data['weights'][src]
                del data['weights'][src]

        return data

    def importWeights(self, path=None):
        self.getData()

        if path is None:
            path = os.path.join(self.weights_path, self.mesh + self.FILE_EXT)

        elif not path.endswith(SkinCluster.FILE_EXT):
            path += SkinCluster.FILE_EXT

        with open(path, 'rb') as weightsFile:
            data = pickle.load(weightsFile)

        importedVtx = len(data['blendWeights'])
        meshCount = cmds.polyEvaluate(self.meshShape, vertex=True)

        if meshCount != importedVtx:
            raise RuntimeError("Imported vtx count did not match that of {}.".format(self.mesh))

        self.data = SkinCluster.remapJoints(data)
        self.setData(self.data)

    def exportWeights(self, path=None):
        if path is None:
            path = os.path.join(self.weights_path, self.mesh + self.FILE_EXT)

        if not path.endswith(SkinCluster.FILE_EXT):
            path += SkinCluster.FILE_EXT

        self.getData()

        directory = os.path.dirname(path)
        if not os.path.isdir(directory):
            print("Making directory at: {}".format(directory))
            os.makedirs(directory)

        with open(path, 'wb') as weightsFile:
            pickle.dump(self.data, weightsFile, pickle.HIGHEST_PROTOCOL)

        print("Exported skin weights to {} successfully.".format(path))

    def setData(self, data):
        self.data = data

        dagPath, components = self.getComponents()
        self.setWeights(dagPath, components)
        self.setBlendWeights(dagPath, components)

        for attr in ['skinningMethod', 'normalizeWeights']:
            cmds.setAttr("{}.{}".format(
                self.skinCluster, attr), self.data[attr])

    def getData(self):
        dagPath, components = self.getComponents()
        self.getInfluenceWeights(dagPath, components)
        self.getBlendWeights(dagPath, components)

        for attr in ['skinningMethod', 'normalizeWeights']:
            self.data[attr] = cmds.getAttr(
                "{}.{}".format(self.skinCluster, attr))

        self.data['name'] = self.skinCluster


    def getComponents(self):
        """
        Looks up deformer set of skin cluster to find which components
        are being affected by self.skinCluster
        """

        fn_set = om.MFnSet(self.fn.deformerSet())
        members = om.MSelectionList()
        fn_set.getMembers(members, False)

        dagPath = om.MDagPath()
        components = om.MObject()

        members.getDagPath(0, dagPath, components)

        return dagPath, components

    def _getCurrentWeights(self, dagPath, components):
        weights = om.MDoubleArray()
        util = om.MScriptUtil()
        util.createFromInt(0)
        uint_ptr = util.asUintPtr()
        self.fn.getWeights(dagPath, components, weights, uint_ptr)
        return weights

    def setWeights(self, dagPath, components):
        weights = self._getCurrentWeights(dagPath, components)

        inflPaths = om.MDagPathArray()
        nInfl = self.fn.influenceObjects(inflPaths)

        inflPerVtx = weights.length() / nInfl

        for imported_infl, imported_weights in self.data['weights'].items():
            for ii in range(inflPaths.length()):
                infl = inflPaths[ii].partialPathName()
                infl = SkinCluster.removeNamespaceFrom(infl)

                if infl == imported_infl:
                    for jj in range(inflPerVtx):
                        weights.set(imported_weights[jj], jj * nInfl + ii)

                    break

        inflIndices = om.MIntArray(nInfl)

        for ii in range(nInfl):
            inflIndices.set(ii, ii)

        self.fn.setWeights(dagPath, components, inflIndices, weights, False)

    def setBlendWeights(self, dagPath, components):
        blendWeights = om.MDoubleArray(len(self.data['blendWeights']))
        for i, w in enumerate(self.data['blendWeights']):
            blendWeights.set(w, i)
        self.fn.setBlendWeights(dagPath, components, blendWeights)

    def getInfluenceWeights(self, dagPath, components):
        weights = self._getCurrentWeights(dagPath, components)
        inflPaths = om.MDagPathArray()

        nInfl = self.fn.influenceObjects(inflPaths)
        inflPerVtx = weights.length() / nInfl

        for idx in range(inflPaths.length()):
            infl = inflPaths[idx].partialPathName()
            infl = SkinCluster.removeNamespaceFrom(infl)
            self.data['weights'][infl] = [weights[jj * nInfl + idx] for jj in range(inflPerVtx)]

    def getBlendWeights(self, dagPath, components):
        weights = om.MDoubleArray()
        self.fn.getBlendWeights(dagPath, components, weights)
        self.data['blendWeights'] = [weights[i] for i in range(weights.length())]