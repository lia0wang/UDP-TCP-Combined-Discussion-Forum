# ASSIGNMENT REPORT

Created Mar 15, 2022
@author: Wang Liao, z5306312
Python 3.9.7

## Features Design

Features except UPD/DWN are entirely implemented using UDP.

UPD and DWN are implemented using both UDP and TCP

- UDP for communication between client and server

- TCP for file transfer: the tcp socket created only when the file needs to be downloaded or uploaded, and closed immediately after the file transfer is complete.

- For example, in **client.py**
  
  ```python
        file_s = socket(AF_INET, SOCK_STREAM)
        file_s.connect(('', PORT))
        with open(file_name, 'wb') as f:
            while True:
                data = file_s.recv(1024)
                if not data:
                    break
                f.write(data)
        file_s.close()
  ```

## Server Design

#### Overview

**Data structure**

- **clients**: a set of client sockets to remove the duplicate client sockets
- **threads**: a list of thread_title to store the threads
- **users**: a dictionary to store the user information
- **online_users**: a list to store the online usernames
- **files**: a list to store the files

When the server starts up, the forum is empty. no threads, no messages, no uploaded files.

The server should open a UDP socket and wait for an authentication data from the clients.

Once authentication is complete, the server should service each command issued by the clients.

The user can only initiate the next command after the previous command is complete.

The server transfers file using TCP.

The server communicates with the client using UDP.

The server should be able to handle multiple clients.

#### Implementation and Purpose

To implement the concurrent interaction with multiple clients, I use multi-threading to handle the requests from clients.

```python
    thread = threading.Thread(target=client_handler, args=(udp_socket, data, add)) # create a new thread for each client
    thread.daemon = True # the main thread can exit when the server is stopped
    thread.start()
```

To deal with the packet loss of UDP, I use retransmission mechanism with setting the timeout.

```python
def udp_receive_data(udp_soc):
    while True:
        try:
            data, add = udp_soc.recvfrom(1024)
            data = json.loads(data.decode('utf-8'))
            return data, add
        except timeout:
            continue
```

## Client Design

#### Overview

**Data structure**
    - **commands**: a list to store the commands
    - **user_info**: a dictionary to store the user information

The client executes the user authentication process at the beginning.
The client should be prompted to enter one of the commands.
The clients communicate with the server using UDP.
The client does not maintain any state about the forum.

#### Implementation and Purpose

To deal with the packet loss of UDP, I use retransmission mechanism with setting the timeout.

```python
def udp_send_request(client_udp_socket, request):
    global PORT
    con_trails = 0
    client_udp_socket.sendto(json.dumps(request).encode('utf-8'), ('', PORT))
    while 1:
        print('Waiting for response...')
        try:
            con_trails = 0
            response, server_address = client_udp_socket.recvfrom(1024)
            response = json.loads(response.decode('utf-8'))
            return response
        except timeout:
            print('No response from server')
            con_trails += 1
            if con_trails < 3:
                print('Retransmitting...')
                continue
            else:
                print('Connection failed')
                break
```

## Application Layer Message Format & How the System Works

#### Overview

I used json to transfer the data between server and client.
Since the json format is more readable and easy to understand, it is easier to debug code and maintain it.

#### Client side

The Client first read in the input commands and split the commands into different variables.

```python
thread_title = input_commands.split()[1]
message_id = input_commands.split()[2]
message = input_commands.split()[3:]
```

Then it create a request dictionary which contains the actual command, the user info and the split variables

```python
    thread_request = {
        'command': 'RMV',
        'username': user_info['username'],
        'password': user_info['password'],
        'thread_title': thread_title
    }
```

Then it sends the request to the server, and get the response.

```python
response = udp_send_request(udp_s, message_request)
```

Finally, depending on the response of server, the client will print the corresponding message.

```python
    if response['status'] == 'NO_THREAD':
        print('Thread does not exist')
    elif response['status'] == 'FAIL':
        print('Thread cannot be removed')
    elif response['status'] == 'OK':
        print('Thread removed')
```

#### Server side

The server first read in the request from the client and convert the request to data and address.

```python
data, add = udp_receive_data(udp_socket)
```

Then it pass the data and address to the client_handler function.

```python
thread = threading.Thread(target=client_handler, args=(udp_socket, data, add))
```

The client_handler function will check the command and call the corresponding function.

```python
user, command = data['username'], data['command']
print("{} issued {} command".format(user, command))
if command == 'AUTH':
    users, online_users = AUTH_USER(data, add, users, online_users, client_udp_socket)
    return
```

Then it will send back a response depending on the data of the request from client.

```python
response = {
    'status': 'OK',
}
thread_title, thread_creator, msg_index = data['thread_title'], data['username'], data['message_id']
if thread_title not in threads:
    response['status'] = 'NO_THREAD'
    print('Thread {} does not exist'.format(thread_title))
    udp_send_response(client_udp_socket, response, add)
```

Finally, the client will check the status of the response and print the corresponding message.
