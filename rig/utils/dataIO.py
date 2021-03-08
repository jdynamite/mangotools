import json
import pickle
import sys
import os

JSON_INDENT = 4

def dump(data):
    """
    Tries to convert a python object into a dictionary
    """
    try:
        result = json.dumps(data, sort_keys=True, indent=JSON_INDENT)
    except BaseException:
        raise RuntimeError("Unable to serialize passed in object")
    
    return result

def save(data, filepath):
    """
    Saves passed in data dictionary onto a file path
    :param dict data:
    :param str filepath:

    .. note::
        Will create missing directories
    """
    if not data:
        return
    
    directory = os.path.dirname(filepath)

    if not os.path.isdir(directory):
        os.makedirs(directory)
    
    with open(filepath, 'w') as f:
        f.write(dump(data))

def load(filepath):
    """
    Loads json from filepath
    :param str filepath:
    :returns dict data:
    """
    err = "File doesn't exist: {}"
    assert os.path.isfile(filepath), err.format(filepath)
    data = dict()
    
    with open(filepath, 'r') as f:
        data = json.loads(f.read())
    
    return data