#!/usr/bin/env python3
import sys

sys.path.insert(0, "D:/projects/Soma/OmegaKG")
from omega_kg.routers.capture import router as capture_router

print("Available routes:")
for route in capture_router.routes:
    if hasattr(route, "path"):
        print(f"  {route.path}")
    else:
        print(f"  No path attribute for {route}")

print("Done")
