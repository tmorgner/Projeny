using System;
using System.Collections;
using System.Collections.Generic;
using System.Diagnostics;
using System.IO;
using System.Linq;
using System.Text;
using UnityEditor;
using UnityEditor.Callbacks;
using UnityEditorInternal;
using UnityEngine;
using Projeny.Internal;

namespace Projeny
{
    public enum ProjectConfigTypes
    {
        LocalProject,
        LocalProjectUser,
        AllProjects,
        AllProjectsUser,
    }

    public static class ProjenyEditorUtil
    {
        public const string ConfigFileName = "Projeny.yaml";

        public const string ProjectConfigFileName = "ProjenyProject.yaml";
        public const string ProjectConfigUserFileName = "ProjenyProjectCustom.yaml";

        public const string PackageConfigFileName = "ProjenyPackage.yaml";

        public static string GetCurrentProjectName()
        {
            return GetCurrentProjectInfo().ProjectName;
        }

        public static ProjectTarget GetCurrentPlatformDirName()
        {
            return GetCurrentProjectInfo().ProjectTarget;
        }

        public static string GetProjectConfigPath(ProjectConfigTypes configType)
        {
            var projectRootDir = Path.Combine(Application.dataPath, "../..");
            var unityProjectsDir = Path.Combine(projectRootDir, "..");

            switch (configType)
            {
                case ProjectConfigTypes.LocalProject:
                {
                    return Path.Combine(projectRootDir, ProjenyEditorUtil.ProjectConfigFileName);
                }
                case ProjectConfigTypes.LocalProjectUser:
                {
                    return Path.Combine(projectRootDir, ProjenyEditorUtil.ProjectConfigUserFileName);
                }
                case ProjectConfigTypes.AllProjects:
                {
                    return Path.Combine(unityProjectsDir, ProjenyEditorUtil.ProjectConfigFileName);
                }
                case ProjectConfigTypes.AllProjectsUser:
                {
                    return Path.Combine(unityProjectsDir, ProjenyEditorUtil.ProjectConfigUserFileName);
                }
            }

            return null;
        }

        public static void ForceGenerateUnitySolution()
        {
            if (UnityEditorInternal.InternalEditorUtility.inBatchMode)
            {
                // This is called by the build script to generate the monodevelop solution
                // because it uses that when generating its own custom solution
                EditorApplication.ExecuteMenuItem("Assets/Open C# Project");
            }
            else
            {
                // Unfortunately we can't use the above method when not in batch mode,
                // because then it will always open up visual studio/monodevelop
                // This works though - let's just hope Unity maintains support for this
                System.Type T = System.Type.GetType("UnityEditor.SyncVS,UnityEditor");
                System.Reflection.MethodInfo SyncSolution = T.GetMethod("SyncSolution", System.Reflection.BindingFlags.Public | System.Reflection.BindingFlags.Static);
                SyncSolution.Invoke(null, null);
            }
        }

        public static ProjectInfo GetCurrentProjectInfo()
        {
            var info = new ProjectInfo();

            var projectPlatformRootPath = Path.GetFullPath(Path.Combine(Application.dataPath, ".."));
            var projectRootPath = Path.GetFullPath(Path.Combine(projectPlatformRootPath, ".."));

            info.ProjectName = Path.GetFileName(projectRootPath);

            var projectAndPlatform = Path.GetFileName(projectPlatformRootPath);
            if (projectAndPlatform.StartsWith(info.ProjectName))
            {
                var platformAndTarget = projectAndPlatform.Substring(info.ProjectName.Length + 1);
                info.ProjectTarget = ParseProjectTarget(platformAndTarget);
            }
            else
            {
                UnityEngine.Debug.LogError("Unexpected project structure. Project sub directories should start with the project name as prefix.");
                info.ProjectTarget = new ProjectTarget()
                {
                    Target = projectAndPlatform.Substring(projectAndPlatform.LastIndexOf("-") + 1),
                    Tag = null
                };
            }

            return info;
        }

        public static ProjectTarget ParseProjectTarget(string platformAndTarget)
        {
            var platformAndTargetSplit = platformAndTarget.IndexOf('-');
            if (platformAndTargetSplit < 0)
            {
                return new ProjectTarget()
                {
                    Tag = null,
                    Target = platformAndTarget
                };
            }
            else
            {
                return new ProjectTarget()
                {
                    Tag = platformAndTarget.Substring(platformAndTargetSplit + 1),
                    Target = platformAndTarget.Substring(0, platformAndTargetSplit)
                };
            }
        }

        // NOTE: This needs to stay in sync with BuildUtil.py
        public static BuildTarget ParseBuildTarget(string platformShortStr)
        {
            switch (platformShortStr.ToLower())
            {
                case "windows":
                {
                    return BuildTarget.StandaloneWindows;
                }
                case "android":
                {
                    return BuildTarget.Android;
                }
                case "webgl":
                {
                    return BuildTarget.WebGL;
                }
                case "osx":
                {
                    return BuildTarget.StandaloneOSXUniversal;
                }
                case "ios":
                {
                    return BuildTarget.iOS;
                }
                case "linux":
                {
                    return BuildTarget.StandaloneLinux;
                }
                case "uwp":
                {
                    return BuildTarget.WSAPlayer;
                }
                case "lumin":
                {
                    try
                    {
                        return (BuildTarget)Enum.Parse(typeof(BuildTarget), "Lumin");
                    }
                    catch (ArgumentException)
                    {
                        throw new NotImplementedException("Platform not availalble");
                    }
                }
            }

            throw new NotImplementedException();
        }

        public class ProjectInfo
        {
            public ProjectTarget ProjectTarget;
            public string ProjectName;
        }
    }
}

