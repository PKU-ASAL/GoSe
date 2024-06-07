from GoSe.info.option_info import OptionInfo
import GoSe.utils.log
import logging
import os

class CLOInfo:
    def __init__(self, progPath: str, progGcovDir: str = None, covPort: int = 12321):
        self.progPath = progPath
        self.progName = os.path.basename(progPath)
        self.progGcovDir = os.path.dirname(progPath) if progGcovDir is None else progGcovDir
        self.covPort = covPort
        # groups: groupName -> [OptionInfo1, OptionInfo2, ...]
        self.groups = {}
        self.posOptions = []
        self.posPatterns = []
        self.instantiatedPosOptions = []

    def __str__(self) -> str:
        pstr = "program path: {}, program name: {}, program gcov directory: {}"\
               .format(self.progPath, self.progName, self.progGcovDir)
        gstr = ""
        for groupName, groupOptionList in self.groups.items():
            gstr += "group '{}': [{}]\n".format(groupName, ", ".join([str(option) for option in groupOptionList]))
        return pstr + gstr

    def __repr__(self) -> str:
        return str(self)
    
    def get_gcov_dir(self):
        return self.progGcovDir
    
    def get_cov_port(self):
        return self.covPort
    
    def get_prog_path(self):
        return self.progPath

    def addGroup(self, groupName: str):
        if groupName in self.groups:
            return
        self.groups[groupName] = []

    def getGroup(self, groupName: str) -> "list[OptionInfo]":
        if groupName not in self.groups:
            return None
        return self.groups[groupName]

    def addRawOption(self, groupName, name, type, value=None, description=''):
        logging.debug("add raw option to group={}: name={}, type={}, value={}, desc={}"\
                      .format(groupName, name, type, value, description))
        option = OptionInfo(name, type, value, description)
        self.addOption(groupName, option)

    def addOption(self, groupName: str, option: OptionInfo):
        self.addGroup(groupName)
        group = self.getGroup(groupName)
        assert group is not None, "Group {} not exists.".format(groupName)
        group.append(option)

    def getAllOptions(self) -> "list[OptionInfo]":
        options = []
        for groupName, groupOptions in self.groups.items():
            options.extend(groupOptions)
        return options
    
    def addRawPosOption(self, name, type, value=None, description=''):
        logging.debug("add raw positional option: name={}, type={}, value={}, desc={}"\
                      .format(name, type, value, description))
        option = OptionInfo(name, type, value, description, isPosition=True)
        self.addPosOption(option)

    def addPosOption(self, option: OptionInfo):
        self.posOptions.append(option)
        self.instantiatedPosOptions.append(option.instantiate())
        assert len(self.posOptions) == len(self.instantiatedPosOptions), "{}\n{}".format(self.posOptions, self.instantiatedPosOptions)