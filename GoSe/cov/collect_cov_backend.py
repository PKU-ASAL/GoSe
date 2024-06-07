from GoSe.utils.cmdlines import instantiate_path
from GoSe.utils.env import DEFAULT_SANDBOX_TGZ, KLEE_REPLAY_PATH, TIMEOUT
import GoSe.utils.log
import datetime
import json
import logging
import os
import subprocess

OK_CNT = 0
ERR_CNT = 0
HAVE_ERR_MSG_CNT = 0

sandbox_path = None

def initialize_sandbox():
    global sandbox_path
    assert sandbox_path is None, "Sandbox already initialized."
    # random sandbox path under /tmp
    sandbox_path = "/tmp/sandbox-{}/sandbox".format(os.getpid())
    assert not os.path.exists(sandbox_path), "Sandbox path already exists: {}".format(sandbox_path)
    # create the sandbox directory
    assert os.path.exists(DEFAULT_SANDBOX_TGZ), "Sandbox tgz not found: " + DEFAULT_SANDBOX_TGZ
    sandbox_parent_dir = os.path.dirname(sandbox_path)
    if not os.path.exists(sandbox_parent_dir):
        os.makedirs(sandbox_parent_dir)
    assert os.system("tar -xf " + DEFAULT_SANDBOX_TGZ + " -C " + sandbox_parent_dir + " > /dev/null") == 0, "Failed to extract the sandbox tgz"
    assert os.path.exists(sandbox_path), "Failed to create the sandbox directory"

def destroy_sandbox():
    global sandbox_path
    assert sandbox_path is not None, "Sandbox not initialized."
    assert os.path.exists(sandbox_path), "Sandbox path does not exist: {}".format(sandbox_path)
    sandbox_parent_dir = os.path.dirname(sandbox_path)
    assert os.path.relpath(sandbox_parent_dir, "/tmp") != "..", "Invalid sandbox parent directory: {}".format(sandbox_parent_dir)
    assert os.system("rm -rf " + sandbox_parent_dir + " > /dev/null") == 0, "Failed to remove the sandbox directory"
    sandbox_path = None

def run_cmd(cmd):
    global OK_CNT, ERR_CNT, HAVE_ERR_MSG_CNT
    result = None
    try:
        logging.debug("Executing {}".format(cmd))
        result = subprocess.run(cmd, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=TIMEOUT+1)
        logging.debug("  Stdout: {}".format(result.stdout))
        logging.debug("  Stderr: {}".format(result.stderr))
    except Exception as e:
        logging.debug("  Exception: {}".format(e))
        if result and result.stderr:
            logging.debug("  Stderr: {}".format(result.stderr))
        ERR_CNT += 1
        return
    if result.returncode != 0:
        output = ""
        try:
            if result.stdout:
                output += result.stdout.decode('utf-8')
            if result.stderr:
                output += result.stderr.decode('utf-8')
        except Exception as e:
            logging.debug("  Exception: {}".format(e))
        ERR_CNT += 1
        if output and 'error' in output.lower():
            logging.debug("  Executing {}".format(cmd))
            logging.debug("  Returned {}.".format(result.returncode))
            logging.debug("  {}".format(output))
            HAVE_ERR_MSG_CNT += 1
        return
    OK_CNT += 1

def remove_stale_files(gcov_dir: str):
    to_delete = set()
    for path, _, files in os.walk(gcov_dir):
        for f in files:
            if f.endswith('.gcov') or f.endswith('.gcda'):
                to_delete.add(os.path.join(path, f))
    for f in to_delete:
        os.remove(f)

# Return [gcov_file_path], set(executed_lines), total_coverage
def collect_cov_server(gcov_dir: str, program_path: str, args_list: "list[list[str]]", ktest_mode=False, preserve_old_gcov=False, backup=False):
    global sandbox_path, OK_CNT, ERR_CNT, HAVE_ERR_MSG_CNT
    OK_CNT = 0
    ERR_CNT = 0
    HAVE_ERR_MSG_CNT = 0
    assert os.path.exists(gcov_dir), f"gcov_dir not exists: {gcov_dir}"
    assert os.path.exists(program_path), f"program_path not exists: {program_path}"
    program_name = os.path.basename(program_path)

    # Protect the gcov directory
    lock = os.path.join(gcov_dir, "collect_cov.lock")
    assert not os.path.exists(lock), f"{lock} exists. Make sure there is only one collecting cov instance in this dir."
    with open(lock, "w") as f:
        f.write(program_name)

    # Remove stale file
    if not preserve_old_gcov:
        remove_stale_files(gcov_dir)

    cmds = []
    for i, args in enumerate(args_list):
        # save progress every 10%
        if (len(args_list) // 10) > 0 and (i % (len(args_list) // 10) == 0):
            with open(os.path.join(gcov_dir, "progress.tmp"), "a") as f:
                f.write(f"{datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}: {i}/{len(args_list)}\n")
        # initialize sandbox before running the command
        initialize_sandbox()
        # instantiate `Path` type options
        final_args = []
        if ktest_mode and isinstance(args, str):
            args = [args]
        assert isinstance(args, list), f"args_list should be list[list[str]]"
        for arg in args:
            arg = instantiate_path(sandbox_path, arg, "@@@", "")
            arg = instantiate_path(sandbox_path, arg, "@@$", "")
            arg = arg.replace("/tmp/sandbox/", sandbox_path + "/")
            if len(arg) > 2 and arg[0] == '"' and arg[-1] == '"':
                arg = arg[1:-1]
            final_args.append(arg.strip(" \n"))
        # note that the sandbox directory must exist
        root_flag = ''
        if program_path.endswith("tcpreplay"):
            root_flag = 'sudo '
        cmd = ['env', '-i', '/bin/bash', '-c', f"cd {sandbox_path}; timeout --signal=KILL --kill-after={TIMEOUT+1}s {TIMEOUT} echo 0 | {root_flag}"]
        if ktest_mode:
            assert len(final_args) == 1 and final_args[0].endswith('.ktest')
            ktest_path = final_args[0]
            assert os.path.exists(ktest_path), f"ktest_path not exists: {ktest_path}"
            single_cmd = ["KLEE_REPLAY_TIMEOUT={}".format(TIMEOUT), KLEE_REPLAY_PATH, program_path, ktest_path]
            cmd[-1] += f"{' '.join(single_cmd)}"
        else:
            cmd[-1] += f"{program_path} {' '.join([arg for arg in final_args if arg != ''])}"
        cmds.append(cmd)
        run_cmd(cmd)
        destroy_sandbox()

    # complete progress
    with open(os.path.join(gcov_dir, "progress.tmp"), "a") as f:
        f.write(f"{datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}: {len(args_list)}/{len(args_list)}\n")

    gcov_paths, cov_lines, taken_branches, coverage = direct_collect_gcov(gcov_dir)

    # backup
    if backup:
        timestamp = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
        data = {
            "gcov_dir": gcov_dir,
            "program_path": program_path,
            "args_list": args_list,
            "ktest_mode": ktest_mode,
            "preserve_old_gcov": preserve_old_gcov,
            "cmds": cmds,
            "gcov_paths": gcov_paths,
            "cov_lines": list(cov_lines),
            "taken_branches": list(taken_branches),
            "coverage": coverage
        }
        to_save = set()
        for path, _, files in os.walk(gcov_dir):
            for f in files:
                if f.endswith('.gcda'):
                    to_save.add(os.path.join(path, f))
        # compress
        relative_paths = [os.path.relpath(path, gcov_dir) for path in to_save]
        assert os.system(f"tar -czf {gcov_dir}/gcda-backup-{timestamp}.tar.gz -C {gcov_dir} {' '.join(relative_paths)}") == 0, "Failed to compress the backup"
        # save data
        with open(f"{gcov_dir}/data-backup-{timestamp}.json", "w") as f:
            json.dump(data, f)

    # Remove the lock
    os.remove(lock)

    return gcov_paths, cov_lines, taken_branches, coverage

def run_gcov(p):
    os.system(f"cd {os.path.dirname(p)} && gcov -b -c -i -l {p} 1>/dev/null 2>/dev/null")

def direct_collect_gcov(d):
    to_delete = set()
    for path, _, files in os.walk(d):
        for f in files:
            if f.endswith('.gcov'): to_delete.add(os.path.join(path, f))

    for f in to_delete:
        os.remove(f)

    for path, _, files in os.walk(d):
        for f in files:
            if f.endswith('.gcda'): run_gcov(os.path.join(path, f))

    gcov_paths = []
    cov_lines = set()
    not_cov_lines = set()
    cov_branches = list()
    not_cov_branches = list()
    for path, _, files in os.walk(d):
        for f in files:
            if not f.endswith('.gcov'): continue
            gcov_paths.append(os.path.join(path, f))

            with open(os.path.join(path, f)) as f_gcov:
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
                    if l.startswith('branch:'):
                        l = l[8:].strip()
                        line, taken = l.strip().split(',')
                        if line == "":
                            continue
                        if taken == "taken":
                            cov_branches.append((filename, int(line)))
                        else:
                            not_cov_branches.append((filename, int(line)))
    if len(gcov_paths) == 0:
        return [], cov_lines, cov_branches, "0/na (0%), 0/na (0%)"
    else:
        assert (len(cov_lines) + len(not_cov_lines)) > 0
        line_coverage = round(1.0 * len(cov_lines) / (len(cov_lines) + len(not_cov_lines)) * 100.0, 2)
        assert (len(cov_branches) + len(not_cov_branches)) > 0
        branch_coverage = round(1.0 * len(cov_branches) / (len(cov_branches) + len(not_cov_branches)) * 100.0, 2)
        statistics = "{}/{} ({}%), {}/{} ({}%)".format(len(cov_lines), len(cov_lines) + len(not_cov_lines), line_coverage, len(cov_branches), len(cov_branches) + len(not_cov_branches), branch_coverage)
        return gcov_paths, cov_lines, cov_branches, statistics

def restore_latest_gcda(gcov_dir: str):
    gcda_backup = None
    for path, _, files in os.walk(gcov_dir):
        for f in files:
            if f.startswith("gcda-backup-") and f.endswith(".tar.gz"):
                if gcda_backup is None or f > gcda_backup:
                    gcda_backup = f
    if gcda_backup is None:
        return
    print(f"Restoring the latest gcda backup: {gcda_backup}")
    assert os.system(f"tar -xzf {gcov_dir}/{gcda_backup} -C {gcov_dir}") == 0, "Failed to extract the latest gcda backup"

def restore_latest_gcda_by_name(gcov_dir: str, gcda_backup_name: str):
    print(f"Restoring the latest gcda backup: {gcda_backup_name}")
    assert os.path.exists(f"{gcov_dir}/{gcda_backup_name}"), "The latest gcda backup does not exist"
    assert os.system(f"tar -xzf {gcov_dir}/{gcda_backup_name} -C {gcov_dir}") == 0, "Failed to extract the latest gcda backup"

def read_seed_file_into_args(seed_file_path: str):
    seed_list = []
    with open(seed_file_path, "r") as f:
        seed_list = f.readlines()
        seed_list = [seed.strip().split() for seed in seed_list]
    return seed_list