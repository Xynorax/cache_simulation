from collections import OrderedDict

from Parameters import MEMORY


class PageTableEntry:
    def __init__(self, frame_number, valid=True, dirty=False, accessed=False):
        self.frame_number = frame_number  # Physical frame number
        self.valid = valid  # Valid bit
        self.dirty = dirty  # Dirty bit
        self.accessed = accessed  # Accessed bit


class MemoryManager:
    def __init__(self, virtual_bits=64, physical_bits=(MEMORY - 1), page_size=4096):
        self.virtual_bits = virtual_bits
        self.physical_bits = physical_bits
        self.page_size = page_size

        # Calculate address space parameters
        self.physical_frames = (1 << physical_bits) // page_size
        self.virtual_pages = (1 << virtual_bits) // page_size

        # Page table (simplified as a dictionary)
        self.page_table = {}

        # Track allocated frames
        self.allocated_frames = set()

        # For page replacement (LRU)
        self.access_order = OrderedDict()

    def translate_virtual_to_physical(self, virtual_address):
        """Translate a 64-bit virtual address to a 23-bit physical address"""
        if virtual_address >= (1 << self.virtual_bits):
            raise ValueError("Virtual address exceeds 64-bit space")

        # Extract page number and offset
        page_number = virtual_address // self.page_size
        offset = virtual_address % self.page_size

        # Check page table
        # Check page table
        if page_number not in self.page_table or not self.page_table[page_number].valid:
            # Page fault - handle it
            self.handle_page_fault(page_number)
            # After handling, the page should be valid
            if not self.page_table[page_number].valid:
                raise MemoryError(f"Failed to make page 0x{page_number:X} valid")

        entry = self.page_table[page_number]

        if not entry.valid:
            raise ValueError("Page is not valid")

        # Update access bits for LRU
        self.access_order.pop(page_number, None)
        self.access_order[page_number] = True
        entry.accessed = True

        # Calculate physical address
        physical_address = (entry.frame_number * self.page_size) + offset

        # Ensure physical address is within 23 bits
        if physical_address >= (1 << self.physical_bits):
            raise ValueError("Physical address exceeds 23-bit space")

        return physical_address

    def handle_page_fault(self, page_number):
        """Handle a page fault by allocating a frame"""
        if len(self.allocated_frames) >= self.physical_frames:
            # Need to evict a page (LRU)
            self.evict_page()

        # Allocate a new frame
        frame = self.allocate_frame()
        # Create new page table entry or update existing one
        if page_number in self.page_table:
            self.page_table[page_number].frame_number = frame
            self.page_table[page_number].valid = True
            self.page_table[page_number].dirty = False
        else:
            self.page_table[page_number] = PageTableEntry(frame)
        self.allocated_frames.add(frame)
        self.access_order[page_number] = True

    def allocate_frame(self):
        """Find an available frame"""
        for frame in range(self.physical_frames):
            if frame not in self.allocated_frames:
                return frame
        raise MemoryError("No available frames")

    def evict_page(self):
        """Evict the least recently used page"""
        if not self.access_order:
            raise MemoryError("No pages to evict")

        # Get the least recently used page
        page_to_evict, _ = self.access_order.popitem(last=False)
        entry = self.page_table[page_to_evict]

        # If dirty, would need to write back to disk here
        if entry.dirty:
            pass  # In a real system, would write to disk

        # Free the frame
        self.allocated_frames.remove(entry.frame_number)
        entry.valid = False

    def mark_dirty(self, virtual_address):
        """Mark a page as dirty (modified)"""
        page_number = virtual_address // self.page_size
        if page_number in self.page_table:
            self.page_table[page_number].dirty = True


# Example usage
if __name__ == "__main__":
    mm = MemoryManager()

    # Test some address translations
    test_addresses = [
        0x0000000000000000,  # Start of memory
        0x0000000000001001,  # Next page
        0x0000000000001000,  # Next page
        0x00000000ABCDEF12,  # Random address
        0x7FFFFFFFFFFFFFFF,  # Large virtual address
    ]
    # Calculate how many pages fit in physical memory
    pages_in_phys_mem = (1 << 23) // 4096  # 2048 pages (8MB / 4KB)
    """for vaddr in test_addresses:
        try:
            paddr = mm.translate_virtual_to_physical(vaddr)
            print(f"Virtual: 0x{vaddr:016X} -> Physical: 0x{paddr:06X}")
        except ValueError as e:
            print(f"Error translating 0x{vaddr:016X}: {str(e)}")"""
    print("\nFilling physical memory:")
    for i in range(pages_in_phys_mem):
        vaddr = i * mm.page_size  # Generate sequential virtual addresses
        paddr = mm.translate_virtual_to_physical(vaddr)
        print(f"Map Virtual: 0x{vaddr:016X} → Physical: 0x{paddr:06X}")
        test_addresses.append(vaddr)  # Add to our test addresses
    eviction_test_address = 0x123456789ABCD000  # New address not yet mapped
    print(f"Accessing new address: 0x{eviction_test_address:016X}")
    paddr = mm.translate_virtual_to_physical(eviction_test_address)
    paddr = mm.translate_virtual_to_physical(eviction_test_address + 1)
    paddr = mm.translate_virtual_to_physical(eviction_test_address - 1)
    paddr = mm.translate_virtual_to_physical(eviction_test_address - 4095)
