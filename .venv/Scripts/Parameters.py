import math

MEMORY = 34  # MEMORY - size of main memory in 2^N bytes
CACHE = 20  # CACHE - size of the cache in 2^N bytes
BLOCK = 6  # BLOCK - size of a block of memory in 2^N bytes
MAPPING = 2  # MAPPING - mapping policy for cache in 2^N ways
COUNTERS_CACHE = 15  # CACHE - size of counters cache in 2^N bytes

mem_size = 2 ** MEMORY
cache_size = 2 ** CACHE
block_size = 2 ** BLOCK
mapping = 2 ** MAPPING
replace_policy = "LRU"
write_policy = "WB"
replacement_policies = ["LRU", "LFU", "FIFO", "RAND", "RLR", "ship_plus", "modified_LRU", "pseudo_LRU", "RL"]
write_policies = ["WB", "WT"]
ctr_cache_size = 2 ** COUNTERS_CACHE

# Several Simulations parameters
No_of_simulations = 1
simulations = {}
# Memory_size, Cache_size, Block_size, mapping, replace_policy, write_policy
# simulations[0] = [mem_size, 2 ** 13, 2 ** 6, 2 ** 0, "LRU", "WB"]
# simulations[1] = [mem_size, 2 ** 13, 2 ** 6, 2 ** 1, "LRU", "WB"]
simulations[0] = [mem_size, cache_size, block_size, 2 ** 3, "ship_plus", "WB", ctr_cache_size, "ship_plus"]
# simulations[3] = [mem_size, 2 ** 13, 2 ** 6, 2 ** 3, "LRU", "WB"]
# simulations[4] = [mem_size, 2 ** 13, 2 ** 6, 2 ** 4, "LRU", "WB"]

# simulations[5] = [mem_size, 2 ** 13, 2 ** 6, 2 ** 0, "RLR", "WB"]
# simulations[6] = [mem_size, 2 ** 13, 2 ** 6, 2 ** 1, "RLR", "WB"]
# simulations[1] = [mem_size, 2 ** 13, 2 ** 6, 2 ** 2, "RLR", "WB"]
# simulations[8] = [mem_size, 2 ** 13, 2 ** 6, 2 ** 3, "RLR", "WB"]
# simulations[9] = [mem_size, 2 ** 13, 2 ** 6, 2 ** 4, "RLR", "WB"]



# Initializations
Execution_Times = [0] * No_of_simulations  # Initialize an array with values for all simulations
cache_hits_end = [0] * No_of_simulations
cache_misses_end = [0] * No_of_simulations
hit_percent = [0] * No_of_simulations
hits = 0
misses = 0
ctr_cache_hits = 0
ctr_cache_misses = 0
l1_hits = 0
l1_misses = 0
l1_hits_cc = 0
l1_misses_cc = 0
write_hits = 0
write_misses = 0
current_level = 0
execution_time = 0
cache_hit = False
smart_set_indexing = False
WARMUP_INSTRUCTIONS = 1000000
global instructions_number
instructions_number = 0
level0_cc_trace = []
level1_cc_trace = []
level2_cc_trace = []
level3_cc_trace = []
lazy_updated = False
lazy_update_active = True
total_evictions = 0
###Randomness calculator variables###
previous_address = 0
randomness_num_entries = 65536
randomness = 0
RANDOMNESS_MAX_VALUE = 128
################
# Parameters
TREE_ARITY = 8
TREE_ROOTS = 64
TREE_ARITY_BITS = (TREE_ARITY - 1).bit_length()

MEMORY_START_ADDR = 0
DATA_MEM_SIZE = mem_size / 2
TREE_DATA_SIZE = 8  # In bytes
DRAM_ACCESS_TIME = 80  # in cycles

# Calculated parameters
NUM_DATA_BLOCKS = DATA_MEM_SIZE // block_size
TREE_LEVELS = int(
    (math.ceil(math.log2(NUM_DATA_BLOCKS / TREE_ROOTS)) + TREE_ARITY_BITS - 1) / math.ceil(math.log2(TREE_ARITY)))
TREE_START_ADDRESS = MEMORY_START_ADDR + DATA_MEM_SIZE
TREE_SIZE = (((TREE_ARITY ** TREE_LEVELS) - 1) // (TREE_ARITY - 1)) * TREE_ARITY * TREE_DATA_SIZE;
IND_TREE_SIZE = DATA_MEM_SIZE // TREE_ROOTS
tree_start_addresses = [0] * TREE_ROOTS
tree_start_addresses[0] = TREE_START_ADDRESS
vLastStart = TREE_START_ADDRESS
for x in range(1, len(tree_start_addresses)):
    vLastStart = vLastStart + TREE_SIZE
    tree_start_addresses[x] = vLastStart;

level_hits_l1 = [0] * TREE_LEVELS
level_misses_l1 = [0] * TREE_LEVELS
level_hits = [0] * TREE_LEVELS
level_misses = [0] * TREE_LEVELS
level_access_counter = [0] * TREE_LEVELS
LLC_ctr_level_hits = [0] * TREE_LEVELS
LLC_ctr_level_misses = [0] * TREE_LEVELS
