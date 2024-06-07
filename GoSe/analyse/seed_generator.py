from GoSe.graph.opft_graph import OPFT
from GoSe.utils.env import SEED_NUM

def generate_seeds(graph: OPFT, seed_num=SEED_NUM):
    assert seed_num is not None
    seeds = graph.walk(seed_num)
    return seeds
