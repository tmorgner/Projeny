
from string import Template
from typing import List

from mtm.util.Assert import *
from mtm.ioc.Inject import Inject
from mtm.util.SystemHelper import SystemHelper
from prj.main import ProjectConfig
from prj.main.ProjectSchemaLoader import ProjectSchemaLoader
from prj.main.ProjectTarget import ProjectTarget


class UnityEditorMenuGenerator:
    _schemaLoader: ProjectSchemaLoader = Inject('ProjectSchemaLoader')
    _sys: SystemHelper = Inject('SystemHelper')
    _log = Inject('Logger')

    _ChangeProjectMenuClassTemplate = Template(
"""
using UnityEditor;
using Projeny.Internal;

namespace Projeny
{
    public static class ProjenyChangeProjectMenu
    {
        $methods
    }
}
""")

    _changeProjectMethodTemplate = Template("""
        [MenuItem("Projeny/Change Project/$name/$platform", false, 8)]
        public static void ChangeProject$index()
        {
            PrjHelper.ChangeProject("$name", "$platform");
        }
        """
    )
    
    _currentProjectMethodTemplate = Template("""
        [MenuItem("Projeny/Change Project/$name-$platform", true, 8)]
        public static bool ChangeProject${index}Validate()
        {
            return false;
        }
        """
    )

    def Generate(self, currentProjName: str, currentPlatform: ProjectTarget, outputPath: str, allProjectNames: List[str]):
        foundCurrent = False
        methodsText = ""
        projIndex = 1
        for projName in allProjectNames:
            try:
                projConfig: ProjectConfig = self._schemaLoader.loadProjectConfig(projName)
            except Exception as e:
                self._log.warn('Could not load config for project {projName}. It will not show up in editor menu.')
                continue

            for target in projConfig.targets:
                platform = target.ToPath()
                methodsText += self._changeProjectMethodTemplate.substitute(name=projName, platform=platform, index=projIndex)

                if projName == currentProjName and target == currentPlatform:
                    assertThat(not foundCurrent)
                    foundCurrent = True
                    methodsText += self._currentProjectMethodTemplate.substitute(name=projName, platform=platform, index=projIndex)

                projIndex += 1


        #assertThat(foundCurrent, "Could not find project " + currentProjName)
        fileText = self._ChangeProjectMenuClassTemplate.substitute(methods=methodsText)
        # self._log.info(fileText)
        self._sys.writeFileAsText(outputPath, fileText)
