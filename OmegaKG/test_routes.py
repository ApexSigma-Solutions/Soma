import sys

sys.path.insert(0, ".")

from omega_kg.routers.capture import router as capture_router

print("Capture routes:")
for route in capture_router.routes:
    if hasattr(route, "path"):
        print(f"  {route.path}