from GoSe.info.option_type import OptionType
import json
import os
import pandas as pd

csv_file = "tests/real_programs/real_programs.csv"

def read_real_program_list():
    with open(csv_file, "r") as f:
        program_list = f.readlines()
    program_list = [x.strip().split(",") for x in program_list[1:]]
    result = []
    for program_name,program_path,program_gcov_dir,program_src_path,program_manual_path in program_list:
        if not program_name or program_name.startswith("#"):
            continue
        result.append((program_name, program_path, program_gcov_dir, program_src_path, program_manual_path))
    return result

def read_option_info_file(filepath):
    # check the filepath
    if not os.path.exists(filepath):
        print("Option info file does not exist.".format(filepath))
        return None
    try:
        df = pd.read_csv(filepath, sep='##', engine='python')
        df.fillna('', inplace=True)
        two_d_list = df.values.tolist()
        dict_list = []
        attr_names = ['groupName', 'name', 'type', 'value', 'description']
        for l in two_d_list:
            assert len(l) == len(attr_names), "The number of columns in the file does not match the number of attributes."
            d = dict()
            for i, value in enumerate(l):
                d[attr_names[i]] = value
            dict_list.append(d)
        # replace string 'None' in col 'value' with None
        for d in dict_list:
            if d['value'] == 'None':
                d['value'] = None
            d['type'] = OptionType.from_string(d['type'])
        return dict_list
    except Exception as e:
        print("Cannot open or read file: {}".format(filepath))
        print("Error message: {}".format(e))
        assert False

def append_cov(result_file, program_name, tool_name, cov):
    # json format
    result = {}
    if os.path.exists(result_file):
        with open(result_file, "r") as f:
            result = json.loads(f.read())
    if program_name not in result:
        result[program_name] = {}
    if tool_name not in result[program_name]:
        result[program_name][tool_name] = []
    result[program_name][tool_name].append(cov)
    with open(result_file, "w") as f:
        f.write(json.dumps(result, indent=4))

# delete collect_cov.lock in gcov dir
def clean_locks():
    with open(csv_file, "r") as f:
        program_list = f.readlines()
        program_list = [x.strip().split(",") for x in program_list[1:]]
    for program_name,program_path,program_gcov_dir,program_src_path,program_manual_path in program_list:
        os.system(f"rm -f {program_gcov_dir}/collect_cov.lock")
        for i in range(32):
            parallel_gcov_dir = program_gcov_dir.replace("obj-gcov", f"obj-gcov{i}")
            os.system(f"rm -f {parallel_gcov_dir}/collect_cov.lock")
