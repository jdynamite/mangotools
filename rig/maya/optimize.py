try:
    from maya import cmds
except (ImportError, ModuleNotFoundError):
    print("Must be in a maya environment!")
    raise

from rig.maya import get_logger
log = get_logger(__name__)


def get_unknown_nodes():
    """
    Get all unknown nodes
    """
    return cmds.ls(type='unknown', referencedNodes=False)

def delete_unknown_nodes():
    """
    Delete unknown nodes in scene
    """

    unable = list()
    able = list()

    for node in get_unknown_nodes():
        try:
            cmds.lockNode(node, lock=False)
            cmds.delete(node)
            able.append(node)
        except RuntimeError:
            unable.append(node)
        except ValueError:
            continue
    
    if unable:
        log.warn("Failed to delete these nodes: {}".format(unable))
    
    if able:
        log.info("Deleted {} nodes.".format(len(able)))