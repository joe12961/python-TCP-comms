# Hewwo mistwa
# Dis is da client
import socket  # <--:0 Dis is the networking library python has built in >w<

sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM) # oooh lets not lose any of those packets guys :33
sock.connect(("127.0.0.1", 55000)) # HARD coded teehee :D  like cock !

while True:
    print(str(out)+"\n" if (out:=sock.sendall(input().encode())) else "",end="")
