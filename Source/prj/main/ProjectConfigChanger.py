from pprint import pprint, pformat
from typing import Any

import mtm.util.YamlSerializer as YamlSerializer
from mtm.log.Logger import Logger
from mtm.util.Assert import *
from mtm.ioc.Inject import Inject
from mtm.util.Platforms import Platforms
from mtm.util.SystemHelper import SystemHelper
from mtm.util.VarManager import VarManager
from prj.main.ProjectTarget import ProjectTarget
from prj.main.ProjenyConstants import ProjectConfigFileName
from prj.main.ProjectConfig import ProjectConfig


class ProjectConfigChanger:
    _log: Logger = Inject[Logger]('Logger')
    _sys: SystemHelper = Inject[SystemHelper]('SystemHelper')
    _packageManager = Inject[Any]('PackageManager')
    _varMgr: VarManager = Inject[VarManager]('VarManager')

    def _getProjectConfigPath(self, projectName: str):
        return self._varMgr.expandPath('[UnityProjectsDir]/{0}/{1}'.format(projectName, ProjectConfigFileName))

    def loadProjectConfig(self, projectName: str) -> ProjectConfig:
        configPath = self._getProjectConfigPath(projectName)

        yamlData = YamlSerializer.deserialize(self._sys.readFileAsText(configPath))

        result = ProjectConfig()

        for pair in yamlData.__dict__.items():
            result.__dict__[pair[0]] = pair[1]

        self._parseTargets(result)
        result.upgradePlatforms()
        return result

    def _parseTargets(self, config: ProjectConfig):
        targetsRaw = config.targets
        config.targets = []

        for t in targetsRaw:
            if not hasattr(t, 'target'):
                continue

            targetAttr = getattr(t, 'target')
            if hasattr(t, 'tag'):
                tagAttr = getattr(t, 'tag')
            else:
                tagAttr = None

            config.targets.append(ProjectTarget(targetAttr, tagAttr))

    def saveProjectConfig(self, projectName: str, projectConfig):
        configPath = self._getProjectConfigPath(projectName)
        text = YamlSerializer.serialize(projectConfig)
        print(text)
        self._sys.writeFileAsText(configPath, text)

    def addPackage(self, projectName: str, packageName: str, addToAssetsFolder: bool):
        with self._log.heading('Adding package {0} to project {1}'.format(packageName, projectName)):
            assertThat(packageName in self._packageManager.getAllPackageNames(), "Could not find the given package '{0}' in the UnityPackages folder", packageName)
            self._packageManager.setPathsForProjectPlatform(projectName, Platforms.Windows)

            projConfig = self.loadProjectConfig(projectName)

            assertThat(packageName not in projConfig.assetsFolder and packageName not in projConfig.pluginsFolder,
                       "Given package '{0}' has already been added to project config", packageName)

            if addToAssetsFolder:
                projConfig.assetsFolder.append(packageName)
            else:
                projConfig.pluginsFolder.append(packageName)

            self.saveProjectConfig(projectName, projConfig)

            self._log.good("Added package '{0}' to file '{1}/{2}'", packageName, projectName, ProjectConfigFileName)
