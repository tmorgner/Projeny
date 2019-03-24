import os
import time

from mtm.log.LogWatcher import LogWatcher

from mtm.ioc.Inject import Inject

from mtm.util.Assert import *
import mtm.util.PlatformUtil as PlatformUtil
from mtm.util.Platforms import Platforms

from mtm.util.SystemHelper import ProcessErrorCodeException
from prj.main.ProjectTarget import ProjectTarget

UnityLogFileLocation = os.getenv('localappdata') + '\\Unity\\Editor\\Editor.log'


class UnityReturnedErrorCodeException(Exception):
    pass


class UnityUnknownErrorException(Exception):
    pass


class UnityHelper:
    _log = Inject('Logger')
    _sys = Inject('SystemHelper')
    _varMgr = Inject('VarManager')
    _commonSettings = Inject('CommonSettings')
    _config = Inject('Config')

    def __init__(self):
        pass

    def onUnityLog(self, logStr: str):
        self._log.noise(logStr)

    def runEditorFunction(self, projectName: str, platform: ProjectTarget, editorCommand: str, batchMode=True,
                          quitAfter=True, extraArgs=''):
        allArgs = ''

        if quitAfter:
            allArgs += ' -quit'

        if batchMode:
            allArgs += ' -batchmode -nographics'

        allArgs += ' ' + extraArgs

        self.runEditorFunctionRaw(projectName, platform, editorCommand, allArgs)

    def openUnity(self, projectName: str, platform: ProjectTarget):
        with self._log.heading('Opening Unity'):
            unity = self.find_unity_for_project(projectName, platform)

            projectPath = self._sys.canonicalizePath("[UnityProjectsDir]/{0}/{1}-{2}".format(projectName,
                                                                                             self._commonSettings.getShortProjectName(
                                                                                                 projectName),
                                                                                             PlatformUtil.toPlatformTargetFolderName(
                                                                                                 platform)))

            self._sys.executeNoWait('"{0}" -buildTarget {1} -projectPath "{2}"'.format(unity,
                                                                                       self._getBuildTargetArg(platform),
                                                                                       projectPath))

    def _getBuildTargetArg(self, platformTarget: ProjectTarget):
        platform = platformTarget.target

        if platform == Platforms.Windows:
            if self._config.tryGetBool(False, 'Unity', 'Win64IsDefault'):
                return 'win64'
            return 'win32'

        if platform == Platforms.Android:
            return 'android'

        if platform == Platforms.WebGl:
            return 'WebGl'

        if platform == Platforms.OsX:
            return 'osx'

        if platform == Platforms.Linux:
            return 'linux'

        if platform == Platforms.Ios:
            return 'ios'

        if platform == Platforms.UWP:
            return 'wsaplayer'

        if platform == Platforms.Lumin:
            return 'Lumin'

        assertThat(False)

    def extract_version(self, projectName: str, platform: ProjectTarget) -> str:
        shortName = self._commonSettings.getShortProjectName(projectName)
        targetFolder = PlatformUtil.toPlatformTargetFolderName(platform)
        projectPath = self._varMgr.expandPath("[UnityProjectsDir]/{0}/{1}-{2}".format(projectName,
                                                                                      shortName,
                                                                                      targetFolder))

        versionPath = os.path.join(projectPath, "ProjectSettings", "ProjectVersion.txt")
        file = open(versionPath)
        try:
            contents = file.readline()
            if contents.startswith("m_EditorVersion: "):
                versionTxt = contents[len("m_EditorVersion: "):]
                return versionTxt.strip()
        finally:
            file.close()
        return ""

    def find_unity_for_project(self, projectName: str, platform: ProjectTarget):
        targetVersion = self.extract_version(projectName, platform)
        if targetVersion is not "":
            self._log.info("Detected unity version {0} in project {1}".format(targetVersion, projectName))

            hubDirectory = self._varMgr.expandPath("[UnityHubPath]")
            unityPath = os.path.join(hubDirectory, targetVersion, "Editor", "Unity.exe")
            if os.path.isfile(unityPath):
                self._log.info("Using Unity editor for version {0} found at {1}".format(targetVersion, unityPath))
                return unityPath

        self._log.info("Using fallback Unity editor.")
        return "[UnityExePath]"

    def runEditorFunctionRaw(self, projectName: str, platform: ProjectTarget, editorCommand: str, extraArgs: str):

        logPath = self._varMgr.expandPath(UnityLogFileLocation)

        logWatcher = LogWatcher(logPath, self.onUnityLog)
        logWatcher.start()

        os.environ['ModestTreeBuildConfigOverride'] = "FromBuildScript"

        assertThat(self._varMgr.hasKey('UnityExePath'), "Could not find path variable 'UnityExePath'")

        try:
            command = '"[UnityExePath]" -buildTarget {0} -projectPath "[UnityProjectsDir]/{1}/{2}-{3}"'.format(
                self._getBuildTargetArg(platform),
                projectName,
                self._commonSettings.getShortProjectName(projectName),
                PlatformUtil.toPlatformTargetFolderName(platform))

            if editorCommand:
                command += ' -executeMethod ' + editorCommand

            command += ' ' + extraArgs

            self._sys.executeAndWait(command)
        except ProcessErrorCodeException as e:
            raise UnityReturnedErrorCodeException("Error while running Unity!  Command returned with error code.")
        except:
            raise UnityUnknownErrorException("Unknown error occurred while running Unity!")
        finally:
            logWatcher.stop()

            while not logWatcher.isDone:
                time.sleep(0.1)

            os.environ['ModestTreeBuildConfigOverride'] = ""


if __name__ == '__main__':
    pass
