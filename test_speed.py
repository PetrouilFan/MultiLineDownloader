import subprocess
import time
import client
import os

# URL = 'ipv4.download.thinkbroadband.com/200MB.zip'
URL = input('URL: ')
def download_file(URL):
    filename = f"{URL.split('/')[-1]}"
    command = f'curl -o {filename} {URL}'
    print(f"Downloading: {filename}")
    subprocess.call(command.split(" "), stderr=subprocess.DEVNULL)
    print(f"Finished:    {filename}")

filename = f"{URL.split('/')[-1]}"

try:
    os.remove(filename)
except:
    pass

print("Starting Downloading")
download_start = time.time()
download_file(URL)
download_stop = time.time()
download = round(download_stop-download_start)
size = os.path.getsize(filename)
Mb = size//1024//1024*8
print(f"\nTime {download}s . Speed {Mb//download} Mb/s")


print("\n\nStarting Multi-Downloading")
multidownload_start = time.time()
client.main(URL)
multidownload_stop = time.time()
multidownload = round(multidownload_stop-multidownload_start)
print(f"\nTime {multidownload}s . Speed {Mb//multidownload} Mb/s")

if multidownload < download:
    print(f"\n{round(download/multidownload,2)} times faster")