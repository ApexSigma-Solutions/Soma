import omega_kg.routers.capture as c
import omega_kg.main as m

print("Capture routes:")
for route in c.routes:
    if hasattr(route, "path"):
        print(f"  {route.path}")
    else:
        print("  No path attribute")

print("\nMain routes:")
for route in m.app.routes:
    if hasattr(route, "path"):
        print(f"  {route.path}")
    else:
        print("  No path attribute")
