from typing import List, Any, Union

from mtm.util.Assert import assertThat
from prj.main import PackageData


class CsProjInfo:
    configType: Union[None, str]
    isIgnored: bool
    dependencies: List[Any]
    absPath: str
    id: str
    name: str
    files: List[str]

    def __init__(self, id: str, absPath: str, name: str, files: List[str],
                 isIgnored: bool, configType, projectType: int, packageInfo: PackageData):
        assertThat(name)

        self.id = id
        self.absPath = absPath
        self.name = name
        self.dependencies = []
        self.files = files
        self.isIgnored = isIgnored
        self.configType = configType
        self.projectType = projectType
        self.packageInfo = packageInfo
