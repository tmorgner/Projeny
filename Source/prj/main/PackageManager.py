import os
from typing import Optional

from mtm.util import UnityHelper, JunctionHelper
from mtm.util.VarManager import VarManager
from mtm.log.Logger import Logger
from mtm.util.SystemHelper import SystemHelper
from mtm.util.Platforms import Platforms
from mtm.util.CommonSettings import ConfigFileName
import mtm.util.MiscUtil as MiscUtil
import mtm.util.PlatformUtil as PlatformUtil
import mtm.util.YamlSerializer as YamlSerializer
from mtm.ioc.Inject import Inject
from mtm.ioc.Inject import InjectMany
from mtm.util.Assert import *

from prj.main.ProjectConfigChanger import ProjectConfigChanger
from prj.main.PackageData import PackageData
from prj.main.ProjectSchema import ProjectSchema
from prj.main.ProjectTarget import ProjectTarget
from prj.main.UnityEditorMenuGenerator import UnityEditorMenuGenerator
from prj.main.ProjectSchemaLoader import ProjectSchemaLoader
from prj.main.FolderTypes import FolderTypes
from prj.reg.PackageInfo import PackageInfo, PackageFolderInfo

import shutil


InstallInfoFileName = 'ProjenyInstall.yaml'

from prj.main.ProjenyConstants import ProjectConfigFileName


class SourceControlTypes:
    Git = 'Git'
    Subversion = 'Subversion'
    # TODO - how to detect?
    # Perforce = 'Perforce'


class PackageManager:
    """
    Main interface for Modest Package Manager
    """
    _config = Inject('Config')
    _varMgr: VarManager = Inject('VarManager')
    _log: Logger = Inject('Logger')
    _sys: SystemHelper = Inject('SystemHelper')
    _unityHelper: UnityHelper = Inject('UnityHelper')
    _junctionHelper: JunctionHelper = Inject('JunctionHelper')
    _projectInitHandlers = InjectMany('ProjectInitHandlers')
    _schemaLoader: ProjectSchemaLoader = Inject('ProjectSchemaLoader')
    _commonSettings = Inject('CommonSettings')
    _projectConfigChanger: ProjectConfigChanger = Inject[ProjectConfigChanger]('ProjectConfigChanger')
    _unityEditorMenuGenerator: UnityEditorMenuGenerator = Inject('UnityEditorMenuGenerator')

    def projectExists(self, projectName: str):
        return self._sys.directoryExists('[UnityProjectsDir]/{0}'.format(projectName))

    def listAllProjects(self):
        projectNames = self.getAllProjectNames()

        defaultProj = self._config.tryGetString(None, 'DefaultProject')

        self._log.info("Found {0} Projects:".format(len(projectNames)))
        for proj in projectNames:
            alias = self.tryGetAliasFromFullName(proj)
            output = proj
            if alias:
                output = "{0} ({1})".format(output, alias)

            if defaultProj == proj:
                output += " (default)"

            self._log.info("  " + output)

    def listTags(self, projectName: str, platform: str):
        schema = self._schemaLoader.loadProjectConfig(projectName)
        tags = []

        for t in schema.targets:
            print(t.ToName())
            if t.tag is None:
                continue

            if t.target == platform and t.tag not in tags:
                tags.append(t.tag)

        self._log.info("Tags: " + ','.join(map(str, tags)))

    def listAllPackages(self, projectName: str):
        packagesNames = self.getAllPackageNames(projectName)
        self._log.info("Found {0} Packages:".format(len(packagesNames)))
        for packageName in packagesNames:
            self._log.info("  " + packageName)

    def _findSourceControl(self):
        for dirPath in self._sys.getParentDirectoriesWithSelf('[ConfigDir]'):
            if self._sys.directoryExists(os.path.join(dirPath, '.git')):
                return SourceControlTypes.Git

            if self._sys.directoryExists(os.path.join(dirPath, '.svn')):
                return SourceControlTypes.Subversion

        return None

    # Todo: This method should take into account what is defined in the default configuration.
    def createProject(self, projName: str, target: ProjectTarget, settingsProject: Optional[str] = None):
        if target is None:
            target = ProjectTarget(Platforms.Windows, None)

        with self._log.heading('Initializing new project-platform "{0}-{1}" with tag ', projName, target.target,
                               target.tag):
            projDirPath = self._varMgr.expand('[UnityProjectsDir]/{0}'.format(projName))
            assertThat(not self._sys.directoryExists(projDirPath),
                       "Cannot initialize new project '{0}', found existing project at '{1}'", projName, projDirPath)

            self._sys.createDirectory(projDirPath)

            if settingsProject is None:
                settingsPath = '[ProjectRoot]/ProjectSettings'
                newProjSettingsDir = os.path.join(projDirPath, 'ProjectSettings')

                if self._varMgr.hasKey('DefaultProjectSettingsDir') and self._sys.directoryExists(
                        '[DefaultProjectSettingsDir]'):
                    self._sys.copyDirectory('[DefaultProjectSettingsDir]', newProjSettingsDir)
                else:
                    self._sys.createDirectory(newProjSettingsDir)
            else:
                settingsPath = '[ProjectRoot]/../{0}/ProjectSettings'.format(settingsProject)

            newUnityPackagesDir = os.path.join(projDirPath, 'Packages')
            self._sys.createDirectory(newUnityPackagesDir)

            newUnityPackageManagerDir = os.path.join(projDirPath, 'UnityPackageManager')
            self._sys.createDirectory(newUnityPackageManagerDir)

            with self._sys.openOutputFile(os.path.join(projDirPath, ProjectConfigFileName)) as outFile:
                outFile.write(
                    """
ProjectSettingsPath: '{0}'
#AssetsFolder:
    # Uncomment and Add package names here
""".format(settingsPath))

            self.updateProjectJunctions(projName, target)
            # self.updateLinksForAllProjects()

    def getProjectFromAlias(self, alias: str):
        result = self.tryGetProjectFromAlias(alias)
        assertThat(result, "Unrecognized project '{0}' and could not find an alias with that name either".format(alias))
        return result

    def tryGetProjectFromAlias(self, alias: str):
        aliasMap = self._config.tryGetDictionary({}, 'ProjectAliases')

        if alias not in aliasMap.keys():
            return None

        return aliasMap[alias]

    def tryGetAliasFromFullName(self, name: str):
        aliasMap = self._config.tryGetDictionary({}, 'ProjectAliases')

        for pair in aliasMap.items():
            if pair[1] == name:
                return pair[0]

        return None

    def _validateDirForFolderType(self, packageInfo: PackageData, sourceDir: str):
        if packageInfo.folderType == FolderTypes.AndroidProject:
            assertThat(os.path.exists(os.path.join(sourceDir, "project.properties")),
                       "Project '{0}' is marked with foldertype AndroidProject and therefore must contain a project.properties file".format(
                           packageInfo.name))

    def updateProjectJunctions(self, projectName: str, projectTarget: ProjectTarget):
        """
        Initialize all the folder links for the given project
        """

        with self._log.heading('Updating package directories for project {0}'.format(projectName)):
            self.checkProjectInitialized(projectName, projectTarget)
            self.setPathsForProjectPlatform(projectName, projectTarget)
            projConfig = self._projectConfigChanger.loadProjectConfig(projectName)
            if projectTarget not in projConfig.targets:
                projConfig.targets.append(projectTarget)
                self._projectConfigChanger.saveProjectConfig(projectName, projConfig)
            schema = self._schemaLoader.loadSchema(projectName, projectTarget)
            self._updateDirLinksForSchema(schema)

            self._checkForVersionControlIgnore()

            self._log.good('Finished updating packages for project "{0}"'.format(schema.name))

    def _checkForVersionControlIgnore(self):
        sourceControlType = self._findSourceControl()

        if sourceControlType == SourceControlTypes.Git:
            self._log.info('Detected git repository.  Making sure generated project folders are ignored by git...')
            if not self._sys.fileExists('[ProjectRoot]/.gitignore'):
                self._sys.copyFile('[ProjectRootGitIgnoreTemplate]', '[ProjectRoot]/.gitignore')
                self._log.warn('Added new git ignore file to project root')
        elif sourceControlType == SourceControlTypes.Subversion:
            self._log.info(
                'Detected subversion repository. Making sure generated project folders are ignored by SVN...')
            try:
                self._sys.executeAndWait('svn propset svn:ignore -F [ProjectRootSvnIgnoreTemplate] .', '[ProjectRoot]')
            except Exception as e:
                self._log.warn(
                    "Warning: Failed to add generated project directories to SVN ignore!  This may be caused by 'svn' not being available on the command line.  Details: " + str(
                        e))
        # else:
        # self._log.warn('Warning: Could not determine source control in use!  An ignore file will not be added for your project.')

    def getAllPackageFolderInfos(self, projectName: str):
        folderInfos = []

        self.setPathsForProject(projectName)
        projConfig = self._schemaLoader.loadProjectConfig(projectName)

        for packageFolder in projConfig.packageFolders:
            folderInfo = PackageFolderInfo()
            folderInfo.path = packageFolder
            folderInfo.projectDirectory = False

            if self._sys.directoryExists(packageFolder):
                for packageName in self._sys.walkDir(packageFolder):

                    if self.isIgnored(packageName):
                        continue

                    packageDirPath = os.path.join(packageFolder, packageName)

                    if not self._sys.IsDir(packageDirPath):
                        continue

                    installInfoFilePath = os.path.join(packageDirPath, InstallInfoFileName)

                    packageInfo = PackageInfo()
                    packageInfo.name = packageName
                    packageInfo.path = packageDirPath

                    if self._sys.fileExists(installInfoFilePath):
                        installInfo = YamlSerializer.deserialize(self._sys.readFileAsText(installInfoFilePath))
                        packageInfo.installInfo = installInfo

                    folderInfo.packages.append(packageInfo)

            folderInfos.append(folderInfo)

        for packageFolder in projConfig.packageProjectFolders:
            folderInfo = PackageFolderInfo()
            folderInfo.path = packageFolder
            folderInfo.projectDirectory = True

            if self._sys.directoryExists(packageFolder):
                for packageName in self._sys.walkDir(packageFolder):

                    if self.isIgnored(packageName):
                        continue

                    packageDirPath = os.path.join(packageFolder, packageName, "Assets", "Plugins", packageName)

                    if not self._sys.IsDir(packageDirPath):
                        continue

                    installInfoFilePath = os.path.join(packageDirPath, InstallInfoFileName)

                    packageInfo = PackageInfo()
                    packageInfo.name = packageName
                    packageInfo.path = packageDirPath

                    if self._sys.fileExists(installInfoFilePath):
                        installInfo = YamlSerializer.deserialize(self._sys.readFileAsText(installInfoFilePath))
                        packageInfo.installInfo = installInfo

                    folderInfo.packages.append(packageInfo)

            folderInfos.append(folderInfo)

        for packageFolder in projConfig.packageProjectFolders:
            folderInfo = PackageFolderInfo()
            folderInfo.path = packageFolder
            folderInfo.projectDirectory = True

            if self._sys.directoryExists(packageFolder):
                for packageName in self._sys.walkDir(packageFolder):

                    if self.isIgnored(packageName):
                        continue

                    packageDirPath = os.path.join(packageFolder, packageName, "Assets", packageName)

                    if not self._sys.IsDir(packageDirPath):
                        continue

                    installInfoFilePath = os.path.join(packageDirPath, InstallInfoFileName)

                    packageInfo = PackageInfo()
                    packageInfo.name = packageName
                    packageInfo.path = packageDirPath

                    if self._sys.fileExists(installInfoFilePath):
                        installInfo = YamlSerializer.deserialize(self._sys.readFileAsText(installInfoFilePath))
                        packageInfo.installInfo = installInfo

                    folderInfo.packages.append(packageInfo)

            folderInfos.append(folderInfo)
        return folderInfos

    def deleteProject(self, projName: str):
        with self._log.heading("Deleting project '{0}'", projName):
            assertThat(self._varMgr.hasKey('UnityProjectsDir'),
                       "Could not find 'UnityProjectsDir' in PathVars.  Have you set up your {0} file?", ConfigFileName)
            fullPath = '[UnityProjectsDir]/{0}'.format(projName)

            assertThat(self._sys.directoryExists(fullPath), "Could not find project with name '{0}' - delete failed",
                       projName)

            self.clearProjectGeneratedFiles(projName)
            self._sys.deleteDirectory(fullPath)
            # self.updateLinksForAllProjects()

    def isIgnored(self, name: str):
        return str(name) == ".git" or str(name) == ".svn"

    def getAllPackageNames(self, projectName: str):
        results = []
        self.setPathsForProject(projectName)
        projConfig = self._schemaLoader.loadProjectConfig(projectName)

        for packageFolder in projConfig.packageFolders:
            if not self._sys.directoryExists(packageFolder):
                continue

            for name in self._sys.walkDir(packageFolder):
                if self.isIgnored(name):
                    continue

                if self._sys.IsDir(os.path.join(packageFolder, name)):
                    results.append(name)

        for packageFolder in projConfig.packageProjectFolders:
            if not self._sys.directoryExists(packageFolder):
                continue

            for name in self._sys.walkDir(packageFolder):
                if self.isIgnored(name):
                    continue

                packagePath = os.path.join(packageFolder, name, "Assets", "Plugins", name)
                if self._sys.IsDir(packagePath):
                    results.append(name)

                packagePath = os.path.join(packageFolder, name, "Assets", name)
                if self._sys.IsDir(packagePath):
                    results.append(name)

        return results

    def getAllProjectNames(self):
        assertThat(self._varMgr.hasKey('UnityProjectsDir'),
                   "Could not find 'UnityProjectsDir' in PathVars.  Have you set up your {0} file?", ConfigFileName)

        results = []
        for name in self._sys.walkDir('[UnityProjectsDir]'):
            if self._sys.IsDir('[UnityProjectsDir]/' + name):
                results.append(name)
        return results

    # This will set up all the directory junctions for all projects for all platforms
    def updateLinksForAllProjects(self) -> bool:
        for projectName in self.getAllProjectNames():

            try:
                projConfig = self._schemaLoader.loadProjectConfig(projectName)
            except Exception as e:
                self._log.warn('Could not load project config for "{0}"'.format(projectName))
                raise

            with self._log.heading('Initializing project "{0}"'.format(projectName)):
                try:
                    for platform in projConfig.targets:
                        self.updateProjectJunctions(projectName, platform)

                    self._log.good('Successfully initialized project "{0}"'.format(projectName))
                except Exception as e:
                    self._log.warn('Failed to initialize project "{0}": {1}'.format(projectName, e))
                    raise

        return True

    def _createSwitchProjectMenuScript(self, currentProjName: str, currentPlatformTarget: ProjectTarget, outputPath: str):
        projectNames = self.getAllProjectNames()
        self._unityEditorMenuGenerator.Generate(currentProjName, currentPlatformTarget, outputPath, projectNames)

    def _addGeneratedProjenyFiles(self, outDir: str, schema: ProjectSchema):
        menuFileOutPath = outDir + '/Editor/ProjenyChangeProjectMenu.cs'
        placeholderOutPath1 = outDir + '/Placeholder.cs'
        placeholderOutPath2 = outDir + '/Editor/Placeholder.cs'

        # Need to always use the same meta files to avoid having unity do a refresh
        self._createSwitchProjectMenuScript(schema.name, schema.projectTargets, menuFileOutPath)
        self._sys.copyFile('[ProjenyChangeProjectMenuMeta]', menuFileOutPath + ".meta")

        self._sys.copyFile('[PlaceholderFile1]', placeholderOutPath1)
        self._sys.copyFile('[PlaceholderFile1].meta', placeholderOutPath1 + ".meta")

        self._sys.copyFile('[PlaceholderFile2]', placeholderOutPath2)
        self._sys.copyFile('[PlaceholderFile2].meta', placeholderOutPath2 + ".meta")

    def _updateDirLinksForSchema(self, schema: ProjectSchema):
        self._removeProjectPlatformJunctions()

        self._sys.deleteDirectoryIfExists('[PluginsDir]/Projeny')

        # Define DoNotIncludeProjenyInUnityProject only if you want to include Projeny as just another prebuilt package
        # This is nice because then you can call methods on projeny from another package
        if self._config.tryGetBool(False, 'DoNotIncludeProjenyInUnityProject'):
            self._addGeneratedProjenyFiles('[PluginsDir]/ProjenyGenerated', schema)
        else:
            dllOutPath = '[PluginsDir]/Projeny/Editor/Projeny.dll'

            self._sys.copyFile('[ProjenyUnityEditorDllPath]', dllOutPath)
            self._sys.copyFile('[ProjenyUnityEditorDllMetaFilePath]', dllOutPath + '.meta')

            self._sys.copyFile('[YamlDotNetDllPath]', '[PluginsDir]/Projeny/Editor/YamlDotNet.dll')

            self._sys.copyDirectory('[ProjenyUnityEditorAssetsDirPath]', '[PluginsDir]/Projeny/Editor/Assets')

            self._addGeneratedProjenyFiles('[PluginsDir]/Projeny', schema)

        self._junctionHelper.makeJunction(schema.projectSettingsPath, '[ProjectPlatformRoot]/ProjectSettings')
        if schema.unityPackagesPath is not None:
            self._junctionHelper.makeJunction(schema.unityPackagesPath, '[ProjectPlatformRoot]/Packages')

        for packageInfo in schema.packages.values():
            self._log.debug('Processing package "{0}"'.format(packageInfo.name))

            self._validateDirForFolderType(packageInfo, packageInfo.dirPath)

            assertThat(os.path.exists(packageInfo.dirPath),
                       "Could not find package with name '{0}' while processing schema '{1}'.  See build log for full object graph to see where it is referenced".format(
                           packageInfo.name, schema.name))

            outputPackageDir = self._varMgr.expandPath(packageInfo.outputDirVar)

            linkDir = os.path.join(outputPackageDir, packageInfo.name)

            assertThat(not os.path.exists(linkDir), "Did not expect this path to exist: '{0}'".format(linkDir))

            self._junctionHelper.makeJunction(packageInfo.dirPath, linkDir)

    def checkProjectInitialized(self, projectName: str, projectTarget: ProjectTarget):
        self.setPathsForProjectPlatform(projectName, projectTarget)

        if self._sys.directoryExists('[ProjectPlatformRoot]'):
            return

        self._log.warn(
            'Project "{0}" is not initialized for platform "{1}" and tag "{2}".  Initializing now.'.format(projectName,
                                                                                                           projectTarget.target,
                                                                                                           projectTarget.tag))
        self._initNewProjectForPlatform(projectName, projectTarget)

    def isProjectPlatformInitialized(self, projectName: str, projectTarget: ProjectTarget):
        self.setPathsForProjectPlatform(projectName, projectTarget)
        return self._sys.directoryExists('[ProjectPlatformRoot]')

    def setPathsForProject(self, projectName: str):
        self._varMgr.set('ShortProjectName', self._commonSettings.getShortProjectName(projectName))
        self._varMgr.set('ProjectName', projectName)
        self._varMgr.set('ProjectRoot', '[UnityProjectsDir]/[ProjectName]')

    def setPathsForProjectPlatform(self, projectName: str, projectTarget: ProjectTarget):

        self.setPathsForProject(projectName)

        self._varMgr.set('ShortPlatform', PlatformUtil.toPlatformTargetFolderName(projectTarget))

        self._varMgr.set('Platform', projectTarget.target)

        self._varMgr.set('ProjectPlatformRoot', '[ProjectRoot]/[ShortProjectName]-[ShortPlatform]')
        self._varMgr.set('ProjectAssetsDir', '[ProjectPlatformRoot]/Assets')

        # For reasons I don't understand, the unity generated project is named with 'Assembly' on some machines and not other
        # Problem due to unity version but for now just allow either or
        self._varMgr.set('UnityGeneratedProjectEditorPath',
                         '[ProjectPlatformRoot]/[ShortProjectName]-[ShortPlatform].CSharp.Editor.Plugins.csproj')
        self._varMgr.set('UnityGeneratedProjectEditorPath2',
                         '[ProjectPlatformRoot]/Assembly-CSharp-Editor-firstpass.csproj')
        self._varMgr.set('UnityGeneratedProjectEditorPath3',
                         '[ProjectPlatformRoot]/[ProjectName]-[Platform].Editor.Plugins.csproj')

        self._varMgr.set('UnityGeneratedProjectPath',
                         '[ProjectPlatformRoot]/[ShortProjectName]-[ShortPlatform].CSharp.Plugins.csproj')
        self._varMgr.set('UnityGeneratedProjectPath2', '[ProjectPlatformRoot]/Assembly-CSharp-firstpass.csproj')
        self._varMgr.set('UnityGeneratedProjectPath3', '[ProjectPlatformRoot]/[ProjectName]-[Platform].Plugins.csproj')

        self._varMgr.set('PluginsDir', '[ProjectAssetsDir]/Plugins')
        self._varMgr.set('PluginsAndroidDir', '[PluginsDir]/Android')
        self._varMgr.set('PluginsAndroidLibraryDir', '[PluginsDir]/Android/libs')
        self._varMgr.set('PluginsIosLibraryDir', '[PluginsDir]/iOS')
        self._varMgr.set('PluginsWebGlLibraryDir', '[PluginsDir]/WebGL')

        self._varMgr.set('StreamingAssetsDir', '[ProjectAssetsDir]/StreamingAssets')
        self._varMgr.set('GizmosDir', '[ProjectAssetsDir]/Gizmos')

        self._varMgr.set('IntermediateFilesDir', '[ProjectPlatformRoot]/obj')

        self._varMgr.set('SolutionPath', '[ProjectRoot]/[ProjectName]-[Platform].sln')

    def deleteAllLinks(self):
        with self._log.heading('Deleting all junctions for all projects'):
            projectNames = []
            projectsDir = self._varMgr.expandPath('[UnityProjectsDir]')

            for itemName in os.listdir(projectsDir):
                fullPath = os.path.join(projectsDir, itemName)
                if os.path.isdir(fullPath):
                    projectNames.append(itemName)

            for projectName in projectNames:
                for platform in Platforms.All:
                    self.setPathsForProjectPlatform(projectName, platform)
                    self._removeProjectPlatformJunctions()

    def _removeProjectPlatformJunctions(self):
        self._junctionHelper.removeJunctionsInDirectory('[ProjectPlatformRoot]', True)

    def clearAllProjectGeneratedFiles(self):
        for projName in self.getAllProjectNames():
            self.clearProjectGeneratedFiles(projName)

    def clearProjectGeneratedFiles(self, projectName: str):
        with self._log.heading('Clearing generated files for project {0}'.format(projectName)):
            self._junctionHelper.removeJunctionsInDirectory('[UnityProjectsDir]/{0}'.format(projectName), True)
            for platform in Platforms.All:
                self.setPathsForProjectPlatform(projectName, ProjectTarget(platform))

                if os.path.exists(self._varMgr.expandPath('[ProjectPlatformRoot]')):
                    platformRootPath = self._varMgr.expand('[ProjectPlatformRoot]')

                    try:
                        shutil.rmtree(platformRootPath)
                    except:
                        self._log.warn(
                            'Unable to remove path {0}.  Trying to kill adb.exe to see if that will help...'.format(
                                platformRootPath))
                        MiscUtil.tryKillAdbExe(self._sys)

                        try:
                            shutil.rmtree(platformRootPath)
                        except:
                            self._log.error(
                                'Still unable to remove path {0}!  A running process may have one of the files locked.  Ensure you have closed down unity / visual studio / etc.'.format(
                                    platformRootPath))
                            raise

                    self._log.debug('Removed project directory {0}'.format(platformRootPath))
                    self._log.good('Successfully deleted project {0} ({1})'.format(projectName, platform))
                else:
                    self._log.debug('Project {0} ({1}) already deleted'.format(projectName, platform))

                # Remove the solution files and the suo files etc.
                self._sys.removeByRegex('[ProjectRoot]/[ProjectName]-[Platform].*')

    def _initNewProjectForPlatform(self, projectName: str, projectTarget: ProjectTarget):

        with self._log.heading('Initializing new project {0} ({1}) {2}'.format(projectName, projectTarget.target, projectTarget.tag)):
            schema = self._schemaLoader.loadSchema(projectName, projectTarget)
            self.setPathsForProjectPlatform(projectName, projectTarget)

            assertThat(self._sys.directoryExists(schema.projectSettingsPath),
                       "Expected to find project settings directory at '{0}'",
                       self._varMgr.expand(schema.projectSettingsPath))

            if self._sys.directoryExists('[ProjectPlatformRoot]'):
                raise Exception(
                    'Unable to create project "{0}". Directory already exists at path "{1}".'.format(projectName,
                                                                                                     self._varMgr.expandPath(
                                                                                                         '[ProjectPlatformRoot]')))

            try:
                self._sys.createDirectory('[ProjectPlatformRoot]')

                self._log.debug('Created directory "{0}"'.format(self._varMgr.expandPath('[ProjectPlatformRoot]')))

                self._junctionHelper.makeJunction(schema.projectSettingsPath, '[ProjectPlatformRoot]/ProjectSettings')
                if schema.unityPackagesPath is not None:
                    self._junctionHelper.makeJunction(schema.unityPackagesPath, '[ProjectPlatformRoot]/Packages')

                self._updateDirLinksForSchema(schema)

                for handler in self._projectInitHandlers:
                    handler.onProjectInit(projectName, projectTarget.target)

            except:
                self._log.error("Failed to initialize project '{0}' for platform '{1}' {2}.".format(schema.name, projectTarget.target, projectTarget.tag))
                raise

            self._log.good('Finished creating new project "{0}" ({1}) {2}'.format(schema.name, projectTarget.target, projectTarget.tag))
