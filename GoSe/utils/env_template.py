from enum import Enum

# Basic
PROJECT_DIR = ""
SEED_NUM = 400
END_PROB = 0.2
HISTORY_LEN = 2
HISTORY_COLLECT_MINUTES = 120
HISTORY_MINUTES_TO_LENGTH_RATIO = 50000 / 180
class Strategies(Enum):
    GoSe = 1
VALID_STRATEGIES_NAMES = []
for member_name, member_value in Strategies.__members__.items():
    VALID_STRATEGIES_NAMES.append(member_name)
DEFAULT_STRATEGY = Strategies.GoSe
DEFAULT_STRATEGY_NAME = DEFAULT_STRATEGY.name
STRATEGY = DEFAULT_STRATEGY
assert DEFAULT_STRATEGY_NAME in VALID_STRATEGIES_NAMES
def set_strategy(strategy_name):
    global STRATEGY
    assert strategy_name in VALID_STRATEGIES_NAMES, "Strategy name {} not valid.".format(strategy_name)
    STRATEGY = Strategies[strategy_name]

# Collect coverage
COV_SERVER_SCRIPT = "GoSe/cov/collect_cov_frontend.py"    
KLEE_REPLAY_PATH = ""
DEFAULT_ENVIRONMENT_SCRIPT = ""
DEFAULT_SANDBOX_TGZ = ""
TIMEOUT = 1.5
COVERAGE_SERVER_PORT = 12321
PRESERVE_OLD_GCOV = False

# Mutation
RANDOM_TIMES = 5
MUTATE_COUNT = 6
THRESHOLD = 1
MUTATION_TIMEOUT = 180
INITIAL_SEED_LENGTH = 0