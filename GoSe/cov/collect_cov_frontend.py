from GoSe.cov.collect_cov_backend import collect_cov_server
import json
import socket
from sys import argv

def run_command(command_json):
    # collect_cov(gcov_dir: str, program_path: str, args_list: "list[list[str]]"):
    assert "gcov_dir" in command_json, f"gcov_dir not found in {command_json}"
    assert "program_path" in command_json, f"program_path not found in {command_json}"
    assert "args_list" in command_json, f"args_list not found in {command_json}"
    assert "ktest_mode" in command_json, f"ktest_mode not found in {command_json}"
    assert "preserve_old_gcov" in command_json, f"preserve_old_gcov not found in {command_json}"
    assert "backup" in command_json, f"backup not found in {command_json}"
    gcov_dir = command_json["gcov_dir"]
    program_path = command_json["program_path"]
    args_list = command_json["args_list"]
    ktest_mode = command_json["ktest_mode"]
    preserve_old_gcov = command_json["preserve_old_gcov"]
    backup = command_json["backup"]
    gcov_paths, cov_lines, cov_branches, coverage = collect_cov_server(gcov_dir, program_path, args_list, ktest_mode, preserve_old_gcov, backup)
    result_dict = {
        "gcov_paths": gcov_paths,
        "executed_lines": list(cov_lines),
        "taken_branches": list(cov_branches),
        "coverage": coverage
    }
    result_str = json.dumps(result_dict)
    return result_str

def start_server(port=12321):
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    print("Server listening on port {}".format(port))
    try:
        server_socket.bind(("0.0.0.0", port))
    except:
        print("Failed to bind to port {}. Maybe the port is already in use.".format(port))
        return
    server_socket.listen(1)

    while True:
        client_socket, client_address = server_socket.accept()
        print(f"Accepted connection from {client_address}")

        client_data = ""
        while True:
            data = client_socket.recv(1024).decode("utf-8")
            if not data:
                break
            client_data += data

        command_json = json.loads(client_data)

        print(f"Received command json: {command_json}")

        result_json = run_command(command_json)

        # if client_socket is broken, ignore
        try:
            client_socket.send(result_json.encode("utf-8"))
            client_socket.shutdown(socket.SHUT_WR)
        except:
            print("Client socket broken, ignored")
        client_socket.close()

if __name__ == "__main__":
    if len(argv) == 2:
        port = int(argv[1])
        start_server(port)
    else:
        start_server()
