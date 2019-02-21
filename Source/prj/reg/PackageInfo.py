
from mtm.util.Assert import *

class PackageFolderInfo:
    def __init__(self):
        self.path = None
        self.packages = []
        self.projectDirectory = False

class PackageInfo:
    def __init__(self):
        self.name = None
        self.path = None
        # Might be null
        self.installInfo = None

class PackageInstallInfo:
    def __init__(self):
        self.installDate = None
        self.releaseInfo = None
