import socket


def test_bind(ip, port):
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        s.bind((ip, port))
        print(f"Successfully bound to {ip}:{port}")
        s.close()
        return True
    except Exception as e:
        print(f"Failed to bind to {ip}:{port}: {e}")
        return False


print("Testing 127.0.0.1:8766...")
test_bind("127.0.0.1", 8766)

print("\nTesting 0.0.0.0:8766...")
test_bind("0.0.0.0", 8766)
