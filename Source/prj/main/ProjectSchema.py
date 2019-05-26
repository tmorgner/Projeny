from typing import Dict, List, Optional

from prj.main.PackageData import PackageData
from prj.main.ProjectTarget import ProjectTarget


class ProjectSchema:
    name: str
    packages: Dict[str, PackageData]
    customFolderMap: Dict[str, str]
    projectSettingsPath: str
    unityPackagesPath: Optional[str]
    projectTargets: ProjectTarget
    targets: List[ProjectTarget]

    def __init__(self, name, packages, customFolderMap, projectSettingsPath, unityPackagesPath, projectTarget, targets):
        self.name = name
        self.packages = packages
        self.customFolderMap = customFolderMap
        self.projectSettingsPath = projectSettingsPath
        self.unityPackagesPath = unityPackagesPath
        self.projectTargets = projectTarget
        self.targets = targets
