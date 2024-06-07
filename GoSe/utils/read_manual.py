import subprocess

def read_help(prog_path):
    if prog_path is None:
        return None
    result = subprocess.run([prog_path, '--help'],
                        stdin=subprocess.DEVNULL,
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE,
                        universal_newlines=True)
    help_text = result.stdout
    # if stderr is not empty, append it to help_text
    if len(result.stderr) > 0:
        help_text += result.stderr
    assert not 'No such file' in help_text, f"error in reading help text: {help_text}"
    assert not 'error:' in help_text, f"error in reading help text: {help_text}"
    print(help_text)
    return help_text

def read_manual(prog_path):
    if prog_path is None:
        return None
    result = subprocess.run(['man', prog_path],
                        stdin=subprocess.DEVNULL,
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE,
                        universal_newlines=True)
    manual_text = result.stdout
    # if stderr is not empty, append it to manual_text
    if len(result.stderr) > 0:
        manual_text += result.stderr
    return manual_text