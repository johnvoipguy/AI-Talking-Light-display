#!/usr/bin/env python3
"""Parse FSEQ v2.2 file to understand the channel mapping"""
import struct
import json

fseq_file = '/app/models/active_models/norfreindeer_seq_new (1).fseq'

try:
    import zstandard as zstd
    has_zstd = True
except ImportError:
    has_zstd = False
    print("⚠️  zstandard not installed - cannot decompress")

# Read the file
with open(fseq_file, 'rb') as f:
    data = f.read()

print(f"File size: {len(data)} bytes")
print(f"\nFirst 32 bytes (header):")
header = data[:32]
print(' '.join(f'{b:02x}' for b in header))

# Check magic
magic = header[0:4]
print(f"\nMagic: {magic} ({'FSEQ' if magic == b'FSEQ' else 'NOT FSEQ'})")

# Parse v2 header
if magic == b'FSEQ':
    version = struct.unpack_from('<I', header, 4)[0]
    compression = struct.unpack_from('<I', header, 8)[0]
    frame_count = struct.unpack_from('<I', header, 12)[0]
    channel_count = struct.unpack_from('<H', header, 16)[0]
    frame_ms = struct.unpack_from('<H', header, 18)[0]
    
    print(f"Version: {version}")
    print(f"Compression: {compression}")
    print(f"Frame count: {frame_count}")
    print(f"Channel count: {channel_count}")
    print(f"Frame time: {frame_ms}ms")
    
    if has_zstd and compression == 1:
        print("\n✅ File uses zstd compression")
        print("To decompress, would need: zstandard library")
        print("\nKey insight: ChannelCount=452, which means 150 nodes * 3 RGB + 2 extra")
