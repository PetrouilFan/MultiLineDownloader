# MultiLineDownloader
A tool to download files faster using multiple network lines and a fast server.
It buffers the file on the server and sends parts of the file on the client through multiple network lines and the client reconstructs the file 
with a result of a bigger download speed.

## To Do
1. *Make the server able to reject clients depending on their URL (invalid URLs, or non URL formats)*
2. *Remove junk code and unused variables*
3. *Make the client able to select how many parts*
4. *Add yaml config file for the server buffer server connections*
5. *Add Upload function*
6. *Add compression
