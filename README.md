# Overview
not web-based (i.e. non-HTTP) but uses a custom application layer protocol

## Basic Functions
    - [ ] Create new user
    - [ ] Create 
    - [ ] File Upload
    - [ ] File Download
        Once the TCP connection is
        established, the file upload or download should be initiated. The TCP connection should be
        immediately closed after the file transfer is completed. 
    - [ ] 

## Protocol Requirements
Most functions should be
implemented over UDP except for uploading and downloading of files, which should use TCP.

Note that, UDP and TCP port numbers are distinct (e.g., UDP port
53 is distinct from TCP port 53). Thus, your server can concurrently open a UDP and TCP port
with the specified port number (as the command line argument).

## Client
Since, UDP segments can be occasionally lost, you must implement some simple mechanisms
to recover from it. 

## Server 
When the server starts up, the forum is empty – i.e., there
exist no threads, no messages, no uploaded files. 

## Testing
    - A server and a single active client
        - Multiple clients will connect to the server but sequentially – one client connects, interacts, exits, the second client connects, interacts, exits and so on. 
    - A server and multiple concurrent clients