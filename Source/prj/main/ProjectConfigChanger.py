import mtm.util.YamlSerializer as YamlSerializer
from mtm.log import Logger
from mtm.util import SystemHelper, VarManager
from mtm.util.Assert import *
from mtm.ioc.Inject import Inject
from mtm.util.Platforms import Platforms
from prj.main import PackageManager
from prj.main.ProjenyConstants import ProjectConfigFileName
from prj.main.ProjectConfig import ProjectConfig


class ProjectConfigChanger:
    _log: Logger = Inject('Logger')
    _sys: SystemHelper = Inject('SystemHelper')
    _packageManager: PackageManager = Inject('PackageManager')
    _varMgr: VarManager = Inject('VarManager')

    def _getProjectConfigPath(self, projectName: str):
        return self._varMgr.expandPath('[UnityProjectsDir]/{0}/{1}'.format(projectName, ProjectConfigFileName))

    def loadProjectConfig(self, projectName: str):
        configPath = self._getProjectConfigPath(projectName)

        yamlData = YamlSerializer.deserialize(self._sys.readFileAsText(configPath))

        result = ProjectConfig()

        for pair in yamlData.__dict__.items():
            result.__dict__[pair[0]] = pair[1]

        result.upgradePlatforms()
        return result

    def saveProjectConfig(self, projectName: str, projectConfig):
        configPath = self._getProjectConfigPath(projectName)
        self._sys.writeFileAsText(configPath, YamlSerializer.serialize(projectConfig))

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
