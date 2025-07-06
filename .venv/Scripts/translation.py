from Parameters import mem_size

va_to_pa = {}
pa_to_va = {}


def va_translation(va):
    # Check if there's a nearby VA that's already mapped (offset check)
    base_va = None
    offset = 0

    # Look for a VA that's a bit less than the current one
    # You can adjust the search range as needed
    for check_offset in range(1, 0x1000):  # Check up to 4KB back
        potential_base = va - check_offset
        if potential_base in va_to_pa:
            base_va = potential_base
            offset = check_offset
            break

    if base_va is not None:
        # Found a nearby VA, use it as base with offset
        base_pa = va_to_pa[base_va]
        pa = base_pa + offset
    else:
        # No nearby VA found, use original translation logic
        part1 = va & 0xFFFF
        part3 = (va >> 24) & 0x1FF
        pa = (part3 << 16) | part1
        pa = pa & 0x3FFFFF
    if va in va_to_pa:
        existing_pa = va_to_pa[va]
        return existing_pa  # Return the existing mapping, not the calculated one

    if pa in pa_to_va:
        existing_va = pa_to_va[pa]
        print(f"Collision detected! VA {hex(va)} and VA {hex(existing_va)} both map to PA {hex(pa)}")
        print(f"Finding next available PA with 4KB free space...")

        # Find next available PA with 4KB (0x1000) of free space
        original_pa = pa
        while True:
            pa += 0x1000  # Move to next 4KB boundary

            # Check bounds
            if pa > mem_size // 2:
                assert False, f"Out of bounds while finding free PA for VA {hex(va)}"

            # Check if this 4KB block is free
            block_free = True
            for addr in range(pa, pa + 0x1000):
                if addr in pa_to_va:
                    block_free = False
                    break

            if block_free:
                print(f"Found free PA block at {hex(pa)} (original was {hex(original_pa)})")
                break
    if pa > mem_size / 2:
        assert False, f"Out of bounds {hex(va)} {va}"
    # Store mapping
    va_to_pa[va] = pa
    pa_to_va[pa] = va

    return pa;


va_translation(54513784)  # 33FD078
va_translation(189190264)
