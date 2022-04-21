import socket
import threading
import os
import sys
import hashlib
from time import sleep
import requests
import urllib

PORT = 10000
SEPARATOR = "<SEP>"
DOWNLOAD_LOCATION = ".tmp/" # EMPTY FOR THE CURRENT DIRECTORY
MAX_SPLITTED_PARTS = 20

download_items = {}

try:
    os.chdir(os.path.dirname(sys.argv[0])) # Change to Script Directory
except:
    pass # Already on the script Directory

class download_item(object):
    def __init__(self,filename):
        self.filename = filename
        self.filesize = 0
        self.finished_downloading = False
        self.last_byte_downloaded = 0

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

# Used to check the integrity of the file (Not implemented yet on the code)
def hashfile(filename):
    openedFile = open(filename,'rb')
    readFile = openedFile.read()
    openedFile.close()
    hash = hashlib.sha256(readFile).hexdigest()
    print(f"File {filename} Hash: {hash}")

def get_filesize(URL):
    user_agent = 'Mozilla/5.0 (Windows; U; Windows NT 5.1; en-US; rv:1.9.0.7) Gecko/2009021910 Firefox/3.0.7'
    headers={'User-Agent':user_agent,} 
    request=urllib.request.Request(URL,None,headers) #The assembled request
    response = urllib.request.urlopen(request)
    return response.length

def stream_file(URL,filename):
    item = download_item(filename)
    item.filesize = int(get_filesize(URL))
    streamer = threading.Thread(target=stream_handler,args=(URL,filename,item))
    streamer.daemon = True
    streamer.start() 
    return item

def stream_handler(URL,filename,item):
    item.filename = filename
    with requests.get(URL, stream=True) as r:
        r.raise_for_status()
        with open(f"{DOWNLOAD_LOCATION}{filename}", 'wb') as f:
            for chunk in r.iter_content(chunk_size=4096): 
                f.write(chunk)
                item.last_byte_downloaded += len(chunk)
    item.finished_downloading = True

def delete_file(filename):
    os.system(f"rm -rf {DOWNLOAD_LOCATION}{filename}")

def request_handler(conn,addr):
    with conn:
        print(f"Connected by {addr}")
        URL = conn.recv(4096).decode()
        filename = f"{addr[0]}.{URL.split('/')[-1]}"
        item = stream_file(URL,filename)
        download_items[filename] = item
        _to_send = filename + SEPARATOR
        _to_send += str(item.filesize)
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
    item = download_items[filename]
    while not os.path.isfile(DOWNLOAD_LOCATION+filename):
        sleep(0.0001)
    with open(DOWNLOAD_LOCATION+filename, "rb") as f:
        while cursor <= end:
            if cursor+BUFFER_SIZE < item.last_byte_downloaded or item.finished_downloading:
                f.seek(cursor)
                bytes_read = f.read(BUFFER_SIZE)    
                if not bytes_read:
                    conn.close()
                conn.sendall(bytes_read)
                cursor += len(bytes_read)
            else:
                sleep(0.0001)
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