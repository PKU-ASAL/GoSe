import subprocess
import json
import os
import socket

# Return [gcov_file_path], set(executed_lines), total_coverage
def collect_cov(gcov_dir: str, program_path: str, args_list: "list[list[str]]", port: int, ktest_mode=False, preserve_old_gcov=False, backup=False):
    assert port is not None and port > 0
    command_json = {
        "gcov_dir": gcov_dir,
        "program_path": program_path,
        "args_list": args_list,
        "ktest_mode": ktest_mode,
        "preserve_old_gcov": preserve_old_gcov,
        "backup": backup
    }
    client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    client_socket.connect(("localhost", port))

    command_json = json.dumps(command_json)
    client_socket.send(command_json.encode("utf-8"))
    client_socket.shutdown(socket.SHUT_WR)

    result_json = ""
    while True:
        data = client_socket.recv(1024).decode("utf-8")
        if not data:
            break
        result_json += data
    client_socket.close()
    result = json.loads(result_json)

    gcov_paths = result["gcov_paths"]
    # result["executed_lines"]) is a list of list, convert it to a set of set
    executed_lines = set(tuple(item) for item in result["executed_lines"])
    taken_branches = result["taken_branches"]
    coverage = result["coverage"]

    return gcov_paths, executed_lines, taken_branches, coverage

def run_gcov(p):
    subprocess.call(['gcov', '-b', '-c', '-i', '-l', p], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, cwd=os.path.dirname(p))

def set_cover_greedy_dict(d) -> list:
    # d: {key: set}
    # set cover problem: find the smallest set of keys the set of which covers all elements
    all_elements = set()
    for s in d.values():
        all_elements |= s
    result = []
    while all_elements:
        best_key = max(d, key=lambda k: len(d[k] & all_elements))
        result.append(best_key)
        all_elements -= d[best_key]
    return result