try:
    from maya.utils import MayaGuiLogHandler
    import maya.OpenMayaUI as omui
    from PySide2 import QtWidgets
    from shiboken2 import wrapInstance
    MAYA_AVAILABLE = True
except ImportError:
    MAYA_AVAILABLE = False

import logging

def getMayaWin():
    """
    Get Maya main window as Qt object
    """
    if not MAYA_AVAILABLE:
        raise RuntimeError("Not in a maya environment!")
    ptr = omui.MQtUtil.mainWindow()
    return wrapInstance(int(ptr), QtWidgets.QMainWindow)

def get_logger(name, level=logging.INFO):
    """
    Get a logger with a maya handler
    :param int level: a level for this logger
    """
    if MAYA_AVAILABLE:
        return MayaLogger(name, level)
    else:
        return logging.getLogger()


class MayaLogger(logging.Logger):
    """
    Logger subclass that uses a maya handler by default
    :param int level: 
        a level to use for this logger,
        defaults to logging.INFO (10)
    """

    MSG_FORMAT  = "%(asctime)s %(name)s: %(message)s"
    DATE_FORMAT = "%H:%M:%S"
    
    def __init__(self, name, level=logging.INFO):
        super(MayaLogger, self).__init__(name, level=level)
        handler = MayaGuiLogHandler()
        handler.setLevel(level)
        formatter = logging.Formatter(self.MSG_FORMAT, self.DATE_FORMAT)
        handler.setFormatter(formatter)
        self.addHandler(handler)

