#!/usr/bin/env python3
"""Test to see what face elements are loaded"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from sequence_generator import SequenceGenerator

gen = SequenceGenerator()

print("\n" + "=" * 70)
print("FACE ELEMENTS LOADED:")
print("=" * 70)

for name, data in sorted(gen.face_elements.items()):
    nodes = gen._parse_node_ranges(data['nodes'])
    print(f"{name:25} | Nodes: {data['nodes']:20} → Count: {len(nodes):3} | Color: {data['color']}")

print("\n" + "=" * 70)
print("SPECIFICALLY - NOSE (FaceOutline2):")
print("=" * 70)

if 'FaceOutline2' in gen.face_elements:
    nose_data = gen.face_elements['FaceOutline2']
    nose_nodes = gen._parse_node_ranges(nose_data['nodes'])
    print(f"Nose nodes: {nose_data['nodes']}")
    print(f"Parsed: {nose_nodes}")
    print(f"Color: {nose_data['color']}")
else:
    print("ERROR: FaceOutline2 NOT FOUND!")
    print(f"Available elements: {list(gen.face_elements.keys())}")
