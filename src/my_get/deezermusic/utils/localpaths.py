from pathlib import Path
import sys
import os
import re
from ..utils import canWrite


homedata = Path.home()
userdata = ""
musicdata = ""

def checkPath(path):
    if path == "": return ""
    if not path.is_dir(): return ""
    if not canWrite(path): return ""
    return path

def getConfigFolder():
    global userdata
    if userdata != "": return userdata
    if os.getenv("XDG_CONFIG_HOME") and userdata == "":
        userdata = Path(os.getenv("XDG_CONFIG_HOME"))
        userdata = checkPath(userdata)
    if os.getenv("APPDATA") and userdata == "":
        userdata = Path(os.getenv("APPDATA"))
        userdata = checkPath(userdata)
    if sys.platform.startswith('darwin') and userdata == "":
        userdata = homedata / 'Library' / 'Application Support'
        userdata = checkPath(userdata)
    if userdata == "":
        userdata = homedata / '.config'
        userdata = checkPath(userdata)

    if userdata == "": userdata = Path(os.getcwd()) / 'config'
    else: userdata = userdata / 'deemix'

    if os.getenv("DEEMIX_DATA_DIR"):
        userdata = Path(os.getenv("DEEMIX_DATA_DIR"))
    return userdata