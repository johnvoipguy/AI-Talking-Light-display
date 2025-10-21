#!/usr/bin/env python3
"""Create a minimal test FSEQ with just the Nose (nodes 43-50) in RED"""
import struct
import os

def create_test_fseq():
    """Create FSEQ with nodes 43-50 (Nose) in RED"""
    
    # FSEQ v2.0 header (32 bytes)
    header = bytearray(32)
    header[0:4] = b'FSEQ'           # Magic
    struct.pack_into('<I', header, 4, 2)    # Version 2.0
    struct.pack_into('<I', header, 8, 0)    # Compression = 0 (uncompressed)
    struct.pack_into('<I', header, 12, 10)  # Frame count = 10 frames
    struct.pack_into('<H', header, 16, 150*3)  # Channel count = 450 (150 nodes * 3 RGB)
    struct.pack_into('<H', header, 18, 25)  # Frame ms = 40ms (25 FPS)
    struct.pack_into('<I', header, 20, 0)   # Step index = 0
    struct.pack_into('<I', header, 24, 0)   # Universe size = 0 (ignored for uncompressed)
    struct.pack_into('<I', header, 28, 0)   # Gamma table = 0 (none)
    
    # Create frame data
    frames = []
    for frame_num in range(10):
        frame = bytearray(150 * 3)  # 450 bytes for 150 nodes * 3 RGB
        
        # Light up nodes 43-50 (Nose) in RED
        for node in range(43, 51):
            r_idx = (node - 1) * 3
            g_idx = r_idx + 1
            b_idx = r_idx + 2
            
            frame[r_idx] = 255  # Full red
            frame[g_idx] = 0    # No green
            frame[b_idx] = 0    # No blue
            
            if frame_num == 0:
                print(f"Node {node:3d} → channels {r_idx:3d}-{b_idx:3d} = RED")
        
        frames.append(bytes(frame))
    
    # Write FSEQ file
    output_file = "output/test_nose_only.fseq"
    os.makedirs("output", exist_ok=True)
    
    with open(output_file, 'wb') as f:
        f.write(header)
        for frame in frames:
            f.write(frame)
    
    file_size = os.path.getsize(output_file)
    print(f"\n✅ Created {output_file}")
    print(f"   File size: {file_size} bytes")
    print(f"   Header: 32 bytes")
    print(f"   Frames: {len(frames)} × 450 bytes = {len(frames) * 450} bytes")
    print(f"   Total: {32 + len(frames) * 450} bytes")
    
    return output_file

if __name__ == "__main__":
    create_test_fseq()
