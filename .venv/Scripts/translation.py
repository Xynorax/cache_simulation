from collections import OrderedDict

from Parameters import mem_size


class VirtualAddressTranslator:
    def __init__(self, max_mappings=1000):
        # Use OrderedDict for efficient LRU implementation
        self.va_to_pa = OrderedDict()
        self.pa_to_va = {}
        self.max_mappings = max_mappings
        self.page_size = 0x1000  # 4KB pages

    def _translate_va_to_pa(self, va):
        """
        Core translation logic - converts virtual address to physical address
        Uses the original algorithm: extract bits and rearrange
        """
        part1 = va & 0xFFFF  # Lower 16 bits
        part3 = (va >> 24) & 0x1FF  # Upper 9 bits (bits 24-32)
        pa = (part3 << 16) | part1  # Combine: upper 9 bits + lower 16 bits
        return pa & 0x3FFFFF  # Mask to 22 bits

    def _find_free_page(self, preferred_pa):
        """
        Find a free 4KB page starting from preferred_pa
        Returns the physical address of a free page
        """
        pa = preferred_pa
        max_pa = mem_size // 2

        # Align to page boundary
        pa = (pa // self.page_size) * self.page_size

        while pa < max_pa:
            # Check if entire page is free
            page_free = True
            for addr in range(pa, pa + self.page_size):
                if addr in self.pa_to_va:
                    page_free = False
                    break

            if page_free:
                return pa

            pa += self.page_size

        return None

    def _evict_lru(self):
        """
        Evict the least recently used mapping
        Returns the physical address of the evicted page
        """
        if not self.va_to_pa:
            return None

        # Get LRU item (first item in OrderedDict)
        lru_va, lru_pa = next(iter(self.va_to_pa.items()))

        print(f"Evicting LRU mapping: VA {hex(lru_va)} -> PA {hex(lru_pa)}")

        # Remove the mapping
        del self.va_to_pa[lru_va]

        # Clean up the entire page
        page_start = (lru_pa // self.page_size) * self.page_size
        for addr in range(page_start, page_start + self.page_size):
            if addr in self.pa_to_va:
                evicted_va = self.pa_to_va[addr]
                # Remove from va_to_pa if it exists
                if evicted_va in self.va_to_pa:
                    del self.va_to_pa[evicted_va]
                del self.pa_to_va[addr]

        return page_start

    def translate(self, va):
        """
        Main translation function
        """
        # Check if already mapped
        if va in self.va_to_pa:
            # Move to end for LRU (most recently used)
            pa = self.va_to_pa[va]
            self.va_to_pa.move_to_end(va)
            return pa

        # Calculate physical address
        pa = self._translate_va_to_pa(va)

        # Check for collision
        if pa in self.pa_to_va:
            existing_va = self.pa_to_va[pa]
            print(f"Collision detected! VA {hex(va)} and VA {hex(existing_va)} both map to PA {hex(pa)}")

            # Find free page
            free_pa = self._find_free_page(pa)
            if free_pa is None:
                # No free space, evict LRU
                print("No free space available, implementing LRU eviction...")
                free_pa = self._evict_lru()
                if free_pa is None:
                    raise RuntimeError("Unable to find free space for translation")

            pa = free_pa
            print(f"Using PA {hex(pa)} instead")

        # Check bounds
        if pa >= mem_size // 2:
            raise RuntimeError(f"Physical address {hex(pa)} out of bounds for VA {hex(va)}")

        # Enforce maximum mappings
        if len(self.va_to_pa) >= self.max_mappings:
            self._evict_lru()

        # Store mapping
        self.va_to_pa[va] = pa
        self.pa_to_va[pa] = va

        return pa

    def get_stats(self):
        """Return statistics about the current state"""
        return {
            'active_mappings': len(self.va_to_pa),
            'max_mappings': self.max_mappings,
            'memory_utilization': len(self.pa_to_va) / (mem_size // 2) * 100
        }

    def clear(self):
        """Clear all mappings"""
        self.va_to_pa.clear()
        self.pa_to_va.clear()


# Global translator instance
translator = VirtualAddressTranslator()


def va_translation(va):
    """
    Wrapper function to maintain compatibility with existing code
    """
    return translator.translate(va)


def get_translation_stats():
    """Get current translation statistics"""
    return translator.get_stats()


def clear_translations():
    """Clear all translations"""
    translator.clear()


# Test the improved implementation
if __name__ == "__main__":
    print("Testing improved virtual address translation...")

    # Test cases
    test_vas = [54513784, 189190264, 0x1000000, 0x2000000]

    for va in test_vas:
        try:
            pa = va_translation(va)
            print(f"VA {hex(va)} -> PA {hex(pa)}")
        except Exception as e:
            print(f"Error translating VA {hex(va)}: {e}")

    # Print statistics
    stats = get_translation_stats()
    print(f"\nStatistics: {stats}")
