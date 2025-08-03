import random
from math import log

import util
from Parameters import smart_set_indexing
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
    # Mapping policies
    WRITE_BACK = "WB"
    WRITE_THROUGH = "WT"

    def __init__(self, size, mem_size, block_size, mapping_pol, replace_pol,
                 write_pol, type="data_cache"):
        self._lines = [Line(block_size) for i in range(size // block_size)]

        self._mapping_pol = mapping_pol  # Mapping policy
        self._replace_pol = replace_pol  # Replacement policy
        self._write_pol = write_pol  # Write policy

        self._size = size  # Cache size
        self._mem_size = mem_size  # Memory size
        self._block_size = block_size  # Block size
        self._type = type
        # Bit offset of cache line tag
        self._tag_shift = int(log(self._size // self._mapping_pol, 2))
        # Bit offset of cache line set
        self._set_shift = int(log(self._block_size, 2))
        if self._replace_pol == Cache.ship_plus:
            self._shct = self.SHCT()
            # Track ~64 sampled sets (1-2% of total sets)
            total_sets = size // (block_size * mapping_pol)
            self.sampled_sets = set(random.sample(range(total_sets), 16))

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

    def read(self, address, pc):
        """Read a block of memory from the cache.

        :param int address: memory address for data to read from cache
        :return: block of memory read from the cache (None if cache miss)
        """
        tag = self._get_tag(address)  # Tag of cache line
        set = self._get_set(address)  # Set of cache lines
        line = None

        # Search for cache line within set
        for candidate in set:
            if candidate.tag == tag and candidate.valid:
                line = candidate
                break

        # Update use bits of cache line
        if line:
            if (self._replace_pol == Cache.LRU or
                    self._replace_pol == Cache.LFU):
                self._update_use(line, set)
            if (self._replace_pol == Cache.RLR):
                self._update_rlr(line, set)

            if (self._replace_pol == Cache.ship_plus):
                set_idx = (address >> self._set_shift) & ((self._size // (self._block_size * self._mapping_pol)) - 1)
                if set_idx in self.sampled_sets:
                    if line.r == 0:
                        self._shct.increment_counter(line.signature)
                        line.r = 1
                line.rrpv = 0

        return line.data if line else line

    def load(self, address, data, pc, WB_insertion=0):
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

            for index in range(len(set)):  # Check if a line in the set is free
                if set[index].valid == 0:
                    victim = set[index]
                    break
            if victim is None:
                for index in range(len(set)):
                    if set[index].use < victim.use:
                        victim = set[index]

            victim.use = 0

            if self._replace_pol == Cache.FIFO:
                self._update_use(victim, set)
        elif self._replace_pol == Cache.RAND:
            index = random.randint(0, self._mapping_pol - 1)
            victim = set[index]

        elif self._replace_pol == Cache.ship_plus:
            victim = None
            for index in range(len(set)):  # Check if a line in the set is free
                if set[index].valid == 0:
                    victim = set[index]
                    break
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
                victim.rrpv = 3
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

        # Store victim info if modified
        if victim.modified:
            victim_info = (index, victim.data)

        # Replace victim
        victim.modified = 0
        victim.valid = 1
        victim.tag = tag
        victim.data = data

        return victim_info

    def write(self, address, byte, pc):
        """Write a byte to cache.

        :param int address: memory address for data to write to cache
        :param int byte: byte of data to write to cache
        :return: boolean indicating whether data was written to cache
        """
        tag = self._get_tag(address)  # Tag of cache line
        set = self._get_set(address)  # Set of cache lines
        line = None

        # Search for cache line within set
        for candidate in set:
            if candidate.tag == tag and candidate.valid:
                line = candidate
                break

        # Update data of cache line
        if line:
            # line.data[self.get_offset(address)] = byte
            line.modified = 1

            if (self._replace_pol == Cache.LRU or
                    self._replace_pol == Cache.LFU):
                self._update_use(line, set)
            if (self._replace_pol == Cache.RLR):
                self._update_rlr(line, set)
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
        if self._type == "data_cache" or self._type == "level1" or self._type == "ctr_cache" or smart_set_indexing == False:
            return address >> self._tag_shift
        else:
            # group1 = (address >> 29) & 0b1111
            # group2 = (address >> 24) & 0b1111
            # group3 = (address >> 19) & 0b1111
            # group4 = (address >> 14) & 0b1111
            # group5 = (address >> 9) & 0b1111
            group1 = (address >> 16) & 0b111111111111111111
            group2 = (address >> 12) & 0b111
            tag = (address >> 13) << 2 | ((address >> 9) & 0b1) << 1 | ((address >> 8) & 0b1)
            return tag

    def _get_set(self, address):
        """Get a set of cache lines from a physical address.

        :param int address: memory address to get set from
        """
        set_mask = (self._size // (self._block_size * self._mapping_pol)) - 1
        if self._type == "data_cache" or self._type == "level1" or self._type == "ctr_cache" or smart_set_indexing == False:

            set_num = (address >> self._set_shift) & set_mask

        elif self._type == "level1_cc":
            bit_3 = (address >> 3) & 0b1
            bit_4 = (address >> 4) & 0b1
            bit_5 = (address >> 5) & 0b1
            bit_6 = (address >> 6) & 0b1
            bit_7 = (address >> 7) & 0b1
            bit_10 = (address >> 10) & 0b1
            bit_11 = (address >> 11) & 0b1
            bit_12 = (address >> 12) & 0b1
            bit_15 = (address >> 15) & 0b1
            set_num = (bit_12 << 5 | bit_11 << 4 | bit_10 << 3 | bit_7 << 2 | bit_6 << 1 | bit_5)
            if set_num > set_mask:
                raise ValueError("Set number = -1")
        index = set_num * self._mapping_pol
        return self._lines[index:index + self._mapping_pol]

    def _update_use(self, line, set):
        """Update the use bits of a cache line.

        :param line line: cache line to update use bits of
        """
        if self._replace_pol == Cache.LRU:
            # Set the current line as MRU (highest use value)
            line.use = max(line.use for line in set) + 1
        elif self._replace_pol == Cache.FIFO:
            # No update on hits (FIFO only cares about insertion order)
            pass
        elif self._replace_pol == Cache.LFU:
            line.use += 1

    def _update_rlr(self, line, set):
        line.preuse_distance = line.age_counter
        for index in range(len(set)):
            set[index].age_counter += 1
        line.age_counter = 0
        line.hit = 1
