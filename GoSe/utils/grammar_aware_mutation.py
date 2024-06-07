from GoSe.info.cloInfo import CLOInfo
from GoSe.utils.collect_cov import collect_cov
from GoSe.utils.cmdlines import record_timestamp, sequence_to_optionlist, optionlist_to_cmdline
from GoSe.utils.env import RANDOM_TIMES, INITIAL_SEED_LENGTH, THRESHOLD, MUTATION_TIMEOUT, MUTATE_COUNT
import GoSe.utils.log
import logging
import random
import time
from tqdm import tqdm

def random_inserter(candidate, all_options):
    # random insert position
    i = random.randint(0, len(candidate))
    # random times
    stub = []
    for _ in range(random.randint(1, RANDOM_TIMES)):
        stub += [random.choice(all_options).name]
    return candidate[:i] + stub + candidate[i:]

def random_replacer(candidate, all_options):
    # random replace position
    if len(candidate) == 0:
        i = 0
    else:
        i = random.randint(0, len(candidate) - 1)
    random_len = random.randint(1, RANDOM_TIMES)
    stub = []
    for _ in range(random_len):
        stub += [random.choice(all_options).name]
    return candidate[:i] + stub + candidate[i+1:]

def random_deleter(candidate):
    # random delete position
    if len(candidate) == 0:
        return []
    random_len = random.randint(1, RANDOM_TIMES)
    if len(candidate) <= random_len:
        return []
    i = random.randint(0, len(candidate) - random_len)
    return candidate[:i] + candidate[i+random_len:]

def construct_initial_seed(all_options):
    seed = []
    for _ in range(INITIAL_SEED_LENGTH):
        seed += [random.choice(all_options).name]
    return seed

def grammar_aware_mutation(clo_info: CLOInfo, N, initial_seeds=None, enable_timestamp=False, mutate_value=False):
    assert clo_info is not None
    all_options = clo_info.getAllOptions()
    name_to_oinfo = {oinfo.name: oinfo for oinfo in all_options}
    progress = tqdm(total=THRESHOLD*N, desc="seed_corpus size", )
    if initial_seeds:
        candidates = initial_seeds.copy()
    else:
        candidates = [construct_initial_seed(all_options)]
    logging.debug("Initial seeds: ", candidates)
    seed_corpus = []
    cmdlines_to_exec_lines = {}
    covered_lines = set()
    initial_flag = True
    if mutate_value:
        logging.debug("Mutate value mode")
    start_time = time.time()
    while len(candidates) > 0 and len(seed_corpus) < THRESHOLD*N and time.time() - start_time < MUTATION_TIMEOUT:
        # retrieve the first seed
        candidate = candidates.pop(0)
        # mutate and generate the next seed
        cmdlines_to_seed = {}
        for _ in range(MUTATE_COUNT):
            # insert
            seed = random_inserter(candidate, all_options)
            cmdline = optionlist_to_cmdline(clo_info, sequence_to_optionlist(name_to_oinfo, seed)).split(" ")
            cmdlines_to_seed[" ".join(cmdline)] = seed
            # replace
            seed = random_replacer(candidate, all_options)
            cmdline = optionlist_to_cmdline(clo_info, sequence_to_optionlist(name_to_oinfo, seed)).split(" ")
            cmdlines_to_seed[" ".join(cmdline)] = seed
            # delete
            seed = random_deleter(candidate)
            cmdline = optionlist_to_cmdline(clo_info, sequence_to_optionlist(name_to_oinfo, seed)).split(" ")
            cmdlines_to_seed[" ".join(cmdline)] = seed
            # mutate value
            if mutate_value:
                # mutate positional arguments
                cmdline = optionlist_to_cmdline(clo_info, sequence_to_optionlist(name_to_oinfo, candidate), mutation=True).split(" ")
                cmdlines_to_seed[" ".join(cmdline)] = candidate
                # mutate normal arguments
                cmdline = optionlist_to_cmdline(clo_info, sequence_to_optionlist(name_to_oinfo, candidate, mutation=True)).split(" ")
                cmdlines_to_seed[" ".join(cmdline)] = candidate
        # use initial seeds to collect coverage
        new_lines = set()
        if initial_flag:
            for initial_seed in initial_seeds:
                cmdline = optionlist_to_cmdline(clo_info, sequence_to_optionlist(name_to_oinfo, initial_seed)).split(" ")
                cmdlines_to_seed[" ".join(cmdline)] = initial_seed
            initial_flag = False
        # collect coverage
        for joint_cmdline, seed in cmdlines_to_seed.items():
            record_key = joint_cmdline
            cmdline = joint_cmdline.split(" ")
            if record_key in cmdlines_to_exec_lines:
                continue
            _, exec_lines, _, _ = collect_cov(clo_info.get_gcov_dir(), clo_info.get_prog_path(), [cmdline], clo_info.get_cov_port())
            cmdlines_to_exec_lines[record_key] = exec_lines
            increase_lines = exec_lines.difference(covered_lines)
            if len(increase_lines) > 0:
                candidates.insert(0, seed)
            else:
                if not mutate_value:
                    candidates.append(seed)
            # only add seeds that increase coverage in mutate_value mode
            if not mutate_value or len(increase_lines) > 0:
                seed_corpus.append(record_timestamp(cmdline, enable=enable_timestamp))
                progress.update(1)
            new_lines = new_lines.union(increase_lines)
            covered_lines = covered_lines.union(new_lines)
        if mutate_value:
            logging.info("Length of candidates: ", len(candidates))
    progress.close()
    # select top N coverage seeds
    if enable_timestamp:
        seed_corpus.sort(key=lambda x: len(cmdlines_to_exec_lines[" ".join(x[1])]), reverse=True)
        timestamps, seed_corpus = zip(*seed_corpus)
        assert type(timestamps) == tuple and type(seed_corpus) == tuple
        assert len(timestamps) == len(seed_corpus)
        timestamps = list(timestamps)[:N]
        seeds = list(seed_corpus)[:N]
        assert len(timestamps) == len(seeds), "Length mismatch: {} vs {}".format(len(timestamps), len(seeds))
        return timestamps, seeds
    else:
        seed_corpus.sort(key=lambda x: len(cmdlines_to_exec_lines[" ".join(x)]), reverse=True)
        return seed_corpus[:N]