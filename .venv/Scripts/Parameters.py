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
replacement_policies = ["LRU", "LFU", "FIFO", "RAND", "RLR", "ship_plus", "modified_LRU", "pseudo_LRU", "RL",
                        "expected_hits"]
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
lazy_update_misses = 0
total_evictions = 0
write_to_log = False
###Randomness calculator variables###
previous_address = 0
randomness_num_entries = 65536
randomness = 0
RANDOMNESS_MAX_VALUE = 128
################
# Parameters
TREE_ARITY = 8
TREE_ROOTS = 64  # Normally 64 leads to 7 levels
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
lazy_update_level_misses = [0] * TREE_LEVELS


class SHCT:
    """
    Signature History Counter Table implementation
    Based on the SHiP++ cache replacement policy
    """

    def __init__(self, num_entries=65536, counter_bits=3):
        """
        Initialize SHCT

        Args:
            num_entries: Number of entries in the table (default: 16K)
            counter_bits: Number of bits per counter (default: 3-bit)
        """
        self.num_entries = num_entries
        self.counter_bits = counter_bits
        self.max_counter = (1 << counter_bits) - 1  # 2^3 - 1 = 7
        self.min_counter = 0

        # Initialize all counters to 0
        self.counters = [0] * num_entries

        # Statistics
        self.hits = 0
        self.evictions = 0
        self.updates = 0
        # Level counters
        self.max_level_counter = 15
        self.level_counters = [0] * (TREE_LEVELS + 1)
        # Prefetch
        self.stride = [0] * num_entries
        self.previous_address = [0] * num_entries
        self.prefetch_state = [0] * num_entries  # 0 for transient, 1 for steady. Steady state means stride is constant

    def compare_stride(self, signature, address_diff):
        current_stride = self.stride[signature]
        if address_diff == current_stride:
            self.prefetch_state[signature] = 1
            return current_stride
        else:
            self.prefetch_state[signature] = -1
            return -1

    def store_address(self, signature, address_diff, address):
        self.stride[signature] = address_diff
        self.previous_address[signature] = address

    def get_signature(self, pc, is_prefetch=False):
        """
        Calculate signature from PC

        Args:
            pc: Program Counter
            is_prefetch: Whether this is a prefetch access

        Returns:
            14-bit signature
        """
        if is_prefetch:
            # SHiP++ enhancement: separate signatures for prefetch
            signature = ((pc << 1) + 1) & 0xFFFF  # 14-bit mask
        else:
            signature = (pc << 1) & 0xFFFF  # 14-bit mask

        return signature

    def increment_counter(self, signature, level):
        """
        Increment counter for a signature (on cache hit)

        Args:
            signature: 14-bit signature
        """
        if self.level_counters[level] < self.max_level_counter:
            self.level_counters[level] += 1
        index = signature % self.num_entries
        if self.counters[index] < self.max_counter:
            self.counters[index] += 1

    def decrement_counter(self, signature, level):
        """
        Decrement counter for a signature (on eviction without reuse)

        Args:
            signature: 14-bit signature
        """
        if self.level_counters[level] < self.max_level_counter:
            self.level_counters[level] -= 1
        index = signature % self.num_entries
        if self.counters[index] > self.min_counter:
            self.counters[index] -= 1

    def get_counter(self, signature, level):
        index = signature % self.num_entries
        return self.counters[index], self.level_counters[level]


class tree_table:
    def __init__(self, tree_arity, tree_roots, accuracy=TREE_LEVELS - 1):
        self.num_entries = 64 * 8 * 8 * 8
        self.counters = [0] * self.num_entries
        self.accuracy = accuracy
        self.max_counter = 16
        self.min_counter = 0

    def get_index(self, address, level):
        index = 0
        index_part = [0] * self.accuracy
        if address < TREE_START_ADDRESS:
            index = int(((address) // 64) // (TREE_ROOTS)) // TREE_ARITY ** 3
        else:
            if level == TREE_LEVELS - 1 or level == TREE_LEVELS - 2 or level == TREE_LEVELS - 3:
                tree_index = int((address - TREE_START_ADDRESS) // TREE_SIZE)
                level_address = tree_start_addresses[tree_index]
                for i in range(level):
                    level_address += block_size * TREE_ARITY ** i
                subtree_index = int((address - level_address) // 64) // (TREE_ARITY ** (level - 3))
                index = subtree_index + tree_index * TREE_ARITY * 3
        return index

    def increment_counter(self, address, level):
        index = self.get_index(address, level)
        if self.counters[index] < self.max_counter:
            self.counters[index] += 1

    def decrement_counter(self, address, level):
        index = self.get_index(address, level)
        if self.counters[index] > self.min_counter:
            self.counters[index] -= 1

    def decrement_counter_by_index(self, index):
        if self.counters[index] > self.min_counter:
            self.counters[index] -= 1

    def get_counter(self, address, level):
        index = self.get_index(address, level)
        return self.counters[index]

    def get_counter_by_index(self, index):
        return self.counters[index]

global_shct = SHCT()
global_tree_table = tree_table(TREE_ARITY, TREE_ROOTS, 5)


def find_parent_node(nodeAddr):
    tree_level_address = [0] * TREE_LEVELS
    print(f"Find the parent of {nodeAddr}")
    tree_index = int((nodeAddr - TREE_START_ADDRESS) // TREE_SIZE)
    if tree_index < 0:
        tree_index = int((nodeAddr - MEMORY_START_ADDR) // IND_TREE_SIZE)
        node_index = (nodeAddr - tree_index * (NUM_DATA_BLOCKS)) // (block_size)
        TreeNodeOffset = node_index * TREE_DATA_SIZE
        TreeNodeNegativeOffset = TREE_DATA_SIZE * DATA_MEM_SIZE / (TREE_ROOTS * block_size)
        treeNodeAddr = int(
            (TREE_START_ADDRESS + (tree_index + 1) * TREE_SIZE) - TreeNodeNegativeOffset + TreeNodeOffset)
        if treeNodeAddr >> 33 & 1 == 0:
            None
        return treeNodeAddr, (TREE_LEVELS - 1)
    tree_level_address[0] = tree_start_addresses[tree_index]
    i_treeNodeAddr = 6
    for i in range(1, TREE_LEVELS):
        tree_level_address[i] = tree_level_address[i - 1] + (TREE_DATA_SIZE << (TREE_ARITY_BITS * i))
        if tree_level_address[i] > nodeAddr:
            i_treeNodeAddr = i
            print(f"i_treeNodeAddr = {nodeAddr}")
            break

    node_index = (nodeAddr - tree_level_address[i_treeNodeAddr]) // TREE_DATA_SIZE
    node_index = int(node_index) >> TREE_ARITY_BITS
    TreeNodeOffset = node_index * TREE_DATA_SIZE
    parent_node_addr = int(tree_level_address[i_treeNodeAddr - 1] + TreeNodeOffset)
    return parent_node_addr, (i_treeNodeAddr - 1)


rereference_log = []


class log:
    def __init__(self):
        self.rereference_list = []

    def add_event(self, evicted, inserted, way0_address, way1_address, way2_address, way3_address, way4_address,
                  way5_address, way6_address):
        event = {
            "evicted": evicted,
            "inserted": inserted,
            "way0": way0_address,
            "way1": way1_address,
            "way2": way2_address,
            "way3": way3_address,
            "way4": way4_address,
            "way5": way5_address,
            "way6": way6_address
        }
        self.rereference_list.append(event)

    def resolve(self, address):
        for event in self.rereference_list:
            if address == event["way0"]:
                event["way0"] = -1
            elif address == event["way1"]:
                event["way1"] = -1
            elif address == event["way2"]:
                event["way2"] = -1
            elif address == event["way3"]:
                event["way3"] = -1
            elif address == event["way4"]:
                event["way4"] = -1
            elif address == event["way5"]:
                event["way5"] = -1
            elif address == event["way6"]:
                event["way6"] = -1
            elif address == event["inserted"]:
                event["inserted"] = -1

            if address == event["evicted"]:
                if write_to_log == True:
                    with open("rereference_log.txt", "a") as file:
                        file.write(str(instructions_number))
                        file.write("instruction the Evicted node ")
                        file.write(str(event["evicted"]))
                        file.write(" was rereferenced before ")
                        for key, i in event.items():
                            if i != -1 and (key.startswith("way") or key == "inserted"):
                                file.write(str(i))
                                file.write(" ")
                        file.write("\n")
                self.rereference_list.remove(event)
            elif event["way0"] == -1 and event["way1"] == -1 and event["way2"] == -1 and event["way3"] == -1 and event[
                "way4"] == -1 and event["way5"] == -1 and event["way6"] == -1 and event["inserted"] == -1:
                self.rereference_list.remove(event)


rr_log = log()


class HHT():
    def __init__(self):
        self.num_entries = 1000
        self.entries = {i: [None, None, None, None, 0] for i in range(2 ** (MEMORY - 17))}

    def get_expected_hit_counter(self, address):
        tag = address >> 17
        expected_hit_counter = 0
        # Check valid bit
        if self.entries[tag][4]:
            for i in range(4):
                expected_hit_counter += self.entries[tag][i]
            return (expected_hit_counter // 4), 1  # Return the average of the four most recent
        else:
            return 0, 0

    def store_expected_hit_counter(self, address, hit_counter):
        tag = address >> 17
        self.entries[tag].pop(3)
        self.entries[tag].insert(0, hit_counter)
        for i in range(4):
            if self.entries[tag][i] == None:
                return
        self.entries[tag][4] = 1


hht = HHT()
