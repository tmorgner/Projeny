from typing import List, Any

from prj.main.RefInfo import RefInfo


class UnityGeneratedProjInfo:
    referencesEditor: List[Any]
    references: List[Any]
    defines: List[str]

    def __init__(self, defines: List[str], references: List[RefInfo], referencesEditor: List[RefInfo]):
        self.defines = defines
        self.references = references
        self.referencesEditor = referencesEditor
