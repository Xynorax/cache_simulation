import util
from Parameters import *
from benchmarks import *
from cache import Cache
from memory import Memory


def read(address, memory, cache):
    """Read a byte from cache."""
    cache_block = cache.read(address)
    global execution_time
    if cache_block:
        global hits
        hits += 1
        global cache_hit
        cache_hit = True  # Set as true to stop reading parent nodes+
        execution_time = execution_time + cache._mapping_pol * 0.1  # Add execution time depending on associativity (in cycles)
    else:
        block = memory.get_block(address)
        victim_info = cache.load(address, block)
        cache_block = cache.read(address)

        global misses
        misses += 1
        execution_time = execution_time + DRAM_ACCESS_TIME  # Add execution time for a cache miss
        # Write victim line's block to memory if replaced
        if victim_info:
            memory.set_block(victim_info[0], victim_info[1])

    return cache_block[cache.get_offset(address)]


def write(address, byte, memory, cache):
    """Write a byte to cache."""
    written = cache.write(address, byte)
    global execution_time
    global write_misses
    global write_hits
    if written:

        write_hits += 1
    else:
        write_misses += 1
        execution_time = execution_time + DRAM_ACCESS_TIME  # Add execution time for a cache miss
    if write_policy == Cache.WRITE_THROUGH:
        # Write block to memory
        block = memory.get_block(address)
        block[cache.get_offset(address)] = byte
        memory.set_block(address, block)
    elif write_policy == Cache.WRITE_BACK:
        if not written:
            # Write block to cache
            block = memory.get_block(address)
            cache.load(address, block)
            cache.write(address, byte)


command = None


# while (command != "quit"):
def initiate_command(cmd):
    operation = cmd
    operation = operation.split()

    try:
        command = operation[0]
        params = operation[1:]
        if command == "read" and len(params) == 1:
            address = int(params[0])
            byte = read(address, memory, cache)

            print("Byte 0x" + util.hex_str(byte, 2) + f" read from " +
                  util.bin_str(address, MEMORY), f"{address}")

        elif command == "write" and len(params) == 2:
            address = int(params[0])
            byte = int(params[1])
            write(address, byte, memory, cache)

            print("Byte 0x" + util.hex_str(byte, 2) + " written to " +
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

    except IndexError:
        print("\nERROR: out of bounds\n", flush=True)
    except:
        print("\nERROR: incorrect syntax\n", flush=True)


class MemoryAccess:
    def __init__(self, access_type, address, byte=00):
        self.access_type = access_type
        self.counter_addresses = [0] * (TREE_LEVELS)
        self.byte = byte
        if access_type == "read":
            initiate_command(f"read {address}")
        elif access_type == "write":
            initiate_command(f"read {address}")
            initiate_command(f"write {address} {self.byte}")
        global cache_hit
        cache_hit = False
        for level in range(TREE_LEVELS):
            self.compute_counter_addresses(address, level)
        self.access_counter()

    def access_counter(self):
        if self.access_type == "read":
            for i in reversed(range(len(self.counter_addresses))):
                initiate_command(f"read {self.counter_addresses[i]}")
                global cache_hit
                if (cache_hit):
                    cache_hit = False
                    break
        elif self.access_type == "write":
            for i in reversed(range(len(self.counter_addresses))):
                initiate_command(f"read {self.counter_addresses[i]}")
                initiate_command(f"write {self.counter_addresses[i]} {self.byte}")

    def compute_counter_addresses(self, cpu_address, current_level):
        # 1. Compute root index (which tree protects this address)
        root_index = int((cpu_address - MEMORY_START_ADDR) // IND_TREE_SIZE)

        # 2 . Compute leaf node index (data block number within the tree)
        tree_offset = int(root_index * IND_TREE_SIZE)
        dataNodeNum = int((cpu_address - MEMORY_START_ADDR - tree_offset) // block_size)
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
    size = 100  # number of random numbers you want
    random_array = [random.randint(size, mem_size / 2) for _ in range(size)]
    for i in range(len(random_array)):
        MemoryAccess("read", random_array[i])
    initiate_command("stats")
    print(f"Execution time: {execution_time}")


def benchmark_manual():  ##Benchmark 2 - Manually inputed values
    size = 2  # array length
    array = [123]  # list(range(0, 10, 1))
    for i in range(len(array)):
        MemoryAccess("read", array[i])
        MemoryAccess("write", array[i], )
    initiate_command("stats")
    # initiate_command("printmem 0 20")
    # initiate_command("printcache 0 20")


def benchmark_fir():  # Benchmark 3 FIR filter
    N = 3  # Order of the filter
    input_length = 3
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
        upper_bound = int(memory._size / 2) - 1
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


for k in range(len(simulations)):
    execution_time = 0  # Reset execution time for each simulation
    global hits
    hits = 0
    global misses
    misses = 0
    memory = Memory(mem_size, block_size)
    cache = Cache(simulations[k][1], simulations[k][0], simulations[k][2],
                  simulations[k][3], simulations[k][4], simulations[k][5])

    mapping_str = "{0}-way associative".format(simulations[k][3])
    print("\nMemory size: " + str(mem_size) +
          " bytes (" + str(mem_size // block_size) + " blocks)")
    print("Cache size: " + str(cache_size) +
          " bytes (" + str(cache_size // block_size) + " lines)")
    print("Block size: " + str(block_size) + " bytes")
    print("Mapping policy: " + ("direct" if simulations[k][3] == 1 else mapping_str) + "\n")

    benchmark_seq_read()
    Execution_Times[k] = execution_time
    cache_hits_end[k] = hits
    cache_misses_end[k] = misses

print(simulations)
print("Execution times:")
min_value = min(Execution_Times)
Execution_Times = [time / min_value for time in Execution_Times]
print(Execution_Times)
print("Cache hits:")
print(cache_hits_end)
print("Cache misses:")
print(cache_misses_end)
