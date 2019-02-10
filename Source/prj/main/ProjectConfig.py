from typing import List
from prj.main.ProjectTarget import ProjectTarget


class ProjectConfig:
    targets: List[ProjectTarget]

    def __init__(self):
        self.pluginsFolder = []
        self.assetsFolder = []
        self.solutionProjects = []
        self.solutionFolders = []
        self.packageFolders = []
        self.targetPlatforms = []
        self.projectSettingsPath = None
        self.unityPackagesPath = None
        self.targets = []

    def upgradePlatforms(self):
        # This version supports a new project definition format that allows multiple projects
        # for each platform. This enables to have a different build settings for each project
        # including different plugin configurations.
        if len(self.targets) == 0:
            for platform in self.targetPlatforms:
                target_def = ProjectTarget(platform)
                self.targets.append(target_def)

        cleanTargets = []
        for t in self.targets:
            target = ProjectTarget(t.target, t.tag)
            cleanTargets.append(target)

        self.targets = cleanTargets

