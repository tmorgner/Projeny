from typing import List

from prj.main import PackageConfig


class AssemblyProjectInfo:
    path: str
    root: str
    config: PackageConfig
    dependencies: List[str]

    def __init__(self, path, root, config, dependencies):
        self.path = path
        self.root = root
        self.config = config
        self.dependencies = dependencies
