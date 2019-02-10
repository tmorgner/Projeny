import os
import shutil
from cx_Freeze import setup, Executable

ScriptDir = os.path.dirname(os.path.realpath(__file__))
BuildDir = os.path.join(ScriptDir, '../Bin/Build/Bin')
BuildPlatformDir = os.path.join(BuildDir, 'Data')

print("Removing previous build directories...")

if os.path.exists(BuildPlatformDir):
    shutil.rmtree(BuildPlatformDir)

print("Building exes..")
base = None
build_exe_options = {"packages": [], "excludes": [], "build_exe": BuildPlatformDir}
executables = [
    Executable(script="prj/main/Prj.py", base=base, targetName='Prj.exe'),
    Executable(script="prj/main/EditorApi.py", targetName="EditorApi.exe", base=base),
    Executable(script="prj/main/OpenInVisualStudio.py", targetName="OpenInVisualStudio.exe", base=base),
    Executable(script="prj/main/ReleaseManifestUpdater.py", targetName="ReleaseManifestUpdater.exe", base=base)]

setup(name="Projeny",
      version="0.1",
      description="Projeny command line exes",
      options={"build_exe": build_exe_options},
      executables=executables)

print("Build completed successfully")
