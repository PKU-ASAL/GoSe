def deduplicate_seeds(seeds):
    seed_str_set = set()
    result = []
    for seed in seeds:
        seed_str = " ".join(seed)
        if seed_str in seed_str_set:
            continue
        seed_str_set.add(seed_str)
        result.append(seed)
    print("Length of seeds: ", len(seeds))
    print("Length of result: ", len(result))
    return result

def deduplicate_seeds_with_timestamps(seeds, timestamps):
    assert len(seeds) == len(timestamps), "Length mismatch: {} vs {}".format(len(seeds), len(timestamps))
    seed_str_set = set()
    result_seeds = []
    result_ts = []
    for i, seed in enumerate(seeds):
        seed_str = " ".join(seed)
        if seed_str in seed_str_set:
            continue
        seed_str_set.add(seed_str)
        result_seeds.append(seed)
        result_ts.append(timestamps[i])
    print("Length of seeds: ", len(seeds))
    print("Length of result: ", len(result_seeds))
    return result_seeds, result_ts