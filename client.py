import socket  # <--:0 Dis is the networking library python has built in >w<
import threading

sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM) # oooh lets not lose any of those packets
sock.connect(("127.0.0.1", 55000)) # HARD coded 

def listen_thread():
    while True:
        data = sock.recv(1024).decode()
        if data.startswith("message:"):
            print(f"<{data[data.find(':')+1:data.find(' ')]}> {data[data.find(' '):]}")

listener = threading.Thread(target=listen_thread, daemon=True)
listener.start()

try: # The TEF block exists only for the connection termination. Would be neater via context managers
    while True:
        print(str(out)+"\n" if (out:=sock.sendall(input().encode())) else "",end="")
except Exception as e:
    raise e
finally:
    sock.sendall(b"terminate connection")
