#!/usr/bin/env python3
"""Test to see what face elements are loaded from xmodel"""
import sys
import os
os.chdir('/app')
sys.path.insert(0, '.')

# Suppress logging noise
import logging
logging.basicConfig(level=logging.WARNING)

from src.sequence_generator import SequenceGenerator

gen = SequenceGenerator()

print("\n" + "="*70)
print("FACE ELEMENTS LOADED FROM XMODEL:")
print("="*70)

if gen.face_elements:
    for name in sorted(gen.face_elements.keys()):
        data = gen.face_elements[name]
        nodes_list = gen._parse_node_ranges(data['nodes'])
        print(f"\n{name}")
        print(f"  Nodes: {data['nodes']}")
        print(f"  Count: {len(nodes_list)}")
        print(f"  Color: RGB{data['color']}")
else:
    print("ERROR: No face elements loaded!")

print("\n" + "="*70)
print("KEY ELEMENTS:")
print("="*70)

for key in ['FaceOutline2', 'Nose', 'Eyes-Open', 'FaceOutline', 'Mouth-AI']:
    if key in gen.face_elements:
        data = gen.face_elements[key]
        nodes = gen._parse_node_ranges(data['nodes'])
        print(f"✅ {key:20} → {len(nodes):3} nodes, color: {data['color']}")
    else:
        print(f"❌ {key:20} NOT FOUND")
