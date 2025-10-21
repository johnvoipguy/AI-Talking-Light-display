#!/usr/bin/env python3
"""Quick debug test to see what nodes are being written"""
import logging
import sys
import os

# Setup detailed logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(levelname)s - %(message)s'
)

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from sequence_generator import SequenceGenerator

# Create generator which will load and log all face elements
gen = SequenceGenerator()

print("\n" + "="*60)
print("FACE ELEMENTS LOADED:")
print("="*60)
for name, data in sorted(gen.face_elements.items()):
    if 'Mouth' not in name:
        nodes = gen._parse_node_ranges(data['nodes'])
        print(f"{name}: {data['nodes']}")
        print(f"  → Parsed nodes: {nodes}")
        print(f"  → Color: {data['color']}")
        print()

# Create a test frame and apply elements
frame = bytearray(450 * 3)  # 150 nodes * 3 RGB
gen._apply_all_static_face_elements(frame)

print("\n" + "="*60)
print("FRAME DATA WRITTEN:")
print("="*60)

# Check which channels have non-zero data
non_zero = []
for i in range(0, len(frame), 3):
    node_num = i // 3 + 1  # Convert channel index to node number
    r, g, b = frame[i], frame[i+1], frame[i+2]
    if r > 0 or g > 0 or b > 0:
        non_zero.append((node_num, r, g, b))

print(f"Nodes with light data: {len(non_zero)}")
for node_num, r, g, b in non_zero[:20]:
    print(f"  Node {node_num:3d} → RGB({r:3d}, {g:3d}, {b:3d})")
if len(non_zero) > 20:
    print(f"  ... and {len(non_zero) - 20} more")
