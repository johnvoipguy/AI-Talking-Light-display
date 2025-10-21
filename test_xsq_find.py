#!/usr/bin/env python3
"""Direct test of _find_latest_xsq"""
import os

xsq_dir = "models/active_models"
xsq_files = [f for f in os.listdir(xsq_dir) if f.endswith('.xsq')]

print("XSQ files found:")
for f in xsq_files:
    full_path = os.path.join(xsq_dir, f)
    mtime = os.path.getmtime(full_path)
    print(f"  {f}: {mtime}")

print("\nFinding max:")
latest = max(xsq_files, key=lambda f: os.path.getmtime(os.path.join(xsq_dir, f)))
print(f"Latest: {latest}")
