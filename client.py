import socket
import sys
import threading
from time import sleep
from git import Object
import psutil
import os
import hashlib
from blessings import Terminal

HOST = os.getenv("mld_host")
PORT = 10000
SEPARATOR = "<SEP>"
BUFFER_SIZE = 1024 * 4 #4KB
MAX_SPLITTED_PARTS = 20

class Terminal_Writer(object):
    def __init__(self, location):
        self.location = location

    def write(self, string):
        with term.location(*self.location):
            print(string)

class part_handler:
    def __init__(self,filesize, total_ips) -> None:
        self.filesize = filesize
        self.total_parts = (filesize//total_ips)//(50*BUFFER_SIZE) # HOW MANY PARTS CAN BE CREATED OF AT LEAST 50 CHUNKS
        if self.total_parts > MAX_SPLITTED_PARTS:
            self.total_parts = MAX_SPLITTED_PARTS
        elif self.total_parts == 0:
            self.total_parts = 1
        starts = self.get_file_starts(self.total_parts)
        ends = self.get_file_ends(self.total_parts)
        self.chunks = []
        for x in range(len(starts)):
            self.chunks.append([starts[x],ends[x]])
        self.part_nums = list(range(0,self.total_parts))

    def get_file_starts(self,parts):
        sizes = []
        _equal_chunks = self.filesize//parts
        for x in range(parts):
            sizes.append(_equal_chunks*x)
        return sizes

    def get_file_ends(self,parts):
        sizes = self.get_file_starts(parts)
        sizes.pop(0)
        for x in range(len(sizes)):
            sizes[x] -= 1
        sizes.append(self.filesize-1)
        return sizes

class Bar(Object):
    def __init__(self,text,total,location,bar_size=None):
        self.text = text
        self.total = total
        if not bar_size:
            self.get_bar_size = lambda: term.width-len(f"{self.text}: || 100.0 %")-2
        else:
            self.get_bar_size = lambda: bar_size
        self.writer = Terminal_Writer((location[0],term.height-1+location[1]))

    def update(self,value):
        percentage = round((value/self.total)*(100),1)
        bar_filled = round(round(percentage) / 100 * self.get_bar_size())
        bar = '█'*bar_filled + ' '*(self.get_bar_size() - bar_filled)
        self.writer.write(f"{self.text}: |{bar}| {percentage} %")

class Progress:
    def __init__(self) -> None:
        self.value = 0

    def config(self,total,part_handler):
        self.total = total
        self.part_progress_bars = self.Part_Progress(part_handler)
        self.total_progress_bar = Bar("Progress",total,(0,-1))

    def start(self):
        self.working = True
        self.thread = threading.Thread(target=self.thread_handler)
        self.thread.daemon = True
        self.thread.start()

    def update(self):
        self.part_progress_bars.update()
        self.total_progress_bar.update(self.value)

    def thread_handler(self):
        while self.working:
            self.update()
            sleep(0.2)

    def stop(self):
        self.working = False

    class Part_Progress:
        def __init__(self,part_handler):
            self.part_handler = part_handler
            self.values = [] # bytes done for every part
            self.parts_bytes_total = []
            for x in range(self.part_handler.total_parts):
                self.values.append(0)
                _chunk_size = self.part_handler.chunks[x][1] - self.part_handler.chunks[x][0]
                self.parts_bytes_total.append(_chunk_size)
            
            # Prepare parts writers
            print("\n"*(self.part_handler.total_parts))
            self.part_bars = []
            for part_num in range(self.part_handler.total_parts):
                _y = 0 - 1 - (self.part_handler.total_parts - part_num)
                _text = f"Part{' '*(3-len(str(part_num+1)))}{part_num+1}"
                self.part_bars.append(Bar(_text,self.parts_bytes_total[part_num],(0,_y),bar_size=15))
        def update(self):
            for _bar_num in range(len(self.part_bars)):
                self.part_bars[_bar_num].update(self.values[_bar_num])

class File_Writer:
    def __init__(self,filename,filesize,total_threads,bar) -> None:
        self.bar = bar
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
                    self.bar.value += len(data[1])
                else:
                    sleep(0.0001)
            return
    def close(self):
        self.stop_bool = True
        self.write_thread.join()

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

def connection_downloader(filename, thread_num, filesize, file_writter, nic, total_ips, parts):
    current_part = 0
    while len(parts.part_nums) > 0:
        current_part = parts.part_nums.pop(0)
        start,end = parts.chunks[current_part]
        cursor = start
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.setsockopt(socket.SOL_SOCKET, 25, nic[0].encode()) # Needed to bind interface in Linux ( Not tested in Windows )
            # s.bind((nic[1],PORT+thread_num)) # It may need in order to bind interface in Windows
            s.connect((HOST, PORT+1))
            _to_send = f"{BUFFER_SIZE}{SEPARATOR}"
            _to_send += f"{total_ips}{SEPARATOR}"
            _to_send += f"{thread_num}{SEPARATOR}"
            _to_send += f"{filename}{SEPARATOR}"
            _to_send += f"{filesize}{SEPARATOR}"
            _to_send += f"{current_part}{SEPARATOR}"
            s.sendall(_to_send.encode())
            while cursor < end:
                data = s.recv(BUFFER_SIZE)
                if len(data) == 0:
                    break
                file_writter.write(cursor,data)
                bar.part_progress_bars.values[current_part] += len(data)
                cursor += len(data)
            s.close()
        # if end-cursor != -1:
        #     parts.part_nums.append(current_part) # Redownload chunk if missing data

def multi_connection_handler(filename, filesize, file_writter,parts):
    NICs = get_ip_addresses()
    total_ips = len(NICs)
    threads = []
    for thread_num in range(total_ips):
        _thread = threading.Thread(target=connection_downloader,args=(filename,thread_num,filesize,file_writter, NICs[thread_num],total_ips, parts))
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
    parts = part_handler(filesize,total_ips)
    file_writter = File_Writer(original_filename,filesize,total_ips,bar)
    bar.config(filesize,parts)
    bar.start()
    multi_connection_handler(filename,filesize,file_writter,parts)
    file_writter.close()
    sleep(0.5)
    # hashfile(original_filename)

term = Terminal()
bar = Progress()

if __name__ == '__main__':
    if HOST == None:
        print("Please set your host address as an Environment Variable named 'mld_host' (without the quotes)")
        sys.exit()
    URL = input("URL: ")
    main(URL)