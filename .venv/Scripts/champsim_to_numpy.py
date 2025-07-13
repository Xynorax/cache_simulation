import struct

import numpy as np

CHAMPSIM_INSTR_SIZE = 64
CHAMPSIM_INSTR_FORMAT = '<QBBBBBBBBQQQQQQ'  # Little-endian, 64 bytes total


def convert_champsim_to_numpy(trace_filepath: str, output_path: str):
    """Convert ChampSim trace to NumPy array format"""

    # Define your dtype
    champsim_dtype = np.dtype([
        ('field0', '<u8'),  # Q - uint64
        ('field1', '<u1'),  # B - uint8
        ('field2', '<u1'),  # B - uint8
        ('field3', '<u1'),  # B - uint8
        ('field4', '<u1'),  # B - uint8
        ('field5', '<u1'),  # B - uint8
        ('field6', '<u1'),  # B - uint8
        ('field7', '<u1'),  # B - uint8
        ('field8', '<u1'),  # B - uint8
        ('field9', '<u8'),  # Q - uint64
        ('field10', '<u8'),  # Q - uint64
        ('field11', '<u8'),  # Q - uint64
        ('field12', '<u8'),  # Q - uint64
        ('field13', '<u8'),  # Q - uint64
        ('field14', '<u8'),  # Q - uint64
    ])

    with open(trace_filepath, 'rb') as f:
        file_size = f.seek(0, 2)  # Get file size
        f.seek(0)  # Reset to beginning

        total_instructions = 50000000  # file_size // CHAMPSIM_INSTR_SIZE

        # Read in chunks to avoid memory issues
        chunk_size = 1000000  # 1M instructions at a time
        all_data = []

        for i in range(0, total_instructions, chunk_size):
            remaining = min(chunk_size, total_instructions - i)
            chunk_bytes = f.read(remaining * CHAMPSIM_INSTR_SIZE)

            if not chunk_bytes:
                break

            # Unpack this chunk
            chunk_data = list(struct.iter_unpack(CHAMPSIM_INSTR_FORMAT, chunk_bytes))
            all_data.extend(chunk_data)

    # Now convert to numpy (outside the file context)
    np_array = np.array(all_data, dtype=champsim_dtype)
    np.save(output_path, np_array)

    return np_array


# Convert once
NUMPY_TRACE_PATH = "D:\\Youssef\\TUM\\ChampSim\\400.perlbench-41B.npy"
NUMPY_TRACE_PATH = "D:\\Youssef\\TUM\\ChampSim\\429.mcf-51B.npy"
# convert_champsim_to_numpy("D:\\Youssef\\TUM\\ChampSim\\400.perlbench-41B.champsimtrace", NUMPY_TRACE_PATH)
convert_champsim_to_numpy("D:\\Youssef\\TUM\\ChampSim\\429.mcf-51B.champsimtrace", NUMPY_TRACE_PATH)
# Memory-mapped - loads data on-demand (best for large traces)
trace_data = np.load(NUMPY_TRACE_PATH, mmap_mode='r')

# Access specific instructions
instruction_1000 = trace_data[7648960:7648969]
instructions_1000_to_2000 = trace_data[1000:2000]
print(instruction_1000)
