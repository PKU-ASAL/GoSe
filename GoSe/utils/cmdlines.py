from GoSe.info.option_type import OptionType
import json
import os
import random
import time
from xeger import Xeger

FILE_DICT = {
    "md": ["sample.md"],
    "pdf": ["paper.pdf"],
    "jpeg": ["shuttle.jpeg"],
    "jpg": ["photo.jpg"],
    "png": ["photo.png"],
    "tiff": ["sample.tiff"],
    "wav": ["sample-3s.wav"],
    "mp4": ["sample-3s.mp4"],
    "elf": ["cmark"],
    "xml": ["sample.xml"],
    "xml2": ["sample.xml", "sample.md"],
    "spx": ["sample.spx"],
    "targa": ["shuttle.tga"],
    "pcap": ["sample.pcap"],
    "cache": ["sample.cache"],
    "pem": ["test.pem"],
    "xz": ["d.xz"],
    "number": ["d"],
    "config": ["sample.conf"],
    "FILE": ["a", "b", "c", "cmark", "d", "f/f", "sample.md", "photo.jpg", "shuttle.jpeg", "photo.png", "sample.tiff", "sample-3s.wav", "sample.xml"],
    "FOLDER": [".", "e", "f"],
    "default": ["a", "b", "c", "cmark", "d", "f/f", "sample.md", "photo.jpg", "shuttle.jpeg", "photo.png", "sample.tiff", "sample-3s.wav", "sample.xml"],
    "output": ["a"],
    "all": ["a", "b", "c", "cmark", "d", "e", "f", "f/f", "sample.md", "photo.jpg", "shuttle.jpeg", "photo.png", "sample.tiff", "sample-3s.wav", "sample.xml", "sample.spx", "shuttle.tga", "sample.pcap", "sample.cache", "test.pem", "d.xz"]
}

def instantiate_arg(name, type, value, isPosition):
    if isPosition:
        name = ""
        concat_symbol = ""
    else:
        concat_symbol = " "
    if type == OptionType.Boolean:
        return name
    elif type == OptionType.String:
        try:
            assert value is not None and value != "None"
            assert not value.startswith(".") and not value.startswith("^."), "disable arbitrary string"
            assert not value.startswith("\".") and not value.startswith("\"^."), "disable arbitrary string"
            value = Xeger().xeger(value)
        except Exception as e:
            random_strings = ["a", "default", "true", "0", "32", "."]
            random_string = random.choice(random_strings)
            value = random_string
        return name + concat_symbol + value
    elif type == OptionType.Path:
        if value:
            value = instantiate_path("/tmp/sandbox", "@@@" + value, "@@@", "")
        else:
            value = "/tmp/sandbox/a"
        return name + concat_symbol + value
    elif type == OptionType.Range:
        # value is a string like "[0, 16, 'INT']"
        if isinstance(value, str):
            value = json.loads(value)
        assert isinstance(value, list) and len(value) == 3, "Invalid range: {}".format(value)
        if value[2] == "INT":
            value = str(random.randint(value[0], value[1]))
        elif value[2] == "FLOAT":
            value = str(random.uniform(value[0], value[1]))
        else:
            assert False, "Unknown range type: {}".format(value[2])
        return name + concat_symbol + value
    elif type == OptionType.Integer:
        return name + concat_symbol + str(random.randint(0, 100))
    elif type == OptionType.URL:
        return name + concat_symbol + "http://127.0.0.1:9000"
    else:
        assert False, "Not implemented yet: {}".format(type)

def sequence_to_optionlist(name_to_oinfo, sequence, mutation=False) -> "list[str]":
    if mutation:
        # add random alphanumeric characters to the end of the option
        return [name_to_oinfo[x].instantiate() + "".join(random.choices("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789", k=random.randint(0, 1))) for x in sequence]
    else:
        optionlist = []
        for x in sequence:
            if x in name_to_oinfo:
                optionlist.append(name_to_oinfo[x].instantiate())
            else:
                optionlist.append(x)
        return optionlist

def optionlist_to_cmdline(clo_info, option_list: "list[str]", add_pos_arg=True, mutation=False) -> str:
    assert clo_info is not None and option_list is not None
    assert type(option_list) == list
    cmdline_pattern = random.choice(clo_info.posPatterns)
    # add default @OPTION
    if not "@OPTION" in cmdline_pattern:
        cmdline_pattern = "@OPTION " + cmdline_pattern
    # instantiate mapping
    placeholder_map = {}
    placeholder_map["OPTION"] = []
    # check option list is fully instantiated
    for option in option_list:
        if option.startswith("@@@"):
            option = instantiate_path("/tmp/sandbox", option, "@@@", "", mutation=mutation)
        elif option.startswith("@@$"):
            option = instantiate_path("/tmp/sandbox", option, "@@$", "", mutation=mutation)
        placeholder_map["OPTION"].append(option)
    placeholder_map["OPTION"] = " ".join(placeholder_map["OPTION"])
    for option in clo_info.posOptions:
        assert option.name not in placeholder_map, "Positional argument is already instantiated: {}".format(option.name)
        placeholder_map[option.name] = option.instantiate() if add_pos_arg else ""
    cmdline = ""
    for item in cmdline_pattern.split():
        if item[0] == '@':
            assert item[1:] in placeholder_map, "Invalid placeholder: {}\ncmdline_pattern: {}".format(item, cmdline_pattern)
            cmdline += placeholder_map[item[1:]] + " "
        else:
            cmdline += item + " "
    return cmdline

def instantiate_path(sandbox_path, arg, old_symbol, new_symbol, ignore_folder_prefix=False, mutation=False):
    if not old_symbol in arg:
        return arg
    file_type = arg.split(old_symbol)[1].split(" ")[0].strip(' \"()\n')
    if mutation:
        file_type = "all"
        path = os.path.join(sandbox_path, random.choice(FILE_DICT[file_type]))
    elif file_type.startswith("/tmp/sandbox/"):
        path = file_type.replace("/tmp/sandbox/", sandbox_path + "/")
    else:
        if "|" in file_type:
            file_type = file_type.split("|")[0].strip()
        if not file_type in FILE_DICT:
            if file_type != "None" and file_type != "foo" and file_type != "gitignore":
                print(f"Invalid file type: {file_type}\nChange to default.")
            file_type = "default"
        if ignore_folder_prefix and file_type == "FOLDER":
            new_symbol = ""
        path = os.path.join(sandbox_path, random.choice(FILE_DICT[file_type]))
    # check if the path exists
    assert os.path.exists(path), "Path not exists: {}".format(path)
    rel_path = os.path.relpath(path, sandbox_path)
    assert not rel_path.startswith('..'), "Path is not in the sandbox: {}".format(path)
    return arg.split(old_symbol)[0] + new_symbol + path + " " + " ".join(arg.split(old_symbol)[1].split(" ")[1:])

def record_timestamp(seed_list, enable=True):
    if enable:
        ts = time.time()
        return (ts, seed_list)
    else:
        return seed_list