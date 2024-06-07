import logging
import os

def cov_extractor_single(gcov_file_path: str):
    # check if gcov file exists
    if not os.path.exists(gcov_file_path):
        logging.error("Error: gcov file not found: {}".format(gcov_file_path))
        return None, None, None
    # analyse gcov file
    filename = None
    cov_lines = set()
    not_cov_lines = set()
    with open(gcov_file_path, 'r') as f_gcov:
        for l in f_gcov.readlines():
            if l.startswith('file:'):
                filename = os.path.basename(l[5:].strip())
            if l.startswith('lcount:'):
                l = l[7:].strip()
                line, count = l.strip().split(',')
                if int(count) > 0:
                    cov_lines.add((filename, int(line)))
                else:
                    not_cov_lines.add((filename, int(line)))
    return filename, cov_lines

def cov_extractor_list(gcov_file_path_list: "list[str]"):
    executed_lines = set()
    for gcov_file_path in gcov_file_path_list:
        if not gcov_file_path.endswith('.gcov'):
            logging.debug("gcov file {} ignored.".format(gcov_file_path))
            continue
        source_file_name, executed_lines_single = cov_extractor_single(gcov_file_path)
        if source_file_name is None or executed_lines_single is None or len(executed_lines_single) == 0:
            continue
        executed_lines = executed_lines.union(executed_lines_single)
    return executed_lines

def cov_extractor(gcov_file_dir):
    # check if gcov file dir exists
    if not os.path.exists(gcov_file_dir):
        logging.error("Error: gcov file dir not found: {}".format(gcov_file_dir))
        return None
    if os.path.isdir(gcov_file_dir):
        gcov_file_name_list = os.listdir(gcov_file_dir)
    elif os.path.isfile(gcov_file_dir):
        gcov_file_name_list = [gcov_file_dir]
    else:
        assert False, "Error: gcov file dir is neither a file nor a dir: {}".format(gcov_file_dir)
    executed_lines = []
    # analyse gcov file dir
    for gcov_file_name in gcov_file_name_list:
        if not gcov_file_name.endswith('.c.gcov'):
            continue
        gcov_file_path = os.path.join(gcov_file_dir, gcov_file_name)
        source_file_name, executed_lines_single, max_line_number_single = cov_extractor_single(gcov_file_path)
        if source_file_name is None or executed_lines_single is None or max_line_number_single is None:
            continue
        executed_lines_single = ["{}:{}".format(source_file_name, line_number) for line_number in executed_lines_single]
        executed_lines += executed_lines_single
    return set(executed_lines)