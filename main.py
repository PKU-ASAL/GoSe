from GoSe.analyse.seed_generator import generate_seeds
from GoSe.graph.opft_graph import OPFT
from GoSe.graph.build_graph import build_graph
from GoSe.info.cloInfo import CLOInfo
from GoSe.utils.cmdlines import optionlist_to_cmdline, sequence_to_optionlist
from GoSe.utils.collect_cov import collect_cov
from GoSe.utils.deduplicate_seeds import deduplicate_seeds_with_timestamps
from GoSe.utils.env import PRESERVE_OLD_GCOV, SEED_NUM, COVERAGE_SERVER_PORT, HISTORY_LEN, VALID_STRATEGIES_NAMES, DEFAULT_STRATEGY_NAME, set_strategy
from GoSe.utils.file_processors import clean_locks, read_option_info_file, append_cov
from GoSe.utils.grammar_aware_mutation import grammar_aware_mutation
import GoSe.utils.log
from GoSe.utils.output_seeds import output_coverage, output_seeds_with_timestamps, update_timestamps
from GoSe.utils.parse_manual import parse_manual
from GoSe.utils.read_manual import read_help, read_manual
import argparse
import logging
import os

def generate_instantiation_guidebook(prog_path, dst_dir):
    if not os.path.exists(prog_path):
        logging.error("Program does not exist: {}".format(prog_path))
        return
    help_text = read_help(prog_path)
    manual_path = os.path.join(os.path.dirname(prog_path), '..', 'man', '{}.1'.format(os.path.basename(prog_path)))
    if os.path.exists(manual_path):
        manual_text = read_manual(manual_path)
        if help_text is None or len(help_text) == 0:
            help_text = manual_text
    assert help_text is not None, "Help text and manual text are both empty."
    assert len(help_text) > 0, "Help text and manual text are both empty."
    guidebook_path = parse_manual(prog_path, help_text, dst_dir)
    logging.info("Instantiation guidebook: {}".format(guidebook_path))
    assert guidebook_path is not None and os.path.exists(guidebook_path)

def _build_clo_info(prog_path, gcov_prog_dir, option_info_dir):
    prog_name = os.path.basename(prog_path)
    option_info_path = os.path.join(option_info_dir, "{}_option_info.csv".format(prog_name))
    pos_option_info_path = os.path.join(option_info_dir, "{}_positional_option_info.csv".format(prog_name))
    pos_pattern_path = os.path.join(option_info_dir, "{}_usage.txt".format(prog_name))
    if not os.path.exists(option_info_path):
        logging.warn("Option info does not exist: {}".format(option_info_path))
        return
    if not os.path.exists(pos_option_info_path):
        logging.warn("Operand info does not exist: {}".format(pos_option_info_path))
        return
    if not os.path.exists(pos_pattern_path):
        logging.warn("Operand pattern does not exist: {}".format(pos_pattern_path))
        return
    assert COVERAGE_SERVER_PORT is not None and type(COVERAGE_SERVER_PORT) == int
    clo_info = CLOInfo(prog_path, gcov_prog_dir, COVERAGE_SERVER_PORT)
    info_dict_list = read_option_info_file(option_info_path)
    logging.debug(info_dict_list)
    for info_dict in info_dict_list:
        clo_info.addRawOption(info_dict['groupName'], info_dict['name'], info_dict['type'], info_dict['value'], info_dict['description'])

    pos_info_dict_list = read_option_info_file(pos_option_info_path)
    logging.debug(pos_info_dict_list)
    for info_dict in pos_info_dict_list:
        clo_info.addRawPosOption(info_dict['name'], info_dict['type'], info_dict['value'], info_dict['description'])
    
    with open(pos_pattern_path, 'r') as f:
        pos_patterns = f.read().split('\n')
        for pattern in pos_patterns:
            # ignore empty pattern initially
            if pattern.strip() == '':
                continue
            clo_info.posPatterns.append(pattern)
        # if no other patterns, add empty pattern
        if len(clo_info.posPatterns) == 0:
            clo_info.posPatterns.append("")
        clo_info.posPatterns = list(set(clo_info.posPatterns))
    logging.debug(str(clo_info))
    return clo_info

def run_build_graph(prog_path, gcov_prog_dir, option_info_dir, save_prob_dir=None):
    prog_name = os.path.basename(prog_path)
    logging.info("Running build graph for program: {}".format(prog_name))
    # check if the probability file exists
    if save_prob_dir:
        if os.path.exists(os.path.join(save_prob_dir, "{}-probability.json".format(prog_name))):
            logging.warning("Probability file already exists: {}".format(os.path.join(save_prob_dir, "{}-probability.json".format(prog_name))))
            logging.warning("Skip building graph.")
            return
    # remove old locks
    clean_locks()
    clo_info = _build_clo_info(prog_path, gcov_prog_dir, option_info_dir)
    graph = build_graph(clo_info, HISTORY_LEN)
    assert graph is not None
    assert len(graph.vertex_id) == len(graph.vertices)
    assert graph.probability is not None
    if save_prob_dir:
        if not os.path.exists(save_prob_dir):
            os.makedirs(save_prob_dir)
        save_path = os.path.join(save_prob_dir, "{}-probability.json".format(prog_name))
        graph.save_probability(save_path)

def run_GoSe(prog_path, save_prob_dir, gcov_prog_dir, option_info_dir, output_seeds_dir=None, SEED_NUM=200):
    prog_name = os.path.basename(prog_path)
    logging.info("Running run_walk_with_attention for program: {}".format(prog_name))
    graph = OPFT()
    load_path = os.path.join(save_prob_dir, "{}-probability.json".format(prog_name))
    assert os.path.exists(load_path), "Probability file does not exist: {}".format(load_path)
    graph.load_probability(load_path)
    # walk
    clo_info = _build_clo_info(prog_path, gcov_prog_dir, option_info_dir)
    all_options = clo_info.getAllOptions()
    name_to_oinfo = {oinfo.name: oinfo for oinfo in all_options}
    seed_num = SEED_NUM * 2
    logging.info("walk {} seeds".format(seed_num))
    seeds = generate_seeds(graph, seed_num)
    timestamps, seeds = zip(*seeds)
    assert len(timestamps) == len(seeds)
    timestamps = list(timestamps)
    seeds = list(seeds)
    seed_num = len(seeds)
    # mutate on batched seeds 
    WALK_NUM = 200
    MUTATE_NUM = 50
    start = 0
    final_seeds = []
    final_timestamps = []
    while start < seed_num:
        end = min(start + WALK_NUM, seed_num)
        batch_seeds = seeds[start:end]
        batch_timestamps = update_timestamps(timestamps[start:end])
        batch_instantiated_seeds = []
        for i, seed in enumerate(batch_seeds):
            instantiated_seed = optionlist_to_cmdline(clo_info, sequence_to_optionlist(name_to_oinfo, seed)).split(" ")
            batch_instantiated_seeds.append(instantiated_seed)
        logging.info("use walked {}-{} seeds".format(start, end))
        timestamps2, seeds2 = grammar_aware_mutation(clo_info, MUTATE_NUM, batch_seeds, enable_timestamp=True, mutate_value=True)
        assert len(timestamps2) == len(seeds2), "Length mismatch: {} vs {}".format(len(timestamps2), len(seeds2))
        final_seeds += batch_instantiated_seeds
        final_seeds += seeds2
        final_timestamps += batch_timestamps
        final_timestamps += timestamps2
        assert len(final_timestamps) == len(final_seeds), "Length mismatch: {} vs {}".format(len(final_timestamps), len(final_seeds))
        logging.info("length of final seeds: {}".format(len(final_seeds)))
        if len(final_seeds) >= SEED_NUM:
            break
        start = end
    final_seeds, final_timestamps = deduplicate_seeds_with_timestamps(final_seeds, final_timestamps)
    if output_seeds_dir:
        output_seeds_with_timestamps(prog_name, final_seeds, final_timestamps, output_seeds_dir)
    return final_seeds

def get_seeds_coverage(prog_path, gcov_prog_dir, seeds, log_key=None, output_seeds_dir=None, output_coverage_file=None):
    if log_key is None:
        from GoSe.utils.env import STRATEGY
        log_key = 'GoSe-{}'.format(STRATEGY.name)
    if PRESERVE_OLD_GCOV:
        logging.warning("Preserve old gcov files.")
    prog_name = os.path.basename(prog_path)
    assert COVERAGE_SERVER_PORT is not None and type(COVERAGE_SERVER_PORT) == int
    path, lines, branches, final_cov = collect_cov(gcov_prog_dir, prog_path, seeds, COVERAGE_SERVER_PORT, preserve_old_gcov=PRESERVE_OLD_GCOV)
    if len(path) == 0:
        logging.warn("{}: No gcov is collected.".format(prog_name))
        logging.warn("collect_cov: {}, {}".format(prog_name, seeds))
    logging.info("Total: {} {}".format(prog_name, final_cov))
    if output_coverage_file:
        append_cov(output_coverage_file, prog_name, log_key, final_cov)
    if output_seeds_dir:
        output_coverage(prog_name, seeds, lines, branches, output_seeds_dir)

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--prog-path", help="tested program path", type=str)
    parser.add_argument("--prog-gcov-dir", help="tested program gcov directory", type=str)
    parser.add_argument("--prog-src-path", help="tested program source code path (.c)", type=str)
    parser.add_argument("--option-csv-dir", help="option info csv directory", type=str)
    parser.add_argument("--coverage-server-port", help="port used to communicate with coverage server", type=int, default=12321)
    parser.add_argument("--strategy", type=str, choices=VALID_STRATEGIES_NAMES, default=DEFAULT_STRATEGY_NAME, help="generation strategy")

    parser.add_argument("--generate-instantiation-guidebook", help="read manual and generate instantiation guidebook", action="store_true", default=False)
    
    parser.add_argument("--build-graph", help="build graph", action="store_true", default=False)
    parser.add_argument("--save-probability-dir", help="save probability directory", type=str, default=None)

    parser.add_argument("--generate-seeds-only", help="generate seeds without testing for coverage", action="store_true", default=False)
    parser.add_argument("--test-seeds", help="generate seeds and test for coverage", action="store_true", default=False)
    parser.add_argument("--seed-num", help="number of generated seeds", type=int, default=None)
    parser.add_argument("--output-seeds-dir", help="output seeds directory", type=str, default="GoSe/output/seeds")
    parser.add_argument("--output-coverage-file", help="output coverage file path", type=str, default=None)

    args = parser.parse_args()

    # set strategy
    set_strategy(args.strategy)
    # set coverage server port
    COVERAGE_SERVER_PORT = args.coverage_server_port

    if args.generate_instantiation_guidebook and args.prog_path and args.option_csv_dir:
        generate_instantiation_guidebook(args.prog_path, args.option_csv_dir)
    elif args.build_graph and args.prog_path and args.prog_gcov_dir and args.option_csv_dir:
        run_build_graph(args.prog_path, args.prog_gcov_dir, args.option_csv_dir, args.save_probability_dir)
    elif (args.generate_seeds_only or args.test_seeds) and args.prog_path and args.prog_gcov_dir:
        if args.seed_num:
            SEED_NUM = args.seed_num
        logging.info("SEED_NUM: {}".format(SEED_NUM))
        if args.strategy == "GoSe" and args.option_csv_dir:
            seeds = run_GoSe(args.prog_path, args.save_probability_dir, args.prog_gcov_dir, args.option_csv_dir, args.output_seeds_dir, SEED_NUM)
        if args.test_seeds:
            get_seeds_coverage(args.prog_path, args.prog_gcov_dir, seeds, args.strategy, args.output_seeds_dir, args.output_coverage_file)
        elif args.generate_seeds_only:
            logging.warning("Seeds generated without testing for coverage.")
    else:
        parser.print_help()
        exit(1)
