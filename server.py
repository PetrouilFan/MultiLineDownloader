import socket
import threading
import os
import sys
import subprocess
import hashlib
from time import sleep

PORT = 10000
SEPARATOR = "<SEP>"
DOWNLOAD_LOCATION = ".tmp\\" # EMPTY FOR THE CURRENT DIRECTORY
MAX_SPLITTED_PARTS = 20

try:
    os.chdir(os.path.dirname(sys.argv[0]))
except:
    pass

def part_calculator(filesize,total_threads,current_part,BUFFER_SIZE):
    total_parts = (filesize//total_threads)//(50*BUFFER_SIZE) # HOW MANY PARTS CAN BE CREATED OF AT LEAST 50 CHUNKS
    if total_parts > MAX_SPLITTED_PARTS:
        total_parts = MAX_SPLITTED_PARTS
    elif total_parts == 0:
        total_parts = 1
    starts = get_file_starts(filesize,total_parts)
    ends = get_file_ends(filesize,total_parts)
    return starts[current_part],ends[current_part]

def get_file_starts(filesize,parts):
    sizes = []
    _equal_chunks = filesize//parts
    for x in range(parts):
        sizes.append(_equal_chunks*x)
    return sizes

def get_file_ends(filesize,parts):
    sizes = get_file_starts(filesize,parts)
    sizes.pop(0)
    for x in range(len(sizes)):
        sizes[x] -= 1
    sizes.append(filesize-1)
    return sizes

def get_file_starts(filesize,parts):
    sizes = []
    _equal_chunks = filesize//parts
    for x in range(parts):
        sizes.append(_equal_chunks*x)
    return sizes

def get_file_ends(filesize,parts):
    sizes = get_file_starts(filesize,parts)
    sizes.pop(0)
    for x in range(len(sizes)):
        sizes[x] -= 1
    sizes.append(filesize-1)
    return sizes

def hashfile(filename):
    openedFile = open(filename,'rb')
    readFile = openedFile.read()
    openedFile.close()
    hash = hashlib.sha256(readFile).hexdigest()
    print(f"File {filename} Hash: {hash}")

def download_file(URL,addr):
    filename = f"{addr[0]}.{URL.split('/')[-1]}"
    command = f'curl -o {DOWNLOAD_LOCATION}{filename} {URL}'
    print(f"Downloading: {filename}")
    subprocess.call(command.split(" "), stderr=subprocess.DEVNULL)
    print(f"Finished:    {filename}")
    return filename

def delete_file(filename):
    os.system(f"rm -rf {DOWNLOAD_LOCATION}{filename}")

def request_handler(conn,addr):
    with conn:
        print(f"Connected by {addr}")
        URL = conn.recv(4096).decode()
        filename = download_file(URL,addr)
        _to_send = filename + SEPARATOR
        _to_send += str(os.path.getsize(f"{DOWNLOAD_LOCATION}{filename}"))
        _to_send =_to_send.encode()
        conn.sendall(_to_send)

def send_handler(conn):
    data = conn.recv(4096).decode()
    data = data.split(SEPARATOR)
    BUFFER_SIZE = int(data[0])
    total_ips = int(data[1])
    current_thread = int(data[2])
    filename = data[3]
    filesize = int(data[4])
    current_part = int(data[5])
    start,end = part_calculator(filesize,total_ips,current_part,BUFFER_SIZE)
    cursor = start
    with open(DOWNLOAD_LOCATION+filename, "rb") as f:
        while cursor <= end:
            f.seek(cursor)
            bytes_read = f.read(BUFFER_SIZE)
            if not bytes_read:
                print("Last Bytes Read:",bytes_read)
                conn.close()
                sleep(1)
            conn.sendall(bytes_read)
            cursor += len(bytes_read)
        conn.close()
    hashfile(DOWNLOAD_LOCATION+filename)


def send_listener():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("0.0.0.0", PORT+1))
        s.listen()
        while True:
            conn, addr = s.accept()
            threading.Thread(target=send_handler,args=(conn,)).start()

if __name__ == '__main__':
    send_listener_thread = threading.Thread(target=send_listener)
    send_listener_thread.daemon = True
    send_listener_thread.start()
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("0.0.0.0", PORT))
        s.listen()
        while True:
            conn, addr = s.accept()
            _thread = threading.Thread(target=request_handler,args=(conn,addr))
            _thread.daemon = True
            _thread.start()