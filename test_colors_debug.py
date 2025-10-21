#!/usr/bin/env python3
"""Debug: Check what colors are being loaded"""
import sys, os, logging
os.chdir('/app')
sys.path.insert(0, '.')

# Set up logging to see what's happening
logging.basicConfig(level=logging.DEBUG, format='%(levelname)s: %(message)s')

from src.sequence_generator import SequenceGenerator

print("\n" + "="*70)
print("LOADING FACE ELEMENTS")
print("="*70 + "\n")

gen = SequenceGenerator()

print("\n" + "="*70)
print("LOADED FACE ELEMENTS:")
print("="*70)

for name in sorted(gen.face_elements.keys()):
    data = gen.face_elements[name]
    print(f"{name:20} → Color: RGB{data['color']}, Nodes: {data['nodes'][:30]}...")
