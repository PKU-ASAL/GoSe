from GoSe.analyse.cov_analyzer import cov_to_probabilities
from GoSe.graph.opft_vertex import OPFTVertex
from GoSe.info.cloInfo import CLOInfo
from GoSe.utils.collect_cov import collect_cov, set_cover_greedy_dict
from GoSe.utils.checkers import check_condition_homap, check_condition_ohmap, check_hmap, check_pmap
from GoSe.utils.env import COV_SERVER_SCRIPT, HISTORY_COLLECT_MINUTES, HISTORY_MINUTES_TO_LENGTH_RATIO
from concurrent.futures import ThreadPoolExecutor, as_completed
from itertools import product
import logging
import math
import os
import sys
import time
from tqdm import tqdm

def sequence_to_cmdline(sequence: "list[OPFTVertex]") -> "list[str]":
    values = []
    logging.debug("  sequence: {}".format(sequence))
    for oinfo in sequence:
        values.append(oinfo.instantiate())
    logging.debug("  cmdline: {}".format(values))
    return values

def get_pmap_from_probability(probability, option_cnt, history_len):
    pmap = dict()
    for i in range(option_cnt):
        assert i not in pmap
        pmap[i] = dict()
        for j in range(option_cnt):
            assert j not in pmap[i]
            pmap[i][j] = dict()
            for k in range(history_len):
                pmap[i][j][k] = probability(i, j, k)
    return pmap

def get_probability_from_values(pmap, option_cnt, history_len):
    if option_cnt == 0:
        return lambda i, j, k: 0
    # Regression f(i, j, k)
    assert option_cnt > 0
    assert len(pmap[0][0]) >= history_len
    func_map = dict()
    for i in range(option_cnt):
        if i not in func_map:
            func_map[i] = dict()
        for j in range(option_cnt):
            if j not in func_map[i]:
                func_map[i][j] = None
            # regression
            # truncate
            def truncate_function(i, j, k):
                pmap0 = pmap
                max_len = history_len
                return pmap0[i][j][min(k, max_len-1)]
            func_map[i][j] = truncate_function
    def p(i, j, k):
        option_cnt_ = option_cnt
        max_len = history_len
        pmap0 = pmap
        func_map0 = func_map
        assert 0 <= i < option_cnt_ and 0 <= j < option_cnt_
        if 0 <= k < max_len:
            return pmap0[i][j][k]
        return func_map0[i][j](i, j, k)
    return p

def run(all_options, clo_info, choices, gcov_dir, prog_path, cov_port):
    logging.info("Running get_hlmap_in_parallel subtask: {}".format(prog_path))
    hlmap = dict()
    bar_choices = tqdm(choices, file=sys.stderr)
    for choice in bar_choices:
        sequence = []
        for j in choice:
            sequence.append(all_options[j])
        args_with_pos = []
        for pattern in clo_info.posPatterns:
            args = sequence_to_cmdline(sequence)
            for item in pattern.split():
                if item[0] == '@':
                    for option in clo_info.posOptions:
                        if option.name == item[1:]:
                            args.append(option.instantiate())
                            break
                else:
                    args.append(item)
            args_with_pos.append(args)
        logging.debug("args_with_pos: {}".format(args_with_pos))
        # Execute program to obtain gcov results
        _, executed_lines, _, _ = collect_cov(gcov_dir, prog_path, args_with_pos, cov_port)
        choice_str = ",".join([str(x) for x in choice])
        # logging.debug("choices: {} -> executed_lines: {}".format(choice_str, executed_lines))
        hlmap[choice_str] = executed_lines
    return hlmap

def get_hlmap_in_parallel(hlen, all_options, clo_info, jobs=4):
    logging.info("Collecting coverage information...")
    COVERAGE_SERVER_PORT = clo_info.get_cov_port()
    hlmap = dict()
    option_cnt = len(all_options)
    all_choices = []
    for i in range(0, hlen + 1):
        choices = list(product(range(option_cnt), repeat=i))
        all_choices.extend(choices)
    # divide all_choices into jobs
    length = len(all_choices)
    step = max(1, length // jobs)
    # precheck: all gcov dirs should exist
    base_gcov_dir = clo_info.get_gcov_dir()
    base_prog_path = clo_info.get_prog_path()
    all_gcov_dirs = []
    all_prog_paths = []

    for i in range(1, jobs + 1):
        gcov_dir = base_gcov_dir.replace("obj-gcov", "obj-gcov{}".format(i))
        prog_path = base_prog_path.replace("obj-gcov", "obj-gcov{}".format(i))
        assert os.path.exists(gcov_dir), "gcov dir {} not exists".format(gcov_dir)
        assert os.path.exists(prog_path), "prog path {} not exists".format(prog_path)
        all_gcov_dirs.append(gcov_dir)
        all_prog_paths.append(prog_path)

    with ThreadPoolExecutor(max_workers=jobs*2) as executor:
        futures = []
        tasks = []
        cnt = 0
        for i in range(jobs):
            if cnt >= length:
                break
            start = cnt
            end = min(length, cnt + step) if i != jobs - 1 else length
            cnt = end
            executor.submit(os.system, f"echo get_hlmap_in_parallel_{COVERAGE_SERVER_PORT+i} && python3 {COV_SERVER_SCRIPT} {COVERAGE_SERVER_PORT + i} 2>/dev/null 1>/dev/null")
            tasks.append((all_options, clo_info, all_choices[start:end], all_gcov_dirs[i], all_prog_paths[i], COVERAGE_SERVER_PORT + i))
        time.sleep(2)
        for task in tasks:
            futures.append(executor.submit(run, *task))
        for future in tqdm(as_completed(futures), total=len(futures), desc="Collecting coverage information tasks (total length: {})".format(length), file=sys.stderr, dynamic_ncols=True):
            hlmap.update(future.result())
        os.system(f"pkill -f get_hlmap_in_parallel")

    # check all choices in hlmap
    for choice in all_choices:
        choice_str = ",".join([str(x) for x in choice])
        assert choice_str in hlmap, "hlmap incomplete:\nchoice {} not in hlmap".format(choice_str)
    logging.info("Collecting coverage information done.")
    return hlmap

def get_probability(clo_info: CLOInfo, hlen):
    logging.info("In get_probability:")
    if len(clo_info.getAllOptions()) == 0:
        logging.error("No options found.")
        # return function that always returns 0
        return lambda i, j, k: 0, None
    # Update dynmaic history len
    dlen = math.ceil(math.log(HISTORY_COLLECT_MINUTES * HISTORY_MINUTES_TO_LENGTH_RATIO, len(clo_info.getAllOptions())))
    hlen = min(hlen, dlen)
    # Get probabilities
    all_options = clo_info.getAllOptions()
    logging.debug("all_options: {}".format(all_options))
    # 1. Collect P(Option | history)
    option_cnt = len(all_options)
    # hlmap: choice_str "0,1,2" -> executed_lines [{}:{}]
    hlmap = get_hlmap_in_parallel(hlen, all_options, clo_info)
    condition_homap = dict()
    set_cover = set_cover_greedy_dict(hlmap)
    logging.debug("set_cover: {}".format(set_cover))
    logging.debug("len(set_cover): {}".format(len(set_cover)))
    logging.info("Calculating probabilities...")
    # consider all history
    for i in range(0, hlen):
        history_choices = product(range(option_cnt), repeat=i)
        for history_choice in history_choices:
            history_choice_str = ",".join([str(x) for x in history_choice])
            assert history_choice_str in hlmap, "history choice {} not in hlmap".format(history_choice_str)
            history_executed_lines = hlmap[history_choice_str]
            history_choice_name_str = " ".join([all_options[x].name for x in history_choice])
            new_choice_name_str_list = []
            new_executed_lines_list = []
            for j in range(option_cnt):
                new_choice = list(history_choice) + [j]
                new_choice_str = ",".join([str(x) for x in new_choice])
                assert new_choice_str in hlmap, "new choice {} not in hlmap".format(new_choice_str)
                new_executed_lines = hlmap[new_choice_str]
                new_executed_lines_list.append(new_executed_lines)
                new_choice_name_str = " ".join([all_options[x].name for x in new_choice])
                new_choice_name_str_list.append(new_choice_name_str)
            probs = cov_to_probabilities(history_executed_lines, new_executed_lines_list)
            logging.debug("history_choice_str: {}".format(history_choice_str))
            logging.debug("probs: {}".format(probs))
            if history_choice_str not in condition_homap:
                condition_homap[history_choice_str] = dict()
            for j in range(option_cnt):
                condition_homap[history_choice_str][str(j)] = probs[j]
    check_condition_homap(condition_homap, option_cnt, hlen)
    hmap = dict()
    hmap[''] = 1.0
    for i in range(1, hlen + 1):
        choices = product(range(option_cnt), repeat=i)
        for choice in choices:
            choice_str = ",".join([str(x) for x in choice])
            choice_pruned_str = ",".join([str(x) for x in choice[:-1]])
            logging.debug("choice_str: {}".format(choice_str))
            logging.debug("choice_pruned_str: {}".format(choice_pruned_str))
            assert choice_pruned_str in hmap
            assert choice_pruned_str in condition_homap
            assert str(choice[-1]) in condition_homap[choice_pruned_str]
            hmap[choice_str] = hmap[choice_pruned_str] * condition_homap[choice_pruned_str][str(choice[-1])]
    check_hmap(hmap, option_cnt, hlen)
    # 2. Calculate P(Option_i | Option_j)
    #    condition_ohmap[option_i][k][history_choice_str]
    condition_ohmap = dict()
    for j in range(option_cnt):
        if j not in condition_ohmap:
            condition_ohmap[str(j)] = dict()
        for k in range(0, hlen):
            if k not in condition_ohmap[str(j)]:
                condition_ohmap[str(j)][k] = dict()
            history_choices = product(range(option_cnt), repeat=k)
            # Bayesian
            demoninator = 0
            for history_choice in history_choices:
                history_choice_str = ",".join([str(x) for x in history_choice])
                assert history_choice_str in hmap
                assert history_choice_str in condition_homap
                assert str(j) in condition_homap[history_choice_str]
                if j in history_choice:
                    demoninator += hmap[history_choice_str]
            assert demoninator >= 0
            history_choices = product(range(option_cnt), repeat=k)
            for history_choice in history_choices:
                history_choice_str = ",".join([str(x) for x in history_choice])
                logging.debug("history_choice_str: {}".format(history_choice_str))
                assert history_choice_str in hmap
                assert history_choice_str in condition_homap
                assert str(j) in condition_homap[history_choice_str]
                if demoninator > 0:
                    if j in history_choice:
                        numerator = 1.0 * hmap[history_choice_str]
                    else:
                        numerator = 0
                    assert 1.0 * numerator / demoninator <= 1.0
                    condition_ohmap[str(j)][k][history_choice_str] = 1.0 * numerator / demoninator
                else:
                    assert demoninator == 0, "Bad demonimator: {}".format(demoninator)
                    condition_ohmap[str(j)][k][history_choice_str] = 1.0 / pow(option_cnt, k)
    check_condition_ohmap(condition_ohmap, option_cnt, hlen)
    # i: start option, j: end option, k: history length (contains i)
    pmap = dict()
    dmap = dict()
    for i in range(option_cnt):
        pmap[i] = dict()
        dmap[i] = dict()
        for j in range(option_cnt):
            if j not in pmap[i]:
                pmap[i][j] = dict()
            if j not in dmap[i]:
                dmap[i][j] = dict()
            pmap[i][j][0] = hmap[str(j)]
            dmap[i][j][0] = hmap[str(j)] - hmap['']
            for k in range(1, hlen):
                # P(Option_{k+1,i} | Option_{k,j})
                history_choices = product(range(option_cnt), repeat=k)
                pres = 0
                dres = 0
                for history_choice in history_choices:
                    if i not in history_choice:
                        continue
                    assert i in history_choice, "i not in history_choice"
                    history_choice_str = ",".join([str(x) for x in history_choice])
                    assert history_choice_str in condition_ohmap[str(i)][k]
                    _p = condition_ohmap[str(i)][k][history_choice_str] * condition_homap[history_choice_str][str(j)]
                    full_str = ",".join([str(x) for x in history_choice] + [str(j)])
                    pres += _p
                    dres += _p * (len(hlmap[full_str]) - len(hlmap[history_choice_str]))
                pmap[i][j][k] = pres
                dmap[i][j][k] = dres
                if k == 1:
                    assert pmap[i][j][k] == condition_homap[str(i)][str(j)], "pmap[i][j][k]: {} != condition_homap[str(i)][str(j)]: {}".format(pmap[i][j][k], condition_homap[str(i)][str(j)])
    check_pmap(pmap, option_cnt, hlen)
    # 3. Regression f(i, j, k)
    p = get_probability_from_values(pmap, option_cnt, hlen)
    d = get_probability_from_values(dmap, option_cnt, hlen)
    logging.info("Calculating probabilities done.")
    len_to_covered_lines = []
    for l in range(0, hlen + 1):
        covered_lines = set()
        # consider all history with length l
        history_choices = product(range(option_cnt), repeat=l)
        for history_choice in history_choices:
            history_choice_str = ",".join([str(x) for x in history_choice])
            assert history_choice_str in hlmap
            covered_lines |= hlmap[history_choice_str]
        len_to_covered_lines.append(covered_lines)
    # attention scores
    attn_scores = dict()
    for i in range(option_cnt):
        attn_scores[str(i)] = dict()
        for j in range(0, hlen + 1):
            histories = list(product(range(option_cnt), repeat=j))
            score = 0
            histories_with_i = []
            for history in histories:
                if i in history:
                    histories_with_i.append(history)
            if len(histories_with_i) == 0:
                assert j == 0, "histories_with_i is empty but j is not 0"
                attn_scores[str(i)][str(j)] = 0
                continue
            normalized_partial_hmap = dict()
            normalizer = 0
            for history in histories_with_i:
                assert i in history, "i not in history"
                history_str = ",".join([str(x) for x in history])
                assert history_str in hmap, "history_str not in hmap"
                normalized_partial_hmap[history_str] = hmap[history_str]
                normalizer += hmap[history_str]
            assert normalizer > 0, "normalizer is 0"
            for history_str in normalized_partial_hmap:
                normalized_partial_hmap[history_str] /= normalizer
                score += normalized_partial_hmap[history_str] * len(hlmap[history_str])
            attn_scores[str(i)][str(j)] = score
    return p, set_cover, len_to_covered_lines, attn_scores, d
