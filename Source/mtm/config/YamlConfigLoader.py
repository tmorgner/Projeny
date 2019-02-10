
import os
import yaml

from mtm.util.Assert import *


def loadYamlFilesThatExist(*paths):
    configs = []

    for path in paths:
        if os.path.isfile(path):
            print("Loading configuration file " + path)
            config = loadYamlFile(path)

            if config is not None:
                configs.append(config)

    return configs


def loadYamlFile(path):
    return yaml.load(readAllTextFromFile(path))


def readAllTextFromFile(filePath):
    with open(filePath, 'r', encoding='utf-8') as f:
        return f.read()

