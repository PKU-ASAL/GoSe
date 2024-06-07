from GoSe.info.option_type import OptionType
from GoSe.utils.cmdlines import instantiate_arg

class OptionInfo:
    def __init__(self, name, type, value, description, isPosition=False):
        self.name = name
        self.type = type
        self.value = value
        self.description = description
        self.isPosition = isPosition

    def instantiate(self):
        return instantiate_arg(self.name, self.type, self.value, self.isPosition)

    def __str__(self) -> str:
        return f"Option(name={self.name}, type={self.type}, value={self.value}, description={self.description})"

    def __repr__(self) -> str:
        return str(self)

    @staticmethod
    def to_json(self):
        return {
            "name": self.name,
            "type": OptionType.to_string(self.type),
            "value": str(self.value),
            "description": self.description,
            "isPosition": "1" if self.isPosition else "0"
        }
    
    @staticmethod
    def from_json(json_dict):
        return OptionInfo(
            json_dict["name"],
            OptionType.from_string(json_dict["type"]),
            json_dict["value"],
            json_dict["description"],
            True if json_dict["isPosition"] == "1" else False
        )