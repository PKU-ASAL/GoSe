from GoSe.utils.deduplicate_seeds import deduplicate_seeds
import os
import logging
import time
import json

def output_seeds(prog_name, seeds, dst_dir, format=None):
    seeds = deduplicate_seeds(seeds)
    # make sure the directory exists
    if not os.path.exists(dst_dir):
        os.makedirs(dst_dir)
    if format == "no_date":
        output_path = os.path.join(dst_dir, "{}.txt".format(prog_name))
    else:
        output_path = os.path.join(dst_dir, "{}-{}.txt".format(prog_name, time.strftime("%Y%m%d-%H%M%S")))
    with open(output_path, "w") as f:
        for seed in seeds:
            f.write(" ".join(seed))
            f.write("\n")
    logging.info("Output seeds to {}.".format(output_path))

def output_seeds_with_timestamps(prog_name, seeds, timestamps, dst_dir, format=None):
    # make sure the directory exists
    if not os.path.exists(dst_dir):
        os.makedirs(dst_dir)
    if format == "no_date":
        output_path = os.path.join(dst_dir, "{}.txt".format(prog_name))
    else:
        output_path = os.path.join(dst_dir, "{}-{}.txt".format(prog_name, time.strftime("%Y%m%d-%H%M%S")))
    # sort by timestamp
    seeds, timestamps = zip(*sorted(zip(seeds, timestamps), key=lambda x: x[1]))
    with open(output_path, "w") as f:
        for i, seed in enumerate(seeds):
            f.write(str(timestamps[i]) + ":")
            f.write(" ".join(seed))
            f.write("\n")
    logging.info("Output seeds to {}.".format(output_path))

def output_coverage(prog_name, seeds, lines, branches, dst_dir):
    assert os.path.exists(dst_dir), "Seed directory does not exist."
    cov_file = os.path.join(dst_dir, "cov-{}-{}.json".format(prog_name, time.strftime("%Y%m%d-%H%M%S")))
    if not seeds:
        seeds = []
    if not lines:
        lines = []
    if not branches:
        branches = []
    with open(cov_file, "w") as f:
        json.dump({
            "program": prog_name,
            "time": time.strftime("%Y-%m-%d %H:%M:%S"),
            "seeds": list(seeds),
            "lines": list(lines),
            "branches": list(branches)
            }, f, indent=4)
    logging.info("Output coverage to {}.".format(cov_file))

def update_timestamps(timestamps):
    # replace first timestamp with the current timestamp
    # update the rest of the timestamps based on intervals
    new_timestamps = []
    new_timestamps.append(time.time())
    for i in range(1, len(timestamps)):
        new_timestamps.append(new_timestamps[i-1] + (timestamps[i] - timestamps[i-1]))
    return new_timestamps