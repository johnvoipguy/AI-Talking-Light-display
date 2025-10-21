#!/usr/bin/env python3
"""Quick inline test - no imports needed, just raw XML parsing"""
import xml.etree.ElementTree as ET

xmodel_file = "models/active_models/NorRednoseReindeer.xmodel"
tree = ET.parse(xmodel_file)
root = tree.getroot()

print("=" * 60)
print("FACE ELEMENTS FROM XMODEL:")
print("=" * 60)

for face_info in root.findall('.//faceInfo'):
    print(f"\nFound faceInfo element:")
    for attr_name in sorted(face_info.attrib.keys()):
        if attr_name.endswith('-Color') or attr_name.endswith('2-Color') or attr_name.endswith('3-Color'):
            continue
        if attr_name in ['Name', 'CustomColors', 'Type']:
            continue
        
        nodes_str = face_info.get(attr_name, '')
        if nodes_str:
            print(f"  {attr_name}: {nodes_str}")

print("\n" + "=" * 60)
print("CHECKING SPECIFICALLY FOR:")
print("=" * 60)
face_info = root.find('.//faceInfo')
if face_info:
    print(f"Mouth-AI: {face_info.get('Mouth-AI', 'NOT FOUND')}")
    print(f"FaceOutline2: {face_info.get('FaceOutline2', 'NOT FOUND')}")
    print(f"FaceOutline: {face_info.get('FaceOutline', 'NOT FOUND')}")
    print(f"Eyes-Open: {face_info.get('Eyes-Open', 'NOT FOUND')}")
    print(f"\nCorresponding colors:")
    print(f"Mouth-AI-Color: {face_info.get('Mouth-AI-Color', 'NOT FOUND')}")
    print(f"FaceOutline2-Color: {face_info.get('FaceOutline2-Color', 'NOT FOUND')}")
    print(f"FaceOutline-Color: {face_info.get('FaceOutline-Color', 'NOT FOUND')}")
    print(f"Eyes-Open-Color: {face_info.get('Eyes-Open-Color', 'NOT FOUND')}")
