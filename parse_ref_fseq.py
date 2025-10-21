#!/usr/bin/env python3
"""Parse the reference FSEQ file to understand the channel mapping"""
import struct
import os

fseq_file = "/app/models/active_models/norfreindeer_seq_new.fseq"

with open(fseq_file, 'rb') as f:
    # Read header (32 bytes)
    header = f.read(32)
    
    magic = header[0:4]
    version = struct.unpack_from('<I', header, 4)[0]
    compression = struct.unpack_from('<I', header, 8)[0]
    frame_count = struct.unpack_from('<I', header, 12)[0]
    channel_count = struct.unpack_from('<H', header, 16)[0]
    frame_ms = struct.unpack_from('<H', header, 18)[0]
    
    print("FSEQ Header:")
    print(f"  Magic: {magic}")
    print(f"  Version: {version}")
    print(f"  Compression: {compression}")
    print(f"  Frame count: {frame_count}")
    print(f"  Channel count: {channel_count}")
    print(f"  Frame rate: {1000//frame_ms if frame_ms else 0} FPS ({frame_ms} ms)")
    
    # Read frame data
    print(f"\nFrame data ({frame_count} frames × {channel_count} channels):")
    for frame_num in range(frame_count):
        frame_data = f.read(channel_count)
        if len(frame_data) < channel_count:
            print(f"  Frame {frame_num}: Incomplete ({len(frame_data)} bytes)")
            break
        
        # Find non-zero channels
        non_zero = []
        for i in range(0, len(frame_data), 3):
            r = frame_data[i] if i < len(frame_data) else 0
            g = frame_data[i+1] if i+1 < len(frame_data) else 0
            b = frame_data[i+2] if i+2 < len(frame_data) else 0
            
            if r > 0 or g > 0 or b > 0:
                node = i // 3 + 1  # Convert to 1-indexed node
                non_zero.append((node, r, g, b))
        
        if non_zero:
            print(f"\n  Frame {frame_num}:")
            for node, r, g, b in non_zero:
                color_name = ""
                if r == 255 and g == 0 and b == 0:
                    color_name = " (RED)"
                elif r == 128 and g == 64 and b == 0:
                    color_name = " (BROWN)"
                elif r == 128 and g == 0 and b == 255:
                    color_name = " (PURPLE)"
                elif r == 255 and g == 255 and b == 255:
                    color_name = " (WHITE)"
                
                print(f"    Node {node:3d}: RGB({r:3d}, {g:3d}, {b:3d}){color_name}")
