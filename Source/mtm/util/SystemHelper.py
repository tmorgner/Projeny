from distutils.dir_util import copy_tree

from mtm.log.Logger import Logger
from mtm.util.VarManager import VarManager
from mtm.util.ProcessRunner import ProcessRunner
from mtm.util.ProcessRunner import ResultType

import string
import fnmatch
from mtm.util.Assert import *
import mtm.ioc.Container as Container
from mtm.ioc.Inject import Inject
from mtm.ioc.Inject import InjectOptional
import mtm.util.JunctionUtil as JunctionUtil

import time
import os
import shlex
import subprocess
import shutil
import stat
import platform
from glob import glob

class ProcessErrorCodeException(Exception):
    pass

class ProcessTimeoutException(Exception):
    pass

class SystemHelper:
    '''Responsibilities:
        - Miscellaneous file-handling/path-related operations
        - Wrapper to execute arbitrary commands
    '''
    _varManager = Inject('VarManager')
    _log = Inject('Logger')
    _processRunner = Inject('ProcessRunner')

    # Use an hour timeout
    def __init__(self, timeout = 60 * 60):
        self._timeout = timeout

    def canonicalizePath(self, pathStr):
        # Make one standard representation of the given path
        # This will remove ..\ and also change to always use back slashes since this is what os.path.join etc. uses
        return self._varManager.expandPath(pathStr)

    def executeAndWait(self, commandStr, startDir = None):
        expandedStr = self._varManager.expand(commandStr)

        self._log.debug("Executing '%s'" % expandedStr)

        vals = self._splitCommandStr(expandedStr)

        if startDir != None:
            startDir = self._varManager.expand(startDir)

        result = self._processRunner.waitForProcessOrTimeout(vals, self._timeout, startDir)

        if result == ResultType.Error:
            raise ProcessErrorCodeException('Command returned with error code while executing: %s' % expandedStr)

        if result == ResultType.TimedOut:
            raise ProcessTimeoutException('Timed out while waiting for command: %s' % expandedStr)

        assertThat(result == ResultType.Success)

    def executeNoWait(self, commandStr, startDir = None):
        expandedStr = self._varManager.expand(commandStr)

        self._log.debug("Executing '{0}'".format(expandedStr))

        vals = self._splitCommandStr(expandedStr)

        if startDir != None:
            startDir = self._varManager.expand(startDir)

        self._processRunner.execNoWait(vals, startDir)

    # This is only used to execute shell-specific commands like copy, mklink, etc.
    def executeShellCommand(self, commandStr, startDir = None, wait = True):
        expandedStr = self._varManager.expand(commandStr)

        self._log.debug("Executing '%s'" % expandedStr)

        if startDir != None:
            startDir = self._varManager.expand(startDir)

        result = self._processRunner.execShellCommand(expandedStr, startDir, wait)

        if result == ResultType.Error:
            raise ProcessErrorCodeException('Command returned with error code while executing: %s' % expandedStr)

        assertThat(result == ResultType.Success, "Expected success result but found '{0}'".format(result))

    def _splitCommandStr(self, commandStr):
        # Hacky but necessary since shlex.split will otherwise remove our backslashes
        if platform.platform().startswith('Windows'):
            commandStr = commandStr.replace(os.sep, os.sep + os.sep)

        # Convert command to argument list to avoid issues with escape characters, etc.
        # Based on an answer here: http://stackoverflow.com/questions/12081970/python-using-quotes-in-the-subprocess-popen
        return shlex.split(commandStr)

    def executeAndReturnOutput(self, commandStr):
        self._log.debug("Executing '%s'" % commandStr)
        return subprocess.getoutput(self._splitCommandStr(commandStr)).strip()

    def walkDir(self, dirPath):
        dirPath = self._varManager.expand(dirPath)
        return os.listdir(dirPath)

    def getParentDirectoriesWithSelf(self, path):
        yield path

        for parentDir in self.getParentDirectories(path):
            yield parentDir

    def getParentDirectories(self, path):
        path = self._varManager.expand(path)

        lastParentDir = None
        parentDir = os.path.dirname(path)

        while parentDir and parentDir != lastParentDir:
            yield parentDir

            lastParentDir = parentDir
            parentDir = os.path.dirname(parentDir)

    def createDirectory(self, dirPath):
        dirPath = self._varManager.expand(dirPath)
        try:
            os.makedirs(dirPath)
        except:
            pass

    def convertToValidFileName(self, s):
        """Take a string and return a valid filename constructed from the string.
    Uses a whitelist approach: any characters not present in valid_chars are
    removed.

    Note: this method may still produce invalid filenames such as ``, `.` or `..`
    """
        valid_chars = "-_.() %s%s" % (string.ascii_letters, string.digits)
        filename = ''.join(c for c in s if c in valid_chars)
        return filename

    def makeMissingDirectoriesInPath(self, dirPath):
        dirPath = self._varManager.expand(dirPath)
        self._log.debug("Making missing directories in path '{0}'".format(dirPath))
        try:
            os.makedirs(os.path.dirname(dirPath))
        except:
            pass

    def copyFile(self, fromPath, toPath):
        toPath = self._varManager.expand(toPath)
        fromPath = self._varManager.expand(fromPath)

        self.makeMissingDirectoriesInPath(toPath)
        shutil.copy2(fromPath, toPath)
        os.chmod(toPath, stat.S_IWRITE)

    def IsDir(self, path):
        return os.path.isdir(self._varManager.expand(path))

    def clearDirectoryContents(self, dirPath):
        dirPath = self._varManager.expand(dirPath)
        for fileName in os.listdir(dirPath):
            filePath = os.path.join(dirPath, fileName)
            if os.path.isfile(filePath):
                os.unlink(filePath)
            elif os.path.isdir(filePath):
                shutil.rmtree(filePath)

    def deleteDirectoryWaitIfNecessary(self, dirPath):
        dirPath = self._varManager.expand(dirPath)

        if not os.path.isdir(dirPath):
            # Already removed
            return

        attemptsLeft = 10

        while True:
            try:
                shutil.rmtree(dirPath)
            except Exception as e:
                self._log.warn('Could not delete directory at "{0}".  Waiting to try again...'.format(dirPath))
                time.sleep(5)
                attemptsLeft -= 1

                if attemptsLeft < 0:
                    raise e
                continue
            break

    def deleteDirectory(self, dirPath):
        dirPath = self._varManager.expand(dirPath)
        shutil.rmtree(dirPath)

    def deleteAndReCreateDirectory(self, dirPath):
        self.deleteDirectoryIfExists(dirPath)
        self.createDirectory(dirPath)

    def deleteDirectoryIfExists(self, dirPath):
        dirPath = self._varManager.expand(dirPath)

        if os.path.exists(dirPath):
            shutil.rmtree(dirPath)
            return True

        return False

    def getFileExtension(self, path):
        path = self._varManager.expandPath(path)
        return os.path.splitext(path)[1]

    def getFileNameWithoutExtension(self, path):
        return os.path.basename(os.path.splitext(path)[0])

    def deleteEmptyDirectoriesUnder(self, dirPath):
        dirPath = self._varManager.expandPath(dirPath)

        if not os.path.isdir(dirPath):
            return 0

        # Can't process long paths on windows
        if len(dirPath) >= 256:
            return 0

        if JunctionUtil.islink(dirPath):
            # Do not recurse down directory junctions
            return 0

        files = os.listdir(dirPath)

        numDirsDeleted = 0

        for fileName in files:
            fullpath = os.path.join(dirPath, fileName)

            if os.path.isdir(fullpath):
                numDirsDeleted += self.deleteEmptyDirectoriesUnder(fullpath)

        files = os.listdir(dirPath)

        if len(files) == 0:
            self._log.debug("Removing empty folder '%s'" % dirPath)
            os.rmdir(dirPath)
            numDirsDeleted += 1

            metaFilePath = dirPath + '/../' + os.path.basename(dirPath) + '.meta'

            if os.path.isfile(metaFilePath):
                self._log.debug("Removing meta file '%s'" % metaFilePath)
                os.remove(metaFilePath)

        return numDirsDeleted

    def fileExists(self, path):
        return os.path.isfile(self._varManager.expand(path))

    def directoryExists(self, dirPath):
        return os.path.exists(self._varManager.expand(dirPath))

    def copyDirectory(self, fromPath, toPath):
        fromPath = self._varManager.expand(fromPath)
        toPath = self._varManager.expand(toPath)

        self._log.debug("Copying directory '{0}' to '{1}'".format(fromPath, toPath))

        copy_tree(fromPath, toPath)
        for root, dirs, files in os.walk(toPath):
            for file in files:
                os.chmod(os.path.join(root, file), stat.S_IWRITE)

    def readFileLines(self, path):
        with self.openInputFile(path) as f:
            return f.readlines()

    def readFileAsText(self, path):
        with self.openInputFile(path) as f:
            return f.read()

    def writeFileLines(self, path, lines):
        with self.openOutputFile(path) as f:
            f.writelines(lines)

    def writeFileAsText(self, path, text):
        with self.openOutputFile(path) as f:
            f.write(text)

    def openOutputFile(self, path):
        path = self._varManager.expand(path)
        self.makeMissingDirectoriesInPath(path)
        return open(path, 'w', encoding='utf-8', errors='ignore')

    def openInputFile(self, path):
        return open(self._varManager.expand(path), 'r', encoding='utf-8', errors='ignore')

    def removeFile(self, fileName):
        os.remove(self._varManager.expand(fileName))

    def removeFileIfExists(self, fileName):
        fullPath = self._varManager.expand(fileName)

        if os.path.isfile(fullPath):
            os.remove(fullPath)
            return True

        return False

    def getAllDirectoriesRecursive(self, startDir):
        startDir = self._varManager.expand(startDir)

        for root, dirs, files in os.walk(startDir):
            for basename in dirs:
                yield os.path.join(root, basename)

    def getAllFilesInDirectory(self, dirPath):
        dirPath = self._varManager.expand(dirPath)
        return [fileName for fileName in os.listdir(dirPath) if os.path.isfile(os.path.join(dirPath, fileName))]

    def getAllDirectoriesInDirectory(self, dirPath):
        dirPath = self._varManager.expand(dirPath)
        return [fileName for fileName in os.listdir(dirPath) if os.path.isdir(os.path.join(dirPath, fileName))]

    def getAllFilesRecursive(self, startDir):
        startDir = self._varManager.expand(startDir)

        for root, dirs, files in os.walk(startDir):
            for basename in files:
                yield os.path.join(root, basename)

    def findFilesByPattern(self, startDir, pattern):
        for filePath in self.getAllFilesRecursive(startDir):
            basename = os.path.basename(filePath)
            if fnmatch.fnmatch(basename, pattern):
                yield filePath

    def renameFile(self, currentName, newName):
        os.rename(self._varManager.expand(currentName), self._varManager.expand(newName))

    def removeFileWaitIfNecessary(self, fileName):
        outputPath = self._varManager.expand(fileName)

        if not os.path.isfile(outputPath):
            # File already removed
            return

        while True:
            try:
                os.remove(outputPath)
            except OSError:
                self._log.warn('Could not delete file at "{0}".  Waiting to try again...'.format(outputPath))
                time.sleep(5)
                continue
            break

    def removeByRegex(self, regex):
        regex = self._varManager.expand(regex)
        count = 0

        for filePath in glob(regex):
            os.unlink(filePath)
            count += 1

        self._log.debug("Removed %s files matching '%s'" % (count, regex))
