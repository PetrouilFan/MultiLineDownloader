import socket
import sys
import threading
from time import sleep
import psutil
import os
import hashlib

HOST = os.getenv("mld_host")
PORT = 10000
SEPARATOR = "<SEP>"
BUFFER_SIZE = 1024 * 4 #4KB

class Progress_Bar:
    def __init__(self,total,threads) -> None:
        self.threads = threads
        self.total = total
        self.value = 0
        self.total_written = 0
        self.bar_size = 25
        self.working = True
        self.thread = threading.Thread(target=self.handler)
        self.thread.daemon = True
        self.thread.start()

    def update(self):
        percentage = round((self.total_written/(self.total))*(100),1)
        bar_filled = round(percentage / 100 * self.bar_size)
        bar = '#'*bar_filled + ' '*(self.bar_size - bar_filled)
        print(f"|{bar}| {percentage} % Done",end="         \r")

    def handler(self):
        while self.working:
            self.update()
            sleep(0.5)

    def stop(self):
        bar = '#'*self.bar_size
        print(f"|{bar}| {100.00} % Done",end="\r")
        self.working = False

class writter:
    def __init__(self,filename,filesize,total_threads) -> None:
        self.bar = Progress_Bar(filesize,total_threads)
        self.filename = filename
        self.buffer = []
        self.stop_bool = False
        self.write_thread = threading.Thread(target=self._write_handler)
        self.write_thread.daemon = True
        self.write_thread.start()

    def write(self,cursor,data):
        self.buffer.append([cursor,data])
    
    def _write_handler(self):
        with open(self.filename,'wb') as f:
            while (not self.stop_bool) or len(self.buffer) > 0:
                if len(self.buffer) > 0:
                    data = self.buffer.pop(0)
                    f.seek(data[0])
                    f.write(data[1])
                    self.bar.total_written += len(data[1])
                else:
                    sleep(0.0001)
            return
    def close(self):
        self.stop_bool = True
        self.write_thread.join()

def get_file_starts(filesize,threads):
    sizes = []
    _equal_chunks = filesize//threads
    for x in range(threads):
        sizes.append(_equal_chunks*x)
    return sizes

def get_file_ends(filesize,threads):
    sizes = get_file_starts(filesize,threads)
    sizes.pop(0)
    for x in range(len(sizes)):
        sizes[x] -= 1
    sizes.append(filesize-1)
    return sizes

def validIP(address):
    parts = address.split(".")
    if len(parts) != 4:
        return False
    for item in parts:
        if not 0 <= int(item) <= 255:
            return False
    return True

def get_ip_addresses():
    NICs = []
    for interface, snics in psutil.net_if_addrs().items():
        address = snics[0].address
        if address.split('.')[0] != '127':
            if validIP(address):
                NICs.append([interface, address])
    return NICs

def hashfile(filename):
    openedFile = open(filename,'rb')
    readFile = openedFile.read()
    openedFile.close()
    hash = hashlib.sha256(readFile).hexdigest()
    print(f"File {filename} Hash: {hash}")

def connection_downloader(filename, thread_num, filesize, file_writter, nic, total_ips):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.setsockopt(socket.SOL_SOCKET, 25, nic[0].encode()) # Needed to bind interface in Linux ( Not tested in Windows )
        # s.bind((nic[1],PORT+thread_num)) # It may need in order to bind interface in Windows
        s.connect((HOST, PORT+1))
        _to_send = f"{BUFFER_SIZE}{SEPARATOR}"
        _to_send += f"{total_ips}{SEPARATOR}"
        _to_send += f"{thread_num}{SEPARATOR}"
        _to_send += f"{filename}{SEPARATOR}"
        _to_send += f"{filesize}{SEPARATOR}"
        s.sendall(_to_send.encode())
        start = get_file_starts(filesize,total_ips)[thread_num]
        end = get_file_ends(filesize,total_ips)[thread_num]
        cursor = start
        total_recieved = 0
        while cursor < end:
            data = s.recv(BUFFER_SIZE)
            if len(data) == 0:
                break
            file_writter.write(cursor,data)
            total_recieved += len(data)
            cursor += len(data)
        print(f"Thread: {thread_num} Finished         ")
        return

def multi_connection_handler(filename, filesize, file_writter):
    NICs = get_ip_addresses()
    total_ips = len(NICs)
    threads = []
    for thread_num in range(total_ips):
        _thread = threading.Thread(target=connection_downloader,args=(filename,thread_num,filesize,file_writter, NICs[thread_num],total_ips))
        threads.append(_thread)
        _thread.daemon = True
        _thread.start()
    for thread in threads:
        thread.join()

def main(URL):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.connect((HOST, PORT))
        s.sendall(URL.encode())
        data = s.recv(4096).decode()
        data = data.split(SEPARATOR)
        s.close()
    filename = data[0]
    original_filename = ".".join(filename.split('.')[4:])
    filesize = int(data[1])
    NICs = get_ip_addresses()
    total_ips = len(NICs)
    file_writter = writter(original_filename,filesize,total_ips)
    multi_connection_handler(filename,filesize,file_writter)
    file_writter.close()
    hashfile(original_filename)

if __name__ == '__main__':
    if HOST == None:
        print("Please set your host address as an Environment Variable named 'mld_host' (without the quotes)")
        sys.exit()
    URL = input("URL: ")
    main(URL)

