import requests
import socket
import select


PORT = 8001
address = ("0.0.0.0", PORT)
server_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
server_socket.bind(address)
while True:
    data, addr = server_socket.recvfrom(65536)
    print(data.decode())