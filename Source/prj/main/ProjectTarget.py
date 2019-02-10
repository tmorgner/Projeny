
class ProjectTarget:
    target: str
    tag: str

    def __init__(self, target: str, tag: str=None):
        self.target = target
        self.tag = tag

    def ToPath(self):
        if self.tag is None or self.tag == "":
            return self.target
        else:
            return self.target + "-" + self.tag

    def ToName(self):
        if self.tag is None or self.tag == "":
            return self.target
        else:
            return self.target + "; " + self.tag

    def __eq__(self, other):
        return self.__dict__ == other.__dict__
