from enum import Enum

class OptionType(Enum):
    Boolean = 1
    Integer = 2
    String = 3
    # If the path needs to point to a folder, define its value as "FOLDER"
    Path = 4
    Range = 5
    URL = 6

    @staticmethod
    def from_string(s):
        if s == 'Boolean':
            return OptionType.Boolean
        elif s == 'Integer':
            return OptionType.Integer
        elif s == 'String':
            return OptionType.String
        elif s == 'Path':
            return OptionType.Path
        elif s == 'Range':
            return OptionType.Range
        elif s == 'URL':
            return OptionType.URL
        else:
            assert False, "Unknown option type: {}".format(s)
    
    @staticmethod
    def to_string(t):
        if t == OptionType.Boolean:
            return 'Boolean'
        elif t == OptionType.Integer:
            return 'Integer'
        elif t == OptionType.String:
            return 'String'
        elif t == OptionType.Path:
            return 'Path'
        elif t == OptionType.Range:
            return 'Range'
        elif t == OptionType.URL:
            return 'URL'
        else:
            assert False, "Unknown option type: {}".format(t)