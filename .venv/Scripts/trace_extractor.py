import lzma
import os
import struct

# --- Configuration for 64-byte CRC Trace Format ---
CHAMPSIM_INSTR_SIZE = 64
# Format: <Q (IP) B (type) B (branch_taken) B (cache_level) B (padding) I (addr_count) 6Q (addresses)
CHAMPSIM_INSTR_FORMAT = '<QBBBBBBBBQQQQQQ'  # Little-endian, 64 bytes total

# Verify the struct size
if struct.calcsize(CHAMPSIM_INSTR_FORMAT) != CHAMPSIM_INSTR_SIZE:
    raise ValueError(f"Struct format size mismatch! Expected {CHAMPSIM_INSTR_SIZE} bytes, "
                     f"but calculated {struct.calcsize(CHAMPSIM_INSTR_FORMAT)} bytes.")


def parse_champsim_trace(trace_filepath, max_instructions=None):
    """
    Parses a 64-byte CRC format binary trace file.
    """
    parsed_instructions = []

    if not os.path.exists(trace_filepath):
        print(f"Error: Trace file not found at '{trace_filepath}'")
        return []

    open_func = lzma.open if trace_filepath.lower().endswith('.xz') else open

    try:
        with open_func(trace_filepath, 'rb') as f:
            print(f"Parsing CRC trace from '{trace_filepath}'...")
            instruction_count = 0

            while True:
                chunk = f.read(CHAMPSIM_INSTR_SIZE)
                if not chunk:
                    break

                if len(chunk) != CHAMPSIM_INSTR_SIZE:
                    print(f"Warning: Incomplete instruction at offset {f.tell() - len(chunk)}")
                    break

                # Unpack all fields at once
                (ip, is_branch, branch_taken,
                 destination_registers1, destination_registers2,
                 source_registers1, source_registers2, source_registers3, source_registers4
                 , destination_memory1, destination_memory2, source_memory1,
                 source_memory2, source_memory3, source_memory4) = struct.unpack(CHAMPSIM_INSTR_FORMAT, chunk)

                parsed_instructions.append({
                    'instruction_number': instruction_count,
                    'ip': f"0x{ip:016X}",
                    'is_branch': is_branch,
                    'branch_taken': branch_taken,
                    'destination_registers': [destination_registers1, destination_registers2],
                    'source_registers': [source_registers1, source_registers2, source_registers3, source_registers4],
                    'destination_memory': [hex(destination_memory1), hex(destination_memory2)],
                    'source_memory': [hex(source_memory1), hex(source_memory2), hex(source_memory3),
                                      hex(source_memory4)]
                })

                instruction_count += 1
                if max_instructions and instruction_count >= max_instructions:
                    break

            print(f"Finished parsing. Total instructions: {instruction_count}")

    except Exception as e:
        print(f"Error processing '{trace_filepath}': {str(e)}")
        return []

    return parsed_instructions


if __name__ == "__main__":
    TRACE_FILE_PATH = "D:\\Youssef\\TUM\\Master thesis\\400.perlbench-41B.champsimtrace"

    # Parse first 10 instructions
    instructions = parse_champsim_trace(TRACE_FILE_PATH, max_instructions=1000000)

    # Print results
    print("\nParsed Instructions:")
    print("-" * 120)
    print(
        f"{'#':<5} | {'IP':<18} | {'is branch':<9} | {'branch taken':<12} | {'destination registers':<15} | {'source registers':<25} | {'Destination memory':<31}| {'Source memory':<25}")
    print("-" * 120)

    for instr in instructions:
        dest_regs_str = ','.join(str(r) for r in instr['destination_registers'])
        src_regs_str = ','.join(str(r) for r in instr['source_registers'])
        dest_mem_str = ','.join(instr['destination_memory'])
        src_mem_str = ','.join(instr['source_memory'])

        print(f"{instr['instruction_number']:<5} | {instr['ip']:<18} | "
              f"{instr['is_branch']:<9} | {str(instr['branch_taken']):<12} | "
              f"{dest_regs_str:<21} | {src_regs_str:<25} | "
              f"{dest_mem_str:<30} | {src_mem_str}")

    if not instructions:
        print("No instructions parsed - check for errors")
