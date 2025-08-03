import random

import numpy as np
import util
from Parameters import *
from cache import Cache
from translation import *


def read(address, memory, cache, pc, level=TREE_LEVELS):
    """Read a byte from cache."""
    cache_block = cache.read(address, pc)
    global cc_set_access_counter
    global dc_set_access_counter
    global cc_set_eviction_counter
    global dc_set_eviction_counter
    global LLC_total_set_access_counter
    global LLC_dc_set_access_counter
    global LLC_cc_set_access_counter
    if cache._type == "level1_cc":
        set_mask = (cache._size // (cache._block_size * cache._mapping_pol)) - 1
        set_num = (address >> cache._set_shift) & set_mask
        cc_set_access_counter[set_num][level] += 1
    elif cache._type == "level1":
        set_mask = (cache._size // (cache._block_size * cache._mapping_pol)) - 1
        set_num = (address >> cache._set_shift) & set_mask
        dc_set_access_counter[set_num] += 1

    global execution_time
    global instructions_number
    if cache_block:
        if cache._type == "data_cache":
            if instructions_number > WARMUP_INSTRUCTIONS:
                global hits
                hits += 1
        elif cache._type == "level1":
            if instructions_number > WARMUP_INSTRUCTIONS:
                global l1_hits
                l1_hits += 1
        elif cache._type == "level1_cc":
            if instructions_number > WARMUP_INSTRUCTIONS:
                global l1_hits_cc
                l1_hits_cc += 1
        elif cache._type == "ctr_cache":
            if instructions_number > WARMUP_INSTRUCTIONS:
                global ctr_cache_hits
                global LLC_ctr_level_hits
                ctr_cache_hits += 1
                LLC_ctr_level_hits[level] += 1
        if instructions_number > WARMUP_INSTRUCTIONS and level < TREE_LEVELS:
            if cache._type == "level1_cc":
                level_hits_l1[level] += 1
            elif cache._type == "data_cache":
                level_hits[level] += 1
        global cache_hit
        cache_hit = True  # Set as true to stop reading parent nodes
        # execution_time = execution_time + cache._mapping_pol * 0.4  # Add execution time depending on associativity (in cycles)
    else:
        block = bytearray(8)
        if cache._type == "level1":
            cache.load(address, block, pc)
            set_mask = (cache._size // (cache._block_size * cache._mapping_pol)) - 1
            set_num = (address >> cache._set_shift) & set_mask
            dc_set_miss_counter[set_num] += 1
            if instructions_number > WARMUP_INSTRUCTIONS:
                global l1_misses
                l1_misses += 1
            return 0
        # block = memory.get_block(address)
        if cache._type == "level1_cc":
            cache.load(address, block, pc)
            set_mask = (cache._size // (cache._block_size * cache._mapping_pol)) - 1
            set_num = (address >> cache._set_shift) & set_mask
            cc_set_miss_counter[set_num][level] += 1
            if instructions_number > WARMUP_INSTRUCTIONS:
                if level < TREE_LEVELS:
                    level_misses_l1[level] += 1
                global l1_misses_cc
                l1_misses_cc += 1
            return 0
        if level > -1:  # flipped because levels are flipped in the array
            victim_info = cache.load(address, block, pc)
            # if victim_info:
            # memory.set_block(victim_info[0], victim_info[1])

        if cache._type == "data_cache":
            set_mask = (cache._size // (cache._block_size * cache._mapping_pol)) - 1
            set_num = (address >> cache._set_shift) & set_mask
            if level == TREE_LEVELS:
                LLC_dc_set_miss_counter[set_num] += 1
            LLC_total_set_miss_counter[set_num] += 1
            if instructions_number > WARMUP_INSTRUCTIONS:
                global misses
                misses += 1
                if level < TREE_LEVELS:
                    level_misses[level] += 1
        elif cache._type == "ctr_cache":
            set_mask = (cache._size // (cache._block_size * cache._mapping_pol)) - 1
            set_num = (address >> cache._set_shift) & set_mask
            LLC_cc_set_miss_counter[set_num][level] += 1
            if instructions_number > WARMUP_INSTRUCTIONS:
                global ctr_cache_misses
                ctr_cache_misses += 1
                global LLC_ctr_level_misses
                LLC_ctr_level_misses[level] += 1



        # execution_time = execution_time + DRAM_ACCESS_TIME  # Add execution time for a cache miss
        # Write victim line's block to memory if replaced

    return 1


def write(address, byte, memory, cache, pc, level=TREE_LEVELS):
    """Write a byte to cache."""
    written = cache.write(address, byte, pc)
    global execution_time
    global write_misses
    global write_hits
    global instructions_number
    global cc_set_access_counter
    global dc_set_access_counter
    global LLC_total_set_access_counter
    global LLC_dc_set_access_counter
    global LLC_cc_set_access_counter

    if cache._type == "level1_cc":
        set_mask = (cache._size // (cache._block_size * cache._mapping_pol)) - 1
        set_num = (address >> cache._set_shift) & set_mask
        cc_set_access_counter[set_num][level] += 1
    elif cache._type == "level1":
        set_mask = (cache._size // (cache._block_size * cache._mapping_pol)) - 1
        set_num = (address >> cache._set_shift) & set_mask
        dc_set_access_counter[set_num] += 1
    if written:
        if cache._type == "data_cache":
            if instructions_number > WARMUP_INSTRUCTIONS:
                global hits
                hits += 1
        elif cache._type == "level1_cc":
            if instructions_number > WARMUP_INSTRUCTIONS:
                global l1_hits_cc
                l1_hits_cc += 1
        elif cache._type == "level1":
            if instructions_number > WARMUP_INSTRUCTIONS:
                global l1_hits
                l1_hits += 1
        elif cache._type == "ctr_cache":
            if instructions_number > WARMUP_INSTRUCTIONS:
                global ctr_cache_hits
                global LLC_ctr_level_hits
                ctr_cache_hits += 1
                LLC_ctr_level_hits[level] += 1
        if instructions_number > WARMUP_INSTRUCTIONS and level < TREE_LEVELS:
            if cache._type == "level1_cc":
                level_hits_l1[level] += 1
            elif cache._type == "data_cache":
                level_hits[level] += 1
    else:
        block = bytearray(8)
        if cache._type == "data_cache":
            set_mask = (cache._size // (cache._block_size * cache._mapping_pol)) - 1
            set_num = (address >> cache._set_shift) & set_mask
            if level == TREE_LEVELS:
                LLC_dc_set_miss_counter[set_num] += 1
            LLC_total_set_miss_counter[set_num] += 1
            if instructions_number > WARMUP_INSTRUCTIONS:
                global misses
                misses += 1
                if level < TREE_LEVELS:
                    level_misses[level] += 1
        elif cache._type == "level1_cc":
            set_mask = (cache._size // (cache._block_size * cache._mapping_pol)) - 1
            set_num = (address >> cache._set_shift) & set_mask
            cc_set_miss_counter[set_num][level] += 1
            cache.load(address, block, pc, WB_insertion=1)
            cache.write(address, byte, pc)
            if instructions_number > WARMUP_INSTRUCTIONS:
                global l1_misses_cc
                l1_misses_cc += 1
                if level < TREE_LEVELS:
                    level_misses_l1[level] += 1
            return 0
        elif cache._type == "level1":
            set_mask = (cache._size // (cache._block_size * cache._mapping_pol)) - 1
            set_num = (address >> cache._set_shift) & set_mask
            dc_set_miss_counter[set_num] += 1
            cache.load(address, block, pc, WB_insertion=1)
            cache.write(address, byte, pc)
            if instructions_number > WARMUP_INSTRUCTIONS:
                global l1_misses
                l1_misses += 1
            return 0

        elif cache._type == "ctr_cache":
            set_mask = (cache._size // (cache._block_size * cache._mapping_pol)) - 1
            set_num = (address >> cache._set_shift) & set_mask
            LLC_cc_set_miss_counter[set_num][level] += 1
            if instructions_number > WARMUP_INSTRUCTIONS:
                global ctr_cache_misses
                ctr_cache_misses += 1
                global LLC_ctr_level_misses
                LLC_ctr_level_misses[level] += 1

        # execution_time = execution_time + DRAM_ACCESS_TIME  # Add execution time for a cache miss
    if write_policy == Cache.WRITE_THROUGH:  # or level > 0 Flipped because levels are flipped in the array
        # Write block to memory
        #block = memory.get_block(address)
        block[cache.get_offset(address)] = byte
        #memory.set_block(address, block)
    elif write_policy == Cache.WRITE_BACK:
        if not written:

            # Write block to cache
            # block = memory.get_block(address)
            cache.load(address, block, pc, WB_insertion=1)
            cache.write(address, byte, pc)

    return 1
command = None


# while (command != "quit"):
def initiate_command(cmd, ctr=False, pc=0, level_inversed=TREE_LEVELS):
    operation = cmd
    operation = operation.split()

    command = operation[0]
    params = operation[1:]
    if command == "read" and len(params) == 1:
        address = int(params[0])
        if ctr == False:
            if read(address, memory, l1cache, pc, level_inversed) == 0:
                read(address, memory, LLC, pc, level_inversed)
        else:
            if read(address, memory, l1_cache_cc, pc, level_inversed) == 0:
                read(address, memory, LLC_ctr, pc, level_inversed)

        print(f" read from " +
              util.bin_str(address, MEMORY), f"{address}")

    elif command == "write" and len(params) == 2:
        address = int(params[0])
        byte = int(params[1])
        if ctr == False:
            if write(address, byte, memory, l1cache, pc, level_inversed) == 0:
                write(address, byte, memory, LLC, pc, level_inversed)
        else:
            if write(address, byte, memory, l1_cache_cc, pc, level_inversed) == 0:
                write(address, byte, memory, LLC_ctr, pc, level_inversed)

        print(" written to " +
              util.bin_str(address, MEMORY), f"{address}")

    elif command == "randread" and len(params) == 1:
        amount = int(params[0])

        for i in range(amount):
            address = random.randint(0, mem_size - 1)
            read(address, memory, cache)

        print("\n" + str(amount) + " bytes read from memory\n", flush=True)

    elif command == "randwrite" and len(params) == 1:
        amount = int(params[0])

        for i in range(amount):
            address = random.randint(0, mem_size - 1)
            byte = util.rand_byte()
            write(address, byte, memory, cache)

        print("\n" + str(amount) + " bytes written to memory\n", flush=True)

    elif command == "printcache" and len(params) == 2:
        start = int(params[0])
        amount = int(params[1])

        cache.print_section(start, amount)

    elif command == "printmem" and len(params) == 2:
        start = int(params[0])
        amount = int(params[1])

        memory.print_section(start, amount)

    elif command == "stats" and len(params) == 0:
        ratio = (hits / ((hits + misses) if misses else 1)) * 100

        print("Hits: {0} | Misses: {1}".format(hits, misses), flush=True)
        print("Hit/Miss Ratio: {0:.2f}%".format(ratio), flush=True)

    elif command != "quit":
        print("\nERROR: invalid command\n", flush=True)

    # except IndexError:
    #    print("\nERROR: out of bounds\n", flush=True)
    # except:
    #    print("\nERROR: incorrect syntax\n", flush=True)


class MemoryAccess:
    def __init__(self, access_type, address, byte=00, pc=0):
        self.access_type = access_type
        self.counter_addresses = [0] * (TREE_LEVELS)
        self.byte = byte
        self._pc = pc
        global cache_hit
        if access_type == "read":
            initiate_command(f"read {address}", False, self._pc)
            if (cache_hit):
                cache_hit = False
                return
        elif access_type == "write":
            initiate_command(f"read {address}", False, self._pc)
            initiate_command(f"write {address} {self.byte}", False, self._pc)

        cache_hit = False
        root_index = int((address - MEMORY_START_ADDR) // IND_TREE_SIZE)
        tree_offset = int(root_index * IND_TREE_SIZE)
        dataNodeNum = int((address - MEMORY_START_ADDR - tree_offset) // block_size)
        for level in range(TREE_LEVELS):
            self.compute_counter_addresses(address, level, root_index, tree_offset, dataNodeNum)
        self.access_counter()

    def access_counter(self):
        if self.access_type == "read":
            for i in reversed(range(len(self.counter_addresses))):
                initiate_command(f"read {self.counter_addresses[i]}", True, self._pc, i)
                global level_access_counter
                level_access_counter[i] += 1
                global cache_hit
                if (cache_hit):
                    cache_hit = False
                    break
        elif self.access_type == "write":
            for i in reversed(range(len(self.counter_addresses))):
                initiate_command(f"read {self.counter_addresses[i]}", True, self._pc, i)
                level_access_counter[i] += 2
                initiate_command(f"write {self.counter_addresses[i]} {self.byte}", True, self._pc, i)

    def compute_counter_addresses(self, cpu_address, current_level, root_index, tree_offset, dataNodeNum):

        global tree_level_address

        if current_level == 0:
            treeNodeAddr = int(tree_start_addresses[root_index])
            tree_level_address = tree_start_addresses[root_index]
        else:
            shift = TREE_ARITY_BITS * (TREE_LEVELS - 1 - current_level)
            node_index = dataNodeNum >> shift
            TreeNodeOffset = node_index * TREE_DATA_SIZE
            tree_level_address = tree_level_address + (TREE_DATA_SIZE << (TREE_ARITY_BITS * current_level))
            treeNodeAddr = int(tree_level_address + TreeNodeOffset)

        # print(f"Tree node address = {util.bin_str(treeNodeAddr, MEMORY)}, {treeNodeAddr}")
        self.counter_addresses[current_level] = treeNodeAddr

        return 1


def benchmark_random_reads():  ##Benchmark 1 - random read access
    size = 10000  # number of random numbers you want
    random_array = [random.randint(size, (mem_size / 2) - 1) for _ in range(size)]
    for i in range(len(random_array)):
        MemoryAccess("read", random_array[i])
    initiate_command("stats")
    print(f"Execution time: {execution_time}")


def benchmark_manual():  ##Benchmark 2 - Manually inputed values
    global instructions_number
    instructions_number = 999999999
    size = 2  # array length
    array = [123]
    # for i in range(len(array)):
    MemoryAccess("read", 0)
    MemoryAccess("read", (mem_size // 2) // 8)
    MemoryAccess("read", (mem_size // 2) * 7 // 8)
    MemoryAccess("read", (mem_size // 2) * 6 // 8)
    MemoryAccess("read", (mem_size // 2) * 5 // 8)
    MemoryAccess("read", (mem_size // 2) * 4 // 8)
    MemoryAccess("read", (mem_size // 2) * 3 // 8)
    MemoryAccess("read", (mem_size // 2) * 2 // 8)
    initiate_command("stats")
    # initiate_command("printmem 0 20")
    # initiate_command("printcache 0 20")


def benchmark_fir():  # Benchmark 3 FIR filter
    N = 40  # Order of the filter
    input_length = 50000
    input_array = [random.randint(0, 100) for _ in range(input_length)]
    coeffs = [random.randint(0, 100) for _ in range(N)]  # N-tap filter
    N = len(coeffs)
    for i in range(N):
        MemoryAccess("write", i, coeffs[i])
    for i in range(input_length):
        MemoryAccess("write", i + N, input_array[i])
    for j in range(input_length + 1):
        for i in range(N):
            MemoryAccess("read", i)
            if ((i + j) - N >= 0):
                MemoryAccess("read", i + N)
        MemoryAccess("write", input_length + N + j, 0)
    initiate_command("stats")

def benchmark_seq_access():  # Benchmark 4 Sequential access
    access_times = 25700
    for i in range(access_times):
        MemoryAccess("write", i)
    for j in range(access_times):
        MemoryAccess("read", j)
    initiate_command("stats")
    print(f"Execution time: {execution_time}")


def benchmark_seq_read():  # Benchmark 5 Sequential read
    access_times = 70
    for j in range(access_times):
        MemoryAccess("read", j)
    initiate_command("stats")
    print(f"Execution time: {execution_time}")
def benchmark_binary_search():  # Benchmark 6 binary search
    searches = 10000
    for z in range(searches):
        upper_bound = int(memory_size / 2) - 1
        random_address = random.randint(0, upper_bound)
        low = 0
        high = upper_bound  # The maximum possible address in our search space
        attempts = 0
        while low <= high:
            attempts += 1
            address_to_search = (low + high) // 2
            MemoryAccess("read", address_to_search)  # Simulate memory access
            if address_to_search == random_address:
                print(f"SUCCESS: Found {random_address} at address {address_to_search} in {attempts} attempts!")
                break
            elif address_to_search < random_address:
                low = address_to_search + 1
            else:  # address_to_search > random_address
                high = address_to_search - 1
        else:  # This 'else' block runs if the while loop finishes without a 'break'
            print(f"FAIL: Target {random_address} not found after {attempts} attempts. Search space exhausted.")


def benchmark_trace(MAX_INSTRUCTIONS):
    mm = MemoryManager()
    global instructions_number
    instructions_number = 0
    TRACE_FILE_PATH = "D:\\Youssef\\TUM\\ChampSim\\400.perlbench-41B.champsimtrace"
    NUMPY_TRACE_PATH = "D:\\Youssef\\TUM\\ChampSim\\400.perlbench-41B.npy"
    NUMPY_TRACE_PATH = "D:\\Youssef\\TUM\\ChampSim\\429.mcf-51B.npy"
    BATCH = 1
    instr_batch = np.load(NUMPY_TRACE_PATH)
    random_64byte = 0xEE
    random_byte = 0xA
    # for i in range(0, MAX_INSTRUCTIONS, BATCH):
    # instr_batch = parse_champsim_trace_line_fast(TRACE_FILE_PATH, i, BATCH)
    for x in range(MAX_INSTRUCTIONS):
        instr = instr_batch[x]
        instructions_number += 1
        print(f"Instruction number:{instructions_number}")
        program_counter = instr[0]
        if instr[9] == 0 and instr[10] == 0 and instr[11] == 0 and instr[12] == 0 and instr[13] == 0 and instr[14] == 0:
            None
        else:
            for k in range(2):
                dest_addr = instr[9 + k]
                if dest_addr != 0:  # Skip if no destination memory
                    dest_addr = mm.translate_virtual_to_physical(dest_addr)
                    print(f"Virtual Address:{dest_addr}")
                    MemoryAccess("write", dest_addr, random_byte, program_counter)
            for k in range(4):
                src_addr = instr[11 + k]
                if src_addr != 0:  # Skip if 0
                    print(f"Virtual Address:{src_addr}")
                    src_addr = mm.translate_virtual_to_physical(src_addr)
                    MemoryAccess("read", src_addr, pc=program_counter)

for k in range(len(simulations)):
    l1_cache_size = (2 ** 15) // 2
    global cc_set_access_counter
    global dc_set_access_counter
    levels_array = TREE_LEVELS * [0]
    cc_set_access_counter = [[0 for _ in range(TREE_LEVELS)] for _ in range((l1_cache_size // block_size) // 4)]
    dc_set_access_counter = ((l1_cache_size // block_size) // 4) * [0]

    global LLC_total_set_miss_counter
    global LLC_dc_set_miss_counter
    global LLC_cc_set_miss_counter
    LLC_total_set_miss_counter = ((simulations[k][1] // block_size) // 4) * [0]
    LLC_dc_set_miss_counter = ((simulations[k][1] // block_size) // 4) * [0]
    LLC_cc_set_miss_counter = [[0 for _ in range(TREE_LEVELS)] for _ in range((simulations[k][1] // block_size) // 4)]

    global dc_set_miss_counter
    global cc_set_miss_counter
    cc_set_miss_counter = [[0 for _ in range(TREE_LEVELS)] for _ in range((l1_cache_size // block_size) // 4)]
    dc_set_miss_counter = ((l1_cache_size // block_size) // 4) * [0]

    execution_time = 0  # Reset execution time for each simulation
    global hits
    hits = 0
    global misses
    misses = 0
    # memory = Memory(mem_size, block_size)
    memory = 0


    LLC = Cache(simulations[k][1] // 2, simulations[k][0], simulations[k][2],
                simulations[k][3], simulations[k][4], simulations[k][5], type="data_cache")
    # def __init__(self, size, mem_size, block_size, mapping_pol, replace_pol, write_pol, type="data_cache"):

    LLC_ctr = Cache(simulations[k][1] // 2, simulations[k][0], simulations[k][2],
                    mapping_pol=2 ** 4, replace_pol=simulations[k][7], write_pol=simulations[k][5], type="ctr_cache")

    l1cache = Cache(l1_cache_size, simulations[k][0], simulations[k][2], 2 ** 2, "LRU", write_pol="WB",
                    type="level1")
    l1_cache_cc = Cache(l1_cache_size, simulations[k][0], simulations[k][2], 2 ** 2, "LRU", write_pol="WB",
                        type="level1_cc")

    mapping_str = "{0}-way associative".format(simulations[k][3])
    print("\nMemory size: " + str(mem_size) +
          " bytes (" + str(mem_size // block_size) + " blocks)")
    print("Cache size: " + str(cache_size) +
          " bytes (" + str(cache_size // block_size) + " lines)")
    print("Block size: " + str(block_size) + " bytes")
    print("Mapping policy: " + ("direct" if simulations[k][3] == 1 else mapping_str) + "\n")

    benchmark_trace(5000000)
    # benchmark_random_reads()
    # benchmark_manual()
    # benchmark_random_reads()
    #benchmark_manual()
    Execution_Times[k] = execution_time
    cache_hits_end[k] = hits
    cache_misses_end[k] = misses
    hit_percent[k] = hits / (hits + misses) if (hits + misses) != 0 else 0.0
print(f"Warm up instructions: {WARMUP_INSTRUCTIONS}")
print(f"Size of L1 cache: {l1_cache_size}")
print(simulations)
print("Execution times:")
min_value = min(Execution_Times)
Execution_Times = [time / min_value for time in Execution_Times] if (min_value) != 0 else 0.0
print(Execution_Times)
print("-----LLC--------")
print("LLC Cache hits:")
print(cache_hits_end)
print("LLC Cache misses:")
print(cache_misses_end)
print("Hit percent:")
print(hit_percent)
print("Counter Level hits in LLC:")
print(level_hits)
print("Counter Level misses in LLC:")
print(level_misses)
print("-----L1 DC Cache--------")
print("L1 Cache Hits")
print(l1_hits)
print("L1 Cache Misses")
print(l1_misses)
print("-----L1 CC Cache--------")
print("Total hits in L1 CC cache")
print(l1_hits_cc)
print("Total misses in L1 CC cache")
print(l1_misses_cc)
print("Counter Level hits in L1 CC Cache:")
print(level_hits_l1)
print("Counter Level misses in L1 CC Cache:")
print(level_misses_l1)

print("Tree Levels:")
print(TREE_LEVELS)
print("LLC Counter cache hits")
print(ctr_cache_hits)
print("LLC Counter cache misses")
print(ctr_cache_misses)
print(ctr_cache_hits / (ctr_cache_hits + ctr_cache_misses))
print("Counter level hits in LLC counter cache")
print(LLC_ctr_level_hits)
print("Counter level misses in LLC counter cache")
print(LLC_ctr_level_misses)

# print("DC set access counter")
# print(dc_set_access_counter)
# print("CC set access counter")
# print(cc_set_access_counter)

# print("LLC Total set miss counter")
#print(LLC_total_set_miss_counter)
# print("LLC DC set miss counter")
# print(LLC_dc_set_miss_counter)
# print("LLC CC set miss counter")
#print(LLC_cc_set_miss_counter)

# print("DC set miss counter")
# print(dc_set_miss_counter)
# print("CC set miss counter")
#print(cc_set_miss_counter)

# print("LLC CC set miss counter")
#print(LLC_cc_set_miss_counter)
