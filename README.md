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


    - A server and a single active client
        - Multiple clients will connect to the server but sequentially – one client connects, interacts, exits, the second client connects, interacts, exits and so on. 
    - A server and multiple concurrent clients


    Description:
    This is the server side for the discussion forum, the client and server must communicate using both TCP and UDP.
    The server should concurrently open a UDP and TCP port.
    User multi-threading to handle the data from clients concurrently.
    Since we are using UDP, we need to deal with the packet loss of UDP by using the timeout for retransmission.

Features:
    - CRT: Create Thread
    - LST: List Threads
    - MSG: Post Message
    - DLT: Delete Message
    - RDT: Read Thread
    - EDT: Edit Message
    - UPD: Upload File
    - DWN: Download File
    - RMV: Remove Thread
    - XIT: Exit

Design:
    When the server starts up, the forum is empty. - no threads, no messages, no uploaded files.
    The server should open a UDP socket and wait for an authentication data from the client.
    Once authenticated, the server should should service CREATE_THREAD, LIST_THREADS, POST_MESSAGE, DELETE_MESSAGE, READ_THREAD, EDIT_MESSAGE, REMOVE_THREAD, XIT requests from the client.
    This will require the client and server to exchange messages using UDP.
    The server should concurrently open a TCP socket and wait for a connection from the client.
    Once connected, the server should service DOWNLOAD_FILE and UPLOAD_FILE requests from the client.
    The TCP connection should be closed after the file transfer is complete.
    The user can only initiate the next command after the previous command is complete.

    We need to define data structures to store the information of the forum, such as:
        - threads: a list of threads containing thread_title
        - users: a dictionary of users containing username and password
        - online_users: a list of online users
        - messages: a dictionary of messages containing thread_title, message_id, message_content, message_author
        - files: a dictionary of files

    Since the server must interact with multiple clients, we need to implement multi-threading.
    Since it is feasible for multiple clients to send and receive data from the same udp socket,
    we do not need to create multiple udp sockets.

    When interacting with the client, the server should receive the data for a command.

    Description:
    This is the client side for the discussion forum, the client and server must communicate using both TCP and UDP.
    The server should concurrently open a UDP and TCP port.
    Since we are using UDP, we need to deal with the packet loss of UDP by using the timeout for retransmission.
Features:
    - CRT: Create Thread
    - LST: List Threads
    - MSG: Post Message
    - DLT: Delete Message
    - RDT: Read Thread
    - EDT: Edit Message
    - UPD: Upload File
    - DWN: Download File
    - RMV: Remove Thread
    - XIT: Exit

Design:
    Upon initiation, the client should first execute the user authentication process,
    following authentication, the user should be prompted to enter the commands.
    almost all commands require request/response, so the client should send the request to the server
    the client should not maintain any state about the discussion forum
