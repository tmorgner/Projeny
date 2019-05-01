from typing import List

from mtm.config.Config import Config
from prj.main.AssemblyProjectInfo import AssemblyProjectInfo
from prj.main.FolderTypes import FolderTypes


class PackageData:
    isPluginDir: bool
    name: str
    config: Config
    createCustomVsProject: bool
    explicitDependencies: List[str]
    forcePluginsDir: bool
    folderType: str
    assemblyProjectInfo: AssemblyProjectInfo
    dirPath: str
    groupedDependencies: List[str]

    def __init__(
        self, isPluginDir, name, config, createCustomVsProject,
            explicitDependencies, forcePluginsDir, folderType, assemblyProjectInfo, dirPath, groupedDependencies):

        self.isPluginDir = isPluginDir
        self.name = name
        self.explicitDependencies = explicitDependencies
        self.config = config
        self.createCustomVsProject = createCustomVsProject
        self.allDependencies = None
        self.folderType = folderType
        self.assemblyProjectInfo = assemblyProjectInfo
        self.forcePluginsDir = forcePluginsDir
        self.dirPath = dirPath
        self.groupedDependencies = groupedDependencies

    @property
    def outputDirVar(self):

        if self.folderType == FolderTypes.AndroidProject:
            return '[PluginsAndroidDir]'

        if self.folderType == FolderTypes.AndroidLibraries:
            return '[PluginsAndroidLibraryDir]'

        if self.folderType == FolderTypes.Ios:
            return '[PluginsIosLibraryDir]'

        if self.folderType == FolderTypes.WebGl:
            return '[PluginsWebGlLibraryDir]'

        if self.folderType == FolderTypes.StreamingAssets:
            return '[StreamingAssetsDir]'

        if self.folderType == FolderTypes.Gizmos:
            return '[GizmosDir]'

        if self.isPluginDir:
            return '[PluginsDir]'

        return '[ProjectAssetsDir]'
