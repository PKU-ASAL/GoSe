from GoSe.info.option_info import OptionInfo
from GoSe.info.option_type import OptionType
from GoSe.utils.cmdlines import instantiate_arg

class OPFTVertex:
    def __init__(self, optinInfo: OptionInfo = None):
        if optinInfo is None:
            self.optionName = None
            self.optionType = None
            self.optionValue = None
            self.optionIsPosition = False
        else:
            self.optionName = optinInfo.name
            self.optionType = optinInfo.type
            self.optionValue = optinInfo.value
            self.optionIsPosition = optinInfo.isPosition

    def __str__(self) -> str:
        return f"{self.optionName} ({self.optionType}) {self.optionValue} {'(pos)' if self.optionIsPosition else ''}"

    def __repr__(self) -> str:
        return str(self)

    def instantiate(self):
        return instantiate_arg(self.optionName, self.optionType, self.optionValue, self.optionIsPosition)

    @staticmethod
    def to_json(self):
        return {
            "optionName": self.optionName,
            "optionType": OptionType.to_string(self.optionType),
            "optionValue": str(self.optionValue),
            "optionIsPosition": "1" if self.optionIsPosition else "0"
        }

    @staticmethod
    def from_json(json_dict):
        vertex = OPFTVertex()
        vertex.optionName = json_dict["optionName"]
        vertex.optionType = OptionType.from_string(json_dict["optionType"])
        vertex.optionValue = json_dict["optionValue"]
        vertex.optionIsPosition = True if json_dict["optionIsPosition"] == "1" else False
        return vertex
