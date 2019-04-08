from typing import List, Optional

from mtm.util.Assert import assertThat
from mtm.util.Platforms import Platforms
from prj.main.ProjectTarget import ProjectTarget


class ProjectConfig:
    targets: List[ProjectTarget]

    def __init__(self):
        self.pluginsFolder = []
        self.assetsFolder = []
        self.solutionProjects = []
        self.solutionFolders = []
        self.packageFolders = []
        self.packageProjectFolders = []
        self.targetPlatforms = []
        self.projectSettingsPath = None
        self.unityPackagesPath = None
        self.targets = []

    def upgradePlatforms(self):
        # This version supports a new project definition format that allows multiple projects
        # for each platform. This enables to have a different build settings for each project
        # including different plugin configurations.
        for platform in self.targetPlatforms:
            target_def = ProjectTarget(platform)
            self.targets.append(target_def)

        cleanTargets = []
        for t in self.targets:
            target = ProjectTarget(t.target, t.tag)
            if target not in cleanTargets:
                cleanTargets.append(target)

        self.targetPlatforms = []
        self.targets = cleanTargets

    def parseProjectTargetFromDirectoryName(self, projectName: str, platformProjectDirName: str):
        platformAndTag = platformProjectDirName[len(projectName) + 1:]
        return self.parseProjectTarget(platformAndTag)

    def parseProjectTarget(self, platformAndTag: str):
        platform = self._findInTargets(platformAndTag)
        if platform is None:
            assertThat(False, "Invalid platform: " + str(platformAndTag))

        return platform

    def _findInTargets(self, platformAndTag: str) -> Optional[ProjectTarget]:
        for t in self.targets:
            if t.ToPath().lower() == platformAndTag.lower():
                return t

        return None
