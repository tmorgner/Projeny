
from mtm.ioc.Inject import Inject
from mtm.log.Logger import Logger
from mtm.util import PlatformUtil
from mtm.util.SystemHelper import SystemHelper
from mtm.util.UnityHelper import UnityHelper
from prj.main.PackageManager import PackageManager
from prj.main.ProjectTarget import ProjectTarget
from prj.main.VisualStudioHelper import VisualStudioHelper
from prj.main.VisualStudioSolutionGenerator import VisualStudioSolutionGenerator


class ProjenyVisualStudioHelper:
    _vsHelper: VisualStudioHelper = Inject('VisualStudioHelper')
    _vsSolutionGenerator: VisualStudioSolutionGenerator = Inject('VisualStudioSolutionGenerator')
    _log: Logger = Inject('Logger')
    _sys: SystemHelper = Inject('SystemHelper')
    _packageManager: PackageManager = Inject('PackageManager')
    _unityHelper: UnityHelper = Inject('UnityHelper')

    def updateCustomSolution(self, project: str, platform: ProjectTarget):
        self._vsSolutionGenerator.updateVisualStudioSolution(project, platform)

    def openCustomSolution(self, project: str, platform: ProjectTarget, filePath = None):
        self._vsHelper.openVisualStudioSolution(self.getCustomSolutionPath(project, platform), filePath)

    def buildCustomSolution(self, project: str, platform: ProjectTarget):
        solutionPath = self.getCustomSolutionPath(project, platform)

        if not self._sys.fileExists(solutionPath):
            self._log.warn('Could not find generated custom solution.  Generating now.')
            self._vsSolutionGenerator.updateVisualStudioSolution(project, platform)

        with self._log.heading('Building {0}'.format(solutionPath)):
            self._vsHelper.buildVisualStudioProject(solutionPath, 'Debug')

    def getCustomSolutionPath(self, project: str, platform: ProjectTarget):
        path = PlatformUtil.toPlatformTargetFolderName(platform)
        return '[UnityProjectsDir]/{0}/{0}-{1}.sln'.format(project, path)

    def updateUnitySolution(self, projectName: str, platform: ProjectTarget):
        """
        Simply runs unity and then generates the monodevelop solution file using an editor script
        This is used when generating the Visual Studio Solution to get DLL references and defines etc.
        """
        with self._log.heading('Updating unity generated solution for project {0} ({1})'.format(projectName, platform.ToName())):
            self._packageManager.checkProjectInitialized(projectName, platform)

            # This will generate the unity csproj files which we need to generate Modest3d.sln correctly
            # It's also necessary to run this first on clean checkouts to initialize unity properly
            self._unityHelper.runEditorFunction(projectName, platform, 'Projeny.ProjenyEditorUtil.ForceGenerateUnitySolution')


