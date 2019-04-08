import unittest

from mtm.ioc import Container
from mtm.ioc.Inject import Inject
from mtm.log.LogStreamFile import LogStreamFile
from mtm.util import YamlSerializer
from mtm.util.SystemHelper import SystemHelper
from prj.main import EditorApi, Prj
from prj.main.ProjectConfigChanger import ProjectConfigChanger

class TestYaml(unittest.TestCase):
    x = Inject('ProjectSchemaLoader')
    _sys: SystemHelper = Inject('SystemHelper')
    _projectChanger: ProjectConfigChanger = Inject('ProjectConfigChanger')

    @classmethod
    def setUpClass(cls) -> None:
        super().setUpClass()
        Container.clear()
        EditorApi.installBindings("./Projeny.yaml")
        Prj.installPlugins()


    def test_empty(self):
        self.assertEqual("a", "a")

    def test_inject(self):
        self.assertIsNotNone(self.x)

    def test_parseWrite(self):
        originaltext = self._sys.readFileAsText("./UnityProjectsDir/Project/ProjenyProject.expected.yaml")

        projectConfig = self._projectChanger.loadProjectConfig("./Project/")
        text = YamlSerializer.serialize(projectConfig)

        self.assertEqual(originaltext, text)


if __name__ == '__main__':
    unittest.main()
