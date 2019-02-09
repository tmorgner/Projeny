
import traceback
import sys
import os
import argparse

import mtm.util.MiscUtil as MiscUtil
from mtm.config.Config import Config
from mtm.util.VarManager import VarManager
from mtm.log.Logger import Logger
from mtm.util.SystemHelper import SystemHelper
from mtm.log.LogStreamFile import LogStreamFile
from mtm.log.LogStreamConsole import LogStreamConsole
from mtm.util.ProcessRunner import ProcessRunner
from mtm.util.ScriptRunner import ScriptRunner
from prj.reg.UnityPackageAnalyzer import UnityPackageAnalyzer

import time


import mtm.util.YamlSerializer as YamlSerializer

from mtm.util.Assert import *

import mtm.ioc.Container as Container
from mtm.ioc.Inject import Inject


# Use TXT to play nicely with MIME types
ReleaseManifestFileName = 'ProjenyReleaseManifest.txt'

class ReleaseManifest:
    def __init__(self):
        self.releases = []

class Runner:
    _scriptRunner = Inject('ScriptRunner')
    _log = Inject('Logger')
    _sys = Inject('SystemHelper')
    _packageAnalyzer = Inject('UnityPackageAnalyzer')

    def __init__(self):
        self._manifest = None

    def run(self, args):
        self._args = args

        self._args.directory = self._sys.canonicalizePath(self._args.directory)
        self._scriptRunner.runWrapper(self._runInternal)

    def _runInternal(self):
        self._log.debug("Started ReleaseManifestUpdater with arguments: {0}".format(" ".join(sys.argv[1:])))

        while True:
            releasePaths = self._getAllReleasePaths()

            self._log.info("Checking for changes...")

            if self._hasChanged(releasePaths):
                self._manifest = self._createManifest(releasePaths)
                self._saveManifest()

                self._log.info("Detected change to one or more releasePaths. Release manifest has been updated.")

            if self._args.pollInternal <= 0:
                break

            time.sleep(self._args.pollInternal)

    def _saveManifest(self):
        yamlStr = YamlSerializer.serialize(self._manifest)
        self._sys.writeFileAsText(os.path.join(self._args.directory, ReleaseManifestFileName), yamlStr)

    def _createManifest(self, releasePaths):
        manifest = ReleaseManifest()
        for path in releasePaths:
            path = self._sys.canonicalizePath(path)

            releaseInfo = self._packageAnalyzer.getReleaseInfoFromUnityPackage(path)

            assertThat(path.startswith(self._args.directory))
            relativePath = path[len(self._args.directory)+1:]
            releaseInfo.localPath = relativePath

            manifest.releases.append(releaseInfo)
        return manifest

    def _hasChanged(self, releasePaths):
        if self._manifest == None:
            return True

        return False

    def _getAllReleasePaths(self):
        releasePath = []
        for filePath in self._sys.findFilesByPattern(self._args.directory, '*.unitypackage'):
            releasePath.append(filePath)
        return releasePath

def addArguments(parser):
    parser.add_argument('directory', metavar='RELEASE_DIRECTORY', type=str, help="The directory to scan for unitypackage files. ")
    parser.add_argument('-pi', '--pollInternal', default=0, metavar='POLL_INTERVAL', type=int, help="This program will scan the given directory for unitypackage files over the polling interval given here (in seconds).  If unspecified, the manifest will only be updated once and this program will exit")

def installBindings():

    #config = {
        #'PathVars': {
            #'LogPath': 'C:/Temp/ProjenyLog.txt',
        #}
    #}
    #Container.bind('Config').toSingle(Config, [config])
    Container.bind('Config').toSingle(Config, [])

    Container.bind('LogStream').toSingle(LogStreamFile)
    Container.bind('LogStream').toSingle(LogStreamConsole, True, False)

    Container.bind('VarManager').toSingle(VarManager)
    Container.bind('SystemHelper').toSingle(SystemHelper)
    Container.bind('Logger').toSingle(Logger)
    Container.bind('ScriptRunner').toSingle(ScriptRunner)
    Container.bind('ProcessRunner').toSingle(ProcessRunner)
    Container.bind('UnityPackageAnalyzer').toSingle(UnityPackageAnalyzer)

def main():
    # Here we split out some functionality into various methods
    # so that other python code can make use of them
    # if they want to extend projeny
    parser = argparse.ArgumentParser(description='Release Manifest Updater')
    addArguments(parser)

    argv = sys.argv[1:]

    args = parser.parse_args(sys.argv[1:])

    installBindings()

    Runner().run(args)

if __name__ == '__main__':

    if (sys.version_info < (3, 0)):
        print('Wrong version of python!  Install python 3 and try again')
        sys.exit(2)

    succeeded = True

    try:
        main()

    except KeyboardInterrupt as e:
        print('Operation aborted by user by hitting CTRL+C')
        succeeded = False

    except Exception as e:
        sys.stderr.write(str(e))

        if not MiscUtil.isRunningAsExe():
            sys.stderr.write('\n' + traceback.format_exc())

        succeeded = False

    if not succeeded:
        sys.exit(1)

