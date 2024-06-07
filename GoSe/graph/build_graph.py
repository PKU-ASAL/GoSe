from GoSe.utils.cmdlines import sequence_to_optionlist, optionlist_to_cmdline
from GoSe.utils.collect_cov import collect_cov
from GoSe.info.cloInfo import CLOInfo
from GoSe.graph.opft_graph import OPFT
from GoSe.graph.get_probability import get_probability
import logging
import random
import tqdm

def calculate_expected_len(clo_info: CLOInfo, _len_to_covered_lines):
    l = 1
    max_l = 10
    all_options = clo_info.getAllOptions()
    name_to_oinfo = {oinfo.name: oinfo for oinfo in all_options}
    sample_count = len(all_options)
    logging.info(f"sample_count: {sample_count}")
    len_to_seeds = {}
    len_to_covered_lines = _len_to_covered_lines.copy()
    while l < max_l:
        assert l < len(len_to_covered_lines), "l not in len_to_covered_lines"
        covered_lines_l = len_to_covered_lines[l]
        if l + 1 < len (len_to_covered_lines):
            covered_lines_l_plus = len_to_covered_lines[l + 1]
        else:
            covered_lines_l_plus = len_to_covered_lines[l]
            # extend old seeds
            assert l in len_to_seeds, "l not in len_to_seeds"
            old_seeds = len_to_seeds[l]
            sampled_seeds = []
            for seed in old_seeds:
                assert len(seed) == l
                seed.append(random.choice(all_options).name)
                assert len(seed) == l + 1
                sampled_seeds.append(seed)
            # random new seeds
            for _ in range(sample_count):
                seed = []
                for _ in range(l + 1):
                    seed.append(random.choice(all_options).name)
                assert len(seed) == l + 1
                sampled_seeds.append(seed)
            # execute new seeds to get new covered lines
            instantiated_seeds = []
            for seed in sampled_seeds:
                assert len(seed) == l + 1
                # execute seed
                instantiated_seed = sequence_to_optionlist(name_to_oinfo, seed)
                instantiated_seed = optionlist_to_cmdline(clo_info, instantiated_seed).split(" ")
                instantiated_seeds.append(instantiated_seed)
            _, executed_lines, _, _ = collect_cov(clo_info.get_gcov_dir(), clo_info.get_prog_path(), instantiated_seeds, clo_info.get_cov_port())
            covered_lines_l_plus = covered_lines_l_plus.union(executed_lines)
            assert len(sampled_seeds) > 0, "No seed is sampled"
            len_to_seeds[l + 1] = sampled_seeds
        # compare
        if covered_lines_l_plus == covered_lines_l:
            break
        len_to_covered_lines.append(covered_lines_l_plus)
        l += 1
    assert l > 0, "l is not greater than 0"
    return l

def build_graph(clo_info: CLOInfo, hlen: int):
    logging.info("In build_graph:")
    assert clo_info is not None
    graph = OPFT([], [], hlen)
    logging.debug("Zero graph:")
    logging.debug(graph)
    # Build graph
    all_options = clo_info.getAllOptions()
    logging.debug(all_options)
    graph.set_pos_options(clo_info.posOptions)
    graph.set_pos_patterns(clo_info.posPatterns)
    # Add vertices
    for oinfo in all_options:
        graph.add_vertex_from_optioninfo(oinfo)
    logging.debug("After adding vertices:")
    logging.debug(graph)
    # Add edges: complete graph
    graph.create_complete_graph()
    logging.debug("After creating complete graph:")
    logging.debug(graph)
    # Update edge probabilities
    prob_function, set_cover, len_to_covered_lines, attn_scores, d_function = get_probability(clo_info, graph.history_len)
    graph.set_probability(prob_function, set_cover)
    graph.set_expected_len(calculate_expected_len(clo_info, len_to_covered_lines))
    graph.set_attn_scores(attn_scores)
    graph.set_d_function(d_function)
    logging.debug("After setting probabilities:")
    logging.debug(graph)
    return graph
