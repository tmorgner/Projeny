from typing import Union

from mtm.ioc.Inject import Inject
import mtm.util.MiscUtil as MiscUtil
from mtm.log.Logger import Logger

from mtm.util.CommonSettings import ConfigFileName

import win32api
import win32com.client

from mtm.util.Assert import *
from mtm.util.SystemHelper import SystemHelper
from mtm.util.VarManager import VarManager


class VisualStudioHelper:
    _log: Logger = Inject('Logger')
    _config = Inject('Config')
    _varMgr: VarManager = Inject('VarManager')
    _sys: SystemHelper = Inject('SystemHelper')

    def openFile(self, filePath: str, lineNo: int, solutionPath: str):
        if not lineNo or lineNo <= 0:
            lineNo = 1

        if MiscUtil.doesProcessExist('^devenv\.exe$'):
            self.openFileInExistingVisualStudioInstance(filePath, lineNo)

            # This works too but doesn't allow going to a specific line
            #self._sys.executeNoWait('[VisualStudioCommandLinePath] /edit "{0}"'.format(filePath))
        else:
            # Unfortunately, in this case we can't pass in the line number
            self.openVisualStudioSolution(solutionPath, filePath)

    def openFileInExistingVisualStudioInstance(self, filePath: str, lineNo: int):
        try:
            vsPath = self._varMgr.expand('[VisualStudioIdePath]')

            if '2017' in vsPath or 'Visual Studio 15.0' in vsPath:
                dte = win32com.client.GetActiveObject("VisualStudio.DTE.15.0")
            elif 'Visual Studio 14.0' in vsPath:
                dte = win32com.client.GetActiveObject("VisualStudio.DTE.14.0")
            elif 'Visual Studio 12.0' in vsPath:
                dte = win32com.client.GetActiveObject("VisualStudio.DTE.12.0")
            else:
                assertThat(False, "Could not determine visual studio version")
                return

            # noinspection PyStatementEffect
            dte.MainWindow.Activate
            dte.ItemOperations.OpenFile(self._sys.canonicalizePath(filePath))
            dte.ActiveDocument.Selection.MoveToLineAndOffset(lineNo, 1)
        except Exception as error:
            raise Exception("COM Error.  This is often triggered when given a bad line number. Details: {0}".format(win32api.FormatMessage(error.excepinfo[5])))

    def openVisualStudioSolution(self, solutionPath: str, filePath: Union[str,None] = None):

        if self._varMgr.hasKey('VisualStudioIdePath'):
            assertThat(self._sys.fileExists('[VisualStudioIdePath]'),
               "Cannot find path to visual studio.  Expected to find it at '{0}'".format(self._varMgr.expand('[VisualStudioIdePath]')))

            if solutionPath is None:
                self._sys.executeNoWait('"[VisualStudioIdePath]" {0}'.format(self._sys.canonicalizePath(filePath) if filePath else ""))
            else:
                solutionPath = self._sys.canonicalizePath(solutionPath)
                self._sys.executeNoWait('"[VisualStudioIdePath]" {0} {1}'.format(solutionPath, self._sys.canonicalizePath(filePath) if filePath else ""))
        else:
            assertThat(filePath is None,
               "Path to visual studio has not been defined.  Please set <VisualStudioIdePath> within one of your {0} files.  See documentation for details.", ConfigFileName)
            self._sys.executeShellCommand(solutionPath, None, False)

    def buildVisualStudioProject(self, solutionPath: str, buildConfig: str):
        solutionPath = self._varMgr.expand(solutionPath)
        if self._config.getBool('Compilation', 'UseDevenv'):
            buildCommand = '"[VisualStudioCommandLinePath]" {0} /build "{1}"'.format(solutionPath, buildConfig)
        else:
            buildCommand = '"[MsBuildExePath]"'
            #if rebuild:
                #buildCommand += ' /t:Rebuild'
            buildCommand += ' /p:Configuration="{0}" "{1}"'.format(buildConfig, solutionPath)

        self._sys.executeAndWait(buildCommand)



