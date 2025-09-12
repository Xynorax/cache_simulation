import random
from math import log

import Parameters
import tensorflow as tf
import util
from NN_replacementv2 import build_state, rl
from Parameters import smart_set_indexing, randomness, randomness_num_entries
from line import Line


class Cache:
    """Class representing a processor's main cache."""

    # Replacement policies
    LRU = "LRU"
    LFU = "LFU"
    FIFO = "FIFO"
    RAND = "RAND"
    RLR = "RLR"
    ship_plus = "ship_plus"
    modified_LRU = "modified_LRU"
    # Mapping policies
    WRITE_BACK = "WB"
    WRITE_THROUGH = "WT"

    def __init__(self, size, mem_size, block_size, mapping_pol, replace_pol,
                 write_pol, type="data_cache"):
        self._lines = [Line(block_size) for i in range(size // block_size)]
        self.num_sets = (size // block_size) // mapping_pol
        self.sets = [
            [Line(block_size) for _ in range(mapping_pol)]
            for _ in range(self.num_sets)
        ]
        self.plru_bits = [
            [0] * (mapping_pol - 1) for _ in range(self.num_sets)
        ]
        self._mapping_pol = mapping_pol  # Mapping policy
        self._replace_pol = replace_pol  # Replacement policy
        self._write_pol = write_pol  # Write policy

        self._size = size  # Cache size
        self._mem_size = mem_size  # Memory size
        self._block_size = block_size  # Block size
        self._type = type
        # Bit offset of cache line tag
        self._tag_shift = int(log(self._size // (self._mapping_pol * self._block_size), 2)) + int(
            log(self._block_size, 2))
        # Bit offset of cache line set
        self._set_shift = int(log(self._block_size, 2))
        if self._replace_pol == Cache.ship_plus:
            self._shct = self.SHCT()
            total_sets = size // (block_size * mapping_pol)
            spacing = total_sets // 16
            self.sampled_sets = {i for i in range(0, total_sets, spacing)}

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

        def increment_counter(self, signature):
            """
            Increment counter for a signature (on cache hit)

            Args:
                signature: 14-bit signature
            """
            index = signature % self.num_entries
            if self.counters[index] < self.max_counter:
                self.counters[index] += 1

        def decrement_counter(self, signature):
            """
            Decrement counter for a signature (on eviction without reuse)

            Args:
                signature: 14-bit signature
            """
            index = signature % self.num_entries
            if self.counters[index] > self.min_counter:
                self.counters[index] -= 1

        def get_counter(self, signature):
            index = signature % self.num_entries
            return self.counters[index]



    def read(self, address, pc, level):
        """Read a block of memory from the cache.

        :param int address: memory address for data to read from cache
        :return: block of memory read from the cache (None if cache miss)
        """
        tag = self._get_tag(address)  # Tag of cache line
        set = self._get_set(address)  # Set of cache lines
        line = None
        way_index = -1
        # Search for cache line within set
        for candidate in set:
            way_index += 1
            if candidate.tag == tag and candidate.valid:
                line = candidate
                break
        # Update use bits of cache line
        if line:
            if (self._replace_pol == Cache.LRU or
                    self._replace_pol == Cache.LFU or self._replace_pol == Cache.modified_LRU):
                self._update_use(line, set, level)
            elif (self._replace_pol == Cache.RLR):
                self._update_rlr(line, set)
            elif (self._replace_pol == "pseudo_LRU"):
                set_mask = (self._size // (self._block_size * self._mapping_pol)) - 1
                set_num = (address >> self._set_shift) & set_mask
                self._plru_update(set_num, way_index)
            elif (self._replace_pol == Cache.ship_plus):
                set_idx = (address >> self._set_shift) & ((self._size // (self._block_size * self._mapping_pol)) - 1)
                if set_idx in self.sampled_sets:
                    if line.r == 0:
                        self._shct.increment_counter(line.signature)
                        line.r = 1
                line.rrpv = 0
            elif self._replace_pol == "RL":
                rl.resolve(address)
                if line.hits < 1000:
                    line.hits += 1
                line.preuse_distance = line.age_counter
                for index in range(len(set)):
                    if set[index].age_counter < 3000:
                        set[index].age_counter += 1
                line.age_counter = 0



        return line.data if line else line

    def load(self, address, data, pc, level, WB_insertion=0, lazy_update=0):
        """Load a block of memory into the cache.

        :param int address: memory address for data to load to cache
        :param list data: block of memory to load into cache
        :return: tuple containing victim address and data (None if no victim)
        """
        tag = self._get_tag(address)  # Tag of cache line
        set = self._get_set(address)  # Set of cache lines
        victim_info = None

        # Select the victim
        if (self._replace_pol == Cache.LRU or
                self._replace_pol == Cache.LFU or
                self._replace_pol == Cache.FIFO):
            victim = set[0]
            victim = self._find_victim(set)
            victim.use = max(line.use for line in set) + 1
            if self._replace_pol == Cache.FIFO:
                self._update_use(victim, set)
        elif self._replace_pol == Cache.modified_LRU:
            signature = ((pc << 1) + 1) & 0xFFFF  # 14-bit mask
            index = signature % randomness_num_entries
            randomness[index]
            victim = set[0]
            victim = self._find_victim(set)
            victim.use = min(line.use for line in set) - 1
            for line in set:
                if randomness[index] > 40:
                    if line.level > level and victim.use < line.use:
                        victim.use = line.use + 1
                elif randomness[index] <= 40 and randomness[index] >= 19:
                    if (line.level !=
                        4 or line.level != 5) and victim.use < line.use:
                        victim.use = line.use + 1
                elif randomness[index] > 9 and randomness[index] <= 18:
                    if line.level != 6 and victim.use < line.use:
                        victim.use = line.use + 1
                elif randomness[index] < 10:
                    if line.level < level and victim.use < line.use:
                        victim.use = line.use + 1


        elif self._replace_pol == Cache.RAND:
            index = random.randint(0, self._mapping_pol - 1)
            victim = set[index]

        elif self._replace_pol == Cache.ship_plus:
            victim = None
            for index in range(len(set)):  # Check if a line in the set is free
                if set[index].valid == 0:
                    victim = set[index]
                    break
            if self._type == "ctr_cache":
                Parameters.total_evictions += 1
            if victim == None:
                while victim == None:
                    for index in range(len(set)):  # Check which line has RRPV = 3
                        if set[index].rrpv == 3:
                            victim = set[index]
                            break
                    if victim != None:
                        break
                    for item in set:
                        item.rrpv += 1
            incoming_signature = self._shct.get_signature(pc)
            if WB_insertion == 1:
                victim.rrpv = 0
            elif self._shct.get_counter(incoming_signature) == 0:
                victim.rrpv = 3
            elif self._shct.get_counter(incoming_signature) == self._shct.max_counter:
                victim.rrpv = 0
            else:
                victim.rrpv = 2
            set_idx = (address >> self._set_shift) & ((self._size // (self._block_size * self._mapping_pol)) - 1)
            if victim.r == 0 and victim.valid and set_idx in self.sampled_sets:
                self._shct.decrement_counter(victim.signature)
            if set_idx in self.sampled_sets:
                victim.r = 0
                victim.signature = incoming_signature



        elif self._replace_pol == "pseudo_LRU":
            victim = set[0]
            set_mask = (self._size // (self._block_size * self._mapping_pol)) - 1
            set_num = (address >> self._set_shift) & set_mask
            way = self._plru_get_victim(set_num)
            victim = set[way]

        elif self._replace_pol == Cache.RLR:
            victim = set[0]
            for index in range(len(set)):
                if set[index].age_counter > 2 * set[index].preuse_distance:
                    set[index].age_priority = 0
                else:
                    set[index].age_priority = 1
                if (set[index].hit + 8 * set[index].age_priority) <= (victim.hit + 8 * victim.age_priority):
                    victim = set[index]
            victim.hit = 0
            victim.age_priority = 0
            victim.age_counter = 0
            victim.preuse_distance = 0

        elif self._replace_pol == "RL":
            victim = None
            for index in range(len(set)):  # Check if a line in the set is free
                if set[index].valid == 0:
                    victim = set[index]
                    victim.modified = 0
                    victim.valid = 1
                    victim.tag = tag
                    victim.data = data
                    victim.level = level
                    victim.hits = 0
                    victim.lazy_updated = lazy_update
                    victim.use = 0
                    victim.age_counter = 0
                    victim.preuse_distance = 0
                    return None, None
            ways_levels = [0] * self._mapping_pol
            for i in range(len(set)):
                ways_levels[i] = set[i].level
            ways_hits = [0] * self._mapping_pol
            for i in range(len(set)):
                ways_hits[i] = set[i].hits
            ways_preuse = [0] * self._mapping_pol
            for i in range(len(set)):
                ways_preuse[i] = set[i].preuse_distance
            ways_dirty = [0] * self._mapping_pol
            for i in range(len(set)):
                ways_dirty[i] = set[i].modified
            ways_lazy_updated = [0] * self._mapping_pol
            for i in range(len(set)):
                ways_lazy_updated[i] = set[i].lazy_updated

            state = build_state(ways_hits, address, pc, lazy_update, level, ways_levels,
                                ways_preuse, ways_dirty, ways_lazy_updated)

            victim_idx = rl.choose_action(state)
            # Insert incoming
            n = int(log(self._size // (self._mapping_pol * self._block_size), 2))  # number of bits
            mask = (1 << n) - 1
            victim = set[victim_idx]
            evicted_line_addr = victim.tag << (self._tag_shift) | (
                    ((address >> self._set_shift) & mask) << self._set_shift)
            victim_info = None
            l1_victim = None
            if victim.modified and victim.valid:
                victim_info = (evicted_line_addr)
            elif victim.valid:
                l1_victim = (evicted_line_addr)

            victim.modified = 0
            victim.valid = 1
            victim.tag = tag
            victim.data = data
            victim.level = level
            victim.hits = 0
            victim.lazy_updated = lazy_update
            victim.use = 0
            victim.age_counter = 0
            victim.preuse_distance = 0
            ways_levels = [0] * self._mapping_pol
            for i in range(len(set)):
                ways_levels[i] = set[i].level
            ways_hits = [0] * self._mapping_pol
            for i in range(len(set)):
                ways_hits[i] = set[i].hits
            ways_preuse = [0] * self._mapping_pol
            for i in range(len(set)):
                ways_preuse[i] = set[i].preuse_distance
            ways_dirty = [0] * self._mapping_pol
            for i in range(len(set)):
                ways_dirty[i] = set[i].modified
            ways_lazy_updated = [0] * self._mapping_pol
            for i in range(len(set)):
                ways_lazy_updated[i] = set[i].lazy_updated
            next_state = build_state(ways_hits, address, pc, lazy_update, level, ways_levels,
                                     ways_preuse, ways_dirty, ways_lazy_updated)
            way = [0] * (self._mapping_pol - 1)
            x = 0
            set_mask = (self._size // (self._block_size * self._mapping_pol)) - 1
            set_num = (address >> self._set_shift) & set_mask
            for i in range(self._mapping_pol):
                if victim_idx != i:
                    way[x] = (set[i].tag << self._tag_shift) + (set_num << self._set_shift)
                    x += 1
            rl.add_event(evicted_line_addr, address, state, victim_idx, next_state, way[0], way[1], way[2])
            return victim_info, l1_victim

        # Store victim info if modified
        n = int(log(self._size // (self._mapping_pol * self._block_size), 2))  # number of bits
        mask = (1 << n) - 1
        victim_address = victim.tag << (self._tag_shift) | (
                ((address >> self._set_shift) & mask) << self._set_shift)
        l1_victim = None
        if victim.modified and victim.valid:
            victim_info = (victim_address)
        elif victim.valid:
            l1_victim = (victim_address)

        # Replace victim
        victim.modified = 0
        victim.valid = 1
        victim.tag = tag
        victim.data = data
        victim.level = level

        return victim_info, l1_victim

    def write(self, address, byte, pc, level):
        """Write a byte to cache.

        :param int address: memory address for data to write to cache
        :param int byte: byte of data to write to cache
        :return: boolean indicating whether data was written to cache
        """
        tag = self._get_tag(address)  # Tag of cache line
        set = self._get_set(address)  # Set of cache lines
        line = None
        way_index = -1
        # Search for cache line within set
        for candidate in set:
            way_index += 1
            if candidate.tag == tag and candidate.valid:
                line = candidate
                break

        # Update data of cache line
        if line:
            # line.data[self.get_offset(address)] = byte
            line.modified = 1

            if (self._replace_pol == Cache.LRU or
                    self._replace_pol == Cache.LFU or
                    self._replace_pol == Cache.modified_LRU):
                self._update_use(line, set, level)
            elif (self._replace_pol == Cache.RLR):
                self._update_rlr(line, set)
            elif (self._replace_pol == "pseudo_LRU"):
                set_mask = (self._size // (self._block_size * self._mapping_pol)) - 1
                set_num = (address >> self._set_shift) & set_mask
                self._plru_update(set_num, way_index)
            elif self._replace_pol == "RL":
                if line.hits < 127:
                    line.hits += 1
                line.preuse_distance = line.age_counter
                for index in range(len(set)):
                    if set[index].age_counter < 127:
                        set[index].age_counter += 1
                line.age_counter = 0


        return True if line else False

    def print_section(self, start, amount):
        """Print a section of the cache.

        :param int start: start address to print from
        :param int amount: amount of lines to print
        """
        line_len = len(str(self._size // self._block_size - 1))
        use_len = max([len(str(i.use)) for i in self._lines])
        tag_len = int(log(self._mapping_pol * self._mem_size // self._size, 2))
        address_len = int(log(self._mem_size, 2))

        if start < 0 or (start + amount) > (self._size // self._block_size):
            raise IndexError

        print("\n" + " " * line_len + " " * use_len + " U M V T" +
              " " * tag_len + "<DATA @ ADDRESS>")

        for i in range(start, start + amount):
            print(util.dec_str(i, line_len) + ": " +
                  util.dec_str(self._lines[i].use, use_len) + " " +
                  util.bin_str(self._lines[i].modified, 1) + " " +
                  util.bin_str(self._lines[i].valid, 1) + " " +
                  util.bin_str(self._lines[i].tag, tag_len) + " <" +
                  " ".join([util.hex_str(i, 2) for i in self._lines[i].data]) + " @ " +
                  util.bin_str(self.get_physical_address(i), address_len) + ">")
        print()

    def get_physical_address(self, index):
        """Get the physical address of the cache line at index.

        :param int index: index of cache line to get physical address of
        :return: physical address of cache line
        """
        set_num = index // self._mapping_pol

        return ((self._lines[index].tag << self._tag_shift) +
                (set_num << self._set_shift))

    def get_offset(self, address):
        """Get the offset from within a set from a physical address.

        :param int address: memory address to get offset from
        """
        return address & (self._block_size - 1)


    def _get_tag(self, address):
        """Get the cache line tag from a physical address.

        :param int address: memory address to get tag from
        """
        if self._type == "data_cache" or self._type == "level1" or smart_set_indexing == False:
            return address >> self._tag_shift
        else:
            if self._size == 262144:
                # take bits 9 and 13 to 32 as the tag
                # Bits 13-32 are 20 bits. Bit 9 is 1 bit. Total tag is 21 bits.
                tag = ((address >> 13) << 1) | ((address >> 9) & 1)
            elif self._size == 131072:
                # take bits 10, 11, 12 and 14 to 32 as the tag
                # Bits 14-32 are 19 bits. Bits 10, 11, 12 are 3 bits. Total tag is 22 bits.
                tag = ((address >> 14) << 3) | (((address >> 12) & 1) << 2) | (((address >> 11) & 1) << 1) | (
                        (address >> 10) & 1)
            else:
                # take bits 9 and 11 to 32 as the tag
                # Bits 11-32 are 22 bits. Bit 9 is 1 bit. Total tag is 23 bits.
                tag = ((address >> 11) << 1) | ((address >> 9) & 1)
            return tag

    def _get_set(self, address):
        """Get a set of cache lines from a physical address.

        :param int address: memory address to get set from
        """
        set_mask = (self._size // (self._block_size * self._mapping_pol)) - 1
        if self._type == "data_cache" or self._type == "level1" or smart_set_indexing == False:
            set_num = (address >> self._set_shift) & set_mask

        else:
            bit_3 = (address >> 3) & 0b1
            bit_4 = (address >> 4) & 0b1
            bit_5 = (address >> 5) & 0b1
            bit_6 = (address >> 6) & 0b1
            bit_7 = (address >> 7) & 0b1
            bit_8 = (address >> 8) & 0b1
            bit_9 = (address >> 9) & 0b1
            bit_10 = (address >> 10) & 0b1
            bit_11 = (address >> 11) & 0b1
            bit_12 = (address >> 12) & 0b1
            bit_13 = (address >> 13) & 0b1
            bit_14 = (address >> 14) & 0b1
            bit_15 = (address >> 15) & 0b1
            if self._size == 262144:
                set_num = (
                            bit_12 << 8 | bit_11 << 7 | bit_10 << 6 | bit_8 << 5 | bit_7 << 4 | bit_6 << 3 | bit_5 << 2 | bit_4 << 1 | bit_3)
            elif self._size == 131072:
                set_num = (
                            bit_13 << 7 | bit_9 << 6 | bit_8 << 5 | bit_7 << 4 | bit_6 << 3 | bit_5 << 2 | bit_4 << 1 | bit_3)
            else:
                set_num = (address >> self._set_shift) & set_mask
            if set_num > set_mask:
                raise ValueError("Set number = -1")
        index = set_num * self._mapping_pol
        # if self._type == "ctr_cache":
        # print(f"Set Number = {set_num}")
        return self._lines[index:index + self._mapping_pol]

    def _update_use(self, line, set, level):
        """Update the use bits of a cache line.

        :param line line: cache line to update use bits of
        """
        if self._replace_pol == Cache.LRU or self._replace_pol == Cache.modified_LRU:
            # Set the current line as MRU (highest use value)
            line.use = max(line.use for line in set) + 1
            line.level = level
        elif self._replace_pol == Cache.FIFO:
            # No update on hits (FIFO only cares about insertion order)
            pass
        elif self._replace_pol == Cache.LFU:
            line.use += 1

    def _find_victim(self, set):
        victim = None
        for index in range(len(set)):  # Check if a line in the set is free
            if set[index].valid == 0:
                victim = set[index]
                return victim
        if victim is None:
            if self._type == "ctr_cache":
                Parameters.total_evictions += 1
            victim = set[0]
            for index in range(len(set)):
                if set[index].use < victim.use:
                    victim = set[index]
            return victim

    def _plru_get_victim(self, set_index):
        """Choose a victim way from the PLRU tree for a given set."""
        bits = self.plru_bits[set_index]
        way = 0
        idx = 0
        while idx < len(bits):
            direction = bits[idx]
            if direction == 0:  # left subtree is LRU
                idx = 2 * idx + 1
            else:  # right subtree is LRU
                idx = 2 * idx + 2
            way = idx - (len(bits))  # translate tree index → way
        return way

    def _update_rlr(self, line, set):
        line.preuse_distance = line.age_counter
        for index in range(len(set)):
            set[index].age_counter += 1
        line.age_counter = 0
        line.hit = 1

    def _plru_update(self, set_index, way_index):
        """Update PLRU bits after accessing a way."""
        bits = self.plru_bits[set_index]  # length = ways - 1
        node = way_index + len(bits)  # leaf index for this way
        while node > 0:
            parent = (node - 1) // 2
            if node == 2 * parent + 1:  # accessed LEFT child
                bits[parent] = 1  # mark RIGHT subtree as LRU
            else:  # accessed RIGHT child
                bits[parent] = 0  # mark LEFT subtree as LRU
            node = parent

    def get_weights(self):
        weights, biases = self.nn_policy.net.layers[0].get_weights()
        weights1, biases1 = self.nn_policy.net.layers[1].get_weights()
        # print("weights:", weights)  # (state_dim, hidden_dim)
        print("bias:", biases)
        for x in weights:
            print(x)
        print("bias:", biases1)
        print(weights1)

    def save_weights(self):
        self.nn_policy.save()

    def weight_contributions(self):
        x_sample = [0.0, 5e-05, 0.00011, 2e-05, 2e-05, 0.0, 0.0, 0.0, 0.5, 1.0, 0.0004893346922472119, 0, 0, 0, 0, 0, 0,
                    0, 1, 0, 0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0, 0, 0, 1, 0, 0, 0,
                    0, 0, 0, 1, 0, 0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 1, 0, 0.0, 2e-05, 0.0, 2e-05,
                    2e-05, 0.0, 0.0, 0.0, 0, 0, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0.0078125]
        # x_sample: your input as a 1D array
        x_input = tf.convert_to_tensor([x_sample], dtype=tf.float32)  # shape (1, input_dim)

        with tf.GradientTape() as tape:
            tape.watch(x_input)
            y_pred = self.nn_policy.net(x_input)  # forward pass

        # Compute gradients of output w.r.t. input
        grads = tape.gradient(y_pred, x_input)
        print(grads.numpy())

    def invalidate_line(self, address):
        tag = self._get_tag(address)  # Tag of cache line
        set = self._get_set(address)  # Set of cache lines
        line = None
        # Search for cache line within set
        for candidate in set:
            if candidate.tag == tag and candidate.valid:
                candidate.valid = 0
                break
