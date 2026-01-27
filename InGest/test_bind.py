import socket


def test_bind(port):
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        s.bind(("0.0.0.0", port))
        print(f"Successfully bound to port {port}")
        s.close()
        return True
    except Exception as e:
        print(f"Failed to bind to port {port}: {e}")
        return False


print("Testing port 8766...")
success_8766 = test_bind(8766)

print("\nTesting port 8771 (alternative)...")
success_8771 = test_bind(8771)

if not success_8766 and success_8771:
    print("\nConclusion: Port 8766 is specifically blocked/taken.")
elif not success_8766 and not success_8771:
    print("\nConclusion: System-wide binding issue or firewall.")
else:
    print("\nConclusion: Port 8766 IS bindable. The app should work.")
