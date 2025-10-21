#!/usr/bin/env python3
"""Extract node->position mappings from xmodel CustomModelCompressed"""

import re

xmodel_data = "116,0,12;119,0,19;122,0,28;102,0,58;99,0,66;96,1,74;113,2,5;117,3,13;120,3,20;123,4,28;100,4,66;93,4,81;114,5,6;103,5,58;97,5,73;110,6,15;118,6,18;115,7,12;109,7,21;98,7,68;94,7,79;111,8,9;121,8,25;101,8,61;89,8,65;90,8,71;95,8,74;112,9,6;108,9,29;88,9,57;91,9,77;92,10,80;106,11,43;124,12,31;107,12,36;105,12,49;104,12,55;129,15,6;128,15,15;84,15,71;83,15,79;125,16,30;87,17,55;130,18,0;127,18,22;85,18,63;82,19,85;131,23,4;126,24,26;59,24,35;68,24,51;86,24,59;81,24,81;58,26,32;60,26,38;67,26,48;69,26,53;132,27,12;133,27,20;79,27,65;80,27,73;57,30,31;61,30,39;66,30,46;70,30,55;134,32,24;78,32,62;56,34,30;55,34,35;62,34,40;65,34,46;72,34,51;71,34,55;54,38,31;63,38,39;64,38,46;76,38,55;135,40,20;77,40,65;53,42,32;51,42,38;73,42,48;75,42,53;52,44,35;74,44,50;136,47,15;150,47,70;49,50,43;50,51,38;48,51,47;137,56,13;43,56,37;47,56,49;149,56,73;44,60,38;46,60,47;45,62,43;138,66,13;148,66,72;1,67,19;13,67,66;26,70,25;42,70,43;14,70,61;27,72,30;33,72,55;2,73,19;40,73,36;41,73,43;34,73,49;12,73,66;25,74,26;15,74,60;139,75,15;28,75,31;32,75,54;147,75,70;29,76,37;31,76,49;24,77,27;30,77,43;16,77,58;11,79,64;3,80,21;39,80,33;35,80,52;23,81,30;17,81,55;140,84,20;22,84,34;18,84,52;146,84,66;4,85,25;10,85,60;21,86,38;19,86,47;38,87,36;20,87,43;36,87,50;5,89,30;9,89,55;37,90,43;141,92,26;6,92,36;8,92,49;145,92,59;7,93,43;142,98,34;144,98,52;143,103,43"

# Parse into list of (node, x, y)
node_coords = {}
for entry in xmodel_data.split(';'):
    parts = entry.split(',')
    if len(parts) == 3:
        node = int(parts[0])
        x = int(parts[1])
        y = int(parts[2])
        node_coords[node] = (x, y)

# Key nodes we care about
key_nodes = {
    'Mouth': list(range(14, 28)) + [33, 34, 40, 41],  # Mouth-AI nodes
    'Nose': list(range(43, 51)),  # FaceOutline2 (Nose)
    'Eyes': list(range(51, 77)),  # Eyes-Open
    'Outline': list(range(77, 88)) + list(range(105, 108)) + list(range(125, 151))  # FaceOutline
}

print("=" * 70)
print("NODE COORDINATES FROM XMODEL:")
print("=" * 70)

for category, nodes in key_nodes.items():
    print(f"\n{category}:")
    coords_in_category = [(n, node_coords.get(n)) for n in nodes if n in node_coords]
    if coords_in_category:
        # Show min/max coords
        xs = [c[1][0] if c[1] else 0 for c in coords_in_category]
        ys = [c[1][1] if c[1] else 0 for c in coords_in_category]
        print(f"  Nodes: {nodes}")
        print(f"  X range: {min(xs)}-{max(xs)}")
        print(f"  Y range: {min(ys)}-{max(ys)}")
        print(f"  First 3: {coords_in_category[:3]}")

print("\n" + "=" * 70)
print("ALL NODE COORDINATES (sorted by node ID):")
print("=" * 70)
for node in sorted(node_coords.keys()):
    x, y = node_coords[node]
    # Calculate potential channel: y * width + x (assuming 16-wide or similar)
    # But we don't know the width yet
    print(f"Node {node:3d} → ({x:2d}, {y:2d})")

# Check the max x and y to understand grid size
max_x = max(x for x, y in node_coords.values())
max_y = max(y for x, y in node_coords.values())
print(f"\nGrid size appears to be approximately {max_x+1} × {max_y+1}")
