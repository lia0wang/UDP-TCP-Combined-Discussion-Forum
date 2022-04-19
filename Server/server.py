'''
Created Mar 15, 2022

@author: Wang Liao, z5306312

Usage: python3 server.py [port]

Description:
    This is the server side for the discussion forum, the client and server must communicate using both TCP and UDP.
    The server should concurrently open a UDP and TCP port.
    User multi-threading to handle the request from clients concurrently.
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
'''

'''
Design:
    When the server starts up, the forum is empty. - no threads, no messages, no uploaded files.
    The server should open a UDP socket and wait for an authentication request from the client.
    Once authenticated, the server should should service CRT, LST, MSG, DLT, RDT, EDT, RMV, XIT requests from the client.
    This will require the client and server to exchange messages using UDP.
    The server should concurrently open a TCP socket and wait for a connection from the client.
    Once connected, the server should service DWN and UPD requests from the client.
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

    When interacting with the client, the server should receive the request for a command.

'''
from cgi import print_arguments
import re
import sys
import threading
import select
import time
import os
import json
from socket import *
from _thread import *

########################################################################################################################
#                                                                                                                      #
#                                                   GLOBAL VARIABLES                                                   #                                                                                                       
#                                                                                                                      #
########################################################################################################################
PORT = None # the port number of the server
CLIENT_PORT = 9999
state = False # a boolean variable to indicate whether the server is running
clients = [] # a list of clients
threads = [] # a list of threads
users = {} # a dictionary of users containing username and password
online_users = [] # a list of online users
files = [] # a list of files
# messages = {} # a dictionary of messages containing thread_title, message_id, message_content, message_author

########################################################################################################################
#                                                                                                                      #
#                                                    HELPER FUNCTIONS                                                  #                                                                                                       
#                                                                                                                      #
########################################################################################################################
def port_checker():
    '''
    This function is used to check if the port is valid.
    '''
    if len(sys.argv) != 2:
        print('Usage: python3 server.py [port]')
        exit()

    port = int(sys.argv[1])
    if port < 1024 or port > 65535:
        print('Usage: python3 server.py [port]')
        exit()

    return port

def process_credentials():
    # initialize the credentials of the users
    if not os.path.exists('credentials.txt'):
        print('File not found: credentials.txt')
        exit()
    with open('credentials.txt', 'r+') as f: # open the file in read and write mode
        for user_info in f.readlines():
            user_info = user_info.strip().split(' ')
            users[user_info[0]] = user_info[1]

def server_startup(port):
    global state
    state = True

    # create a UDP socket
    udp_socket = socket(AF_INET, SOCK_DGRAM)
    udp_socket.bind(('localhost', port))
    udp_socket.settimeout(1)

    # create a TCP socket
    tcp_socket = socket(AF_INET, SOCK_STREAM)
    tcp_socket.bind(('localhost', port))
    tcp_socket.listen(5)

    print("Waiting for clients")

    while state:
        # wait for a client to connect
        try:
            client_tcp_socket, client_address = tcp_socket.accept()
            print("con {} address {}".format(udp_socket, client_address))
            print("Client connected to server from {}".format(client_address[0]))
            clients.append(udp_socket)
            if client_tcp_socket:
                clients.append(client_tcp_socket)
            thread = threading.Thread(target=client_handler, args=(client_tcp_socket, udp_socket, client_address))
            thread.daemon = True
            thread.start()

        except timeout:
            pass

    # close the sockets
    udp_socket.close()
    tcp_socket.close()

    print("Server is shutting down")

def client_handler(client_tcp_socket, client_udp_socket, client_address):
    global state
    global threads
    global users
    global online_users
    global files
    # global messages

    while True:
        try:
            request = udp_receive_request(client_udp_socket)
        except timeout:
            continue

        if not request:
            break

        user = request['username']
        command = request['command']
        print("{} issued {} command".format(user, command))

        if command == 'AUTH':
            users, online_users = AUTH(request, users, online_users, client_udp_socket)
        elif command == 'CRT':
            threads = CRT(request, threads, client_udp_socket)
        elif command == 'LST':
            LST(threads, client_udp_socket)
        elif command == 'MSG':
            MSG(request, threads, client_udp_socket)
        elif command == 'DLT':
            DLT(request, threads, client_udp_socket)
        elif command == 'RDT':
            RDT(request, threads, client_udp_socket)
        elif command == 'EDT':
            EDT(request, threads, client_udp_socket)
        elif command == 'UPD':
            files = UPD(request, files, threads, client_tcp_socket, client_udp_socket)
        elif command == 'DWN':
            DWN(request, threads, files, client_tcp_socket, client_udp_socket)
        elif command == 'RMV':
            threads = RMV(request, threads, client_udp_socket)
        elif command == 'XIT':
            online_users.remove(user)
            print("User {} exited".format(user))
            if len(online_users) == 0:
                print("No users online now")

def udp_send_response(response, client_udp_socket):
    '''
    send response to the client
    '''
    global CLIENT_PORT
    response = bytes(json.dumps(response), encoding='utf-8')
    client_udp_socket.sendto(response, ('localhost', CLIENT_PORT))
    print("send response {} to port {}".format(response, CLIENT_PORT))

def tcp_send_response(response, client_tcp_socket):
    response = bytes(json.dumps(response), encoding='utf-8')
    client_tcp_socket.send(response)

def udp_receive_request(client_udp_socket):
    global CLIENT_PORT
    while True:
        try:
            request = client_udp_socket.recvfrom(1024)[0]
            request = request.decode('utf-8')
            request = json.loads(request)
            print("received request {} from port {}".format(request, CLIENT_PORT))
            return request
        except timeout:
            continue

########################################################################################################################
#                                                                                                                      #
#                                                COMMAND FUNCTIONS                                                     #                                                                                                       
#                                                                                                                      #
########################################################################################################################
def AUTH(request, users, online_users, client_udp_socket):
    global PORT
    response = {
        'type': '',
        'status': 'OK',
    }
    username = request['username']
    print("Client authenticating")

    # if the username is in online_users, then the user is already logged in 
    if username in online_users:
        response['type'] = 'OLD'
        response['status'] = 'ERROR'
        print('{} has already logged in}'.format(username))

        udp_send_response(response, client_udp_socket)
        return users, online_users
    # if the username is not in online_users, then the user is not logged in
    elif username not in users:
        response['type'] = 'NEW'
        response['status'] = 'OK'
        udp_send_response(response, client_udp_socket)

    request = udp_receive_request(client_udp_socket)

    password = request['password']

    if username in users:
        if password == users[username]:
            # if the password is correct, then the user is logged in
            response['type'] = 'SUC'
            response['status'] = 'OK'
            print('{} successful login'.format(username))
            online_users.append(username)
        else:
            # if the password is incorrect, then the user is not logged in
            response['type'] = 'PWD'
            response['status'] = 'FAIL'
            print('{} Incorrect password'.format(username))
    else:
        # if the username is not in the users dictionary, then create a new user
        response['type'] = 'NEW'
        response['status'] = 'OK'
        print('Welcome, {}'.format(username))
        
        # add the new user to the users dictionary
        users[username] = password
        online_users.append(username)

        # write the new user to credentials.txt
        with open('credentials.txt', 'a+') as f:
            f.write('\n{} {}'.format(username, password))
    
    udp_send_response(response, client_udp_socket)

    return users, online_users

def CRT(request, threads, client_udp_socket):
    global PORT
    response = {
        'status': 'OK'
    }
    thread_title = request['name']
    thread_creator = request['user']

    # if the thread title is in the threads list, then the thread already exists
    if thread_title in threads:
        response['status'] = 'FAIL'
        print('Thread {} exists'.format(thread_title))
    else:
        # if the thread title is not in the threads list, then create a new thread
        response['status'] = 'OK'
        print('Thread {} created'.format(thread_title))

        threads.append(thread_title)
        with open(thread_title, 'w+') as f:
            f.write('{}\n'.format(thread_creator))
    
    udp_send_response(response, client_udp_socket)
    return threads
        
def LST(threads, client_udp_socket):
    global PORT
    response = {
        'status': 'OK',
    }
    
    # if there are no threads, then there are no threads to list
    if len(threads) == 0:
        response['status'] = 'FAIL'
    else:
        # if there are threads, then list them
        response['status'] = 'OK'
        response['threads'] = threads
    
    udp_send_response(response, client_udp_socket)

def MSG(request, threads, client_udp_socket):
    global PORT
    response = {
        'status': 'OK',
    }
    thread_title = request['thread_name']
    thread_creator = request['user']
    msg_content = request['message']
    # if the thread title is not in the threads list, then the thread does not exist
    if thread_title not in threads:
        response['status'] = 'FAIL'
    else:
        # if the thread title is in the threads list, then add the message to the thread
        response['status'] = 'OK'
        msg_index = 0
        with open(thread_title, 'r') as f:
            for line in f:
                msg_index += 1
        with open(thread_title, 'a+') as f:
            f.write('{} {}: {}\n'.format(str(msg_index), thread_creator, msg_content))
        print('Message posted to {} thread'.format(thread_title))

    udp_send_response(response, client_udp_socket)
    return threads
        
def DLT(request, threads, client_udp_socket):
    global PORT
    response = {
        'status': 'OK',
    }
    thread_title = request['thread_name']
    thread_creator = request['user']
    msg_index = request['msg_index']

    # if the thread title is not in the threads list and the msg is not in the thread, then return FAIL
    if thread_title not in threads:
        response['status'] = 'FAIL'
        print('Thread {} does not exist'.format(thread_title))
        udp_send_response(response, client_udp_socket)
    
    # if the msg index is out of range, then return FAIL
    if msg_index <= 0:
        response['status'] = 'FAIL'
        print('Message index {} out of range'.format(msg_index))
        udp_send_response(response, client_udp_socket)

    with open(thread_title, 'r') as f:
        lines = f.readlines()

    # find the line that contains the message index
    line_num = 0
    msg_to_delete = ''
    for line in lines:
        if msg_index in line:
            # if the message index is in the line, get the line number
            line_num = lines.index(line)
            msg_to_delete = line
            break
        else:
            ''.join(line) # remove the newline character from the line
    
    # if the user is not the creator of the thread, then return FAIL
    if thread_creator not in lines[line_num]:
        response['status'] = 'FAIL'
        print('Message {} cannot be deleted'.format(msg_index))
    
    # if msg is not in the thread, then return FAIL
    elif msg_to_delete == '':
        response['status'] = 'FAIL'
        print('Message {} does not exist'.format(msg_index))
    
    # if the user is the creator of the thread, then delete the message
    else:
        response['status'] = 'OK'
        print('Message {} has been deleted'.format(msg_index))

        # remove the message from the thread
        lines.pop(line_num)
        
        # rewrite the thread
        new_lines = []
        # add the thread creator to the thread
        new_lines.append(thread_creator + '\n')
        # add the messages to the thread
        for line in lines[line_num:]:
            line = line.split(' ')
            line[0] = str(int(line[0]) - 1)
            line = ' '.join(line)
            new_lines.append(line)

        with open(thread_title, 'w+') as f:
            f.writelines(new_lines)
    
    udp_send_response(response, client_udp_socket)

def RDT(request, threads, client_udp_socket):
    global PORT
    response = {
        'status': 'OK',
    }
    thread_title = request['thread_name']

    # if the thread title is not in the threads list, then the thread does not exist
    if thread_title not in threads:
        response['status'] = 'FAIL'
        print('Incorrect thread specified')
    else:
        # if the thread title is in the threads list, then get the messages from the thread
        response['status'] = 'OK'
        response['messages'] = []
        with open(thread_title, 'r') as f:
            lines = f.readlines()
        response['messages'] = lines
    
    udp_send_response(response, client_udp_socket)

def EDT(request, threads, client_udp_socket):
    global PORT
    response = {
        'status': 'OK',
    }
    thread_title = request['thread_name']
    thread_creator = request['user']
    msg_index = request['msg_index']
    msg_content = request['message']

    # if the thread title is not in the threads list and the msg is not in the thread, then return FAIL
    if thread_title not in threads:
        response['status'] = 'FAIL'
        print('Thread {} does not exist'.format(thread_title))
        udp_send_response(response, client_udp_socket)
    
    # if the msg index is out of range, then return FAIL
    if msg_index <= 0:
        response['status'] = 'FAIL'
        print('Message index {} out of range'.format(msg_index))
        udp_send_response(response, client_udp_socket)
    
    with open(thread_title, 'r') as f:
        lines = f.readlines()
    
    # find the line that contains the message index
    line_num = 0
    msg_to_edit = ''
    for line in lines:
        if msg_index in line:
            # if the message index is in the line, get the line number
            line_num = lines.index(line)
            msg_to_edit = line
            break
        else:
            ''.join(line)
    
    # if the user is not the creator of the thread, then return FAIL
    if thread_creator not in lines[line_num]:
        response['status'] = 'FAIL'
        print('Message {} cannot be edited'.format(msg_index))

    # if msg is not in the thread, then return FAIL
    elif msg_to_edit == '':
        response['status'] = 'FAIL'
        print('Message {} does not exist'.format(msg_index))
    
    # if the user is the creator of the thread, then edit the message
    else:
        response['status'] = 'OK'
        print('Message {} has been edited'.format(msg_index))

        # edit the message in the thread
        lines[line_num] = '{} {}: {}\n'.format(msg_index, thread_creator, msg_content)
        
        # add the messages to the thread
        with open(thread_title, 'w+') as f:
            f.writelines(lines)
        
    udp_send_response(response, client_udp_socket)
    return threads

def UPD(request, files, threads, client_tcp_socket, client_udp_socket):
    global PORT
    response = {
        'status': 'OK',
    }
    thread_title = request['thread_name']
    thread_creator = request['user']
    file_name = request['file_name']
    file_size = request['file_size']

    # if the thread title is not in the threads list and the msg is not in the thread, then return FAIL
    if thread_title not in threads:
        response['status'] = 'FAIL'
        print('Thread {} does not exist'.format(thread_title))
        udp_send_response(response, client_udp_socket)
    else:
        # if the thread title is in the threads list, then get the messages from the thread
        response['status'] = 'UPD'
        udp_send_response(response, client_udp_socket)

        # receive the file
        download_file = open('{}-{}'.format(thread_title, file_name), 'wb')
        data = client_tcp_socket.recv(1024)

        # loop until the file is fully received
        total_received = 0
        while data:
            download_file.write(data)
            total_received += len(data)
            data = client_tcp_socket.recv(1024)
            if total_received == file_size:
                response['status'] = 'OK'
                print('File {} has been received'.format(file_name))
                break
            elif total_received > file_size:
                response['status'] = 'FAIL'
                print('File {} has been corrupted'.format(file_name))
                break
        download_file.close()

        udp_send_response(response, client_udp_socket)

        # write the file to the thread
        with open(thread_title, 'a') as f:
            f.write('{} uploaded {}\n'.format(thread_creator, file_name))
        print('{} uploaded {} to {}'.format(thread_creator, file_name, thread_title))

        # add the file to the files list
        files.append('{}-{}'.format(thread_title, file_name))

    return files

def DWN(request, threads, files, client_tcp_socket, client_udp_socket):
    response = {
        'status': 'OK',
    }
    thread_title = request['thread_name']
    file_name = request['file_name']

    # if the thread title is not in the threads list and the msg is not in the thread, then return FAIL
    if thread_title not in threads:
        response['status'] = 'FAIL'
        print('Thread {} does not exist'.format(thread_title))
        udp_send_response(response, client_udp_socket)
    else:
        # if the file is not in the files list, then return FAIL
        if '{}-{}'.format(thread_title, file_name) not in files:
            response['status'] = 'FAIL'
            print('File {} does not exist'.format(file_name))
            udp_send_response(response, client_udp_socket)
        else:
            # if the file is in the files list, then send the file
            response['status'] = 'OK'
            response['file_size'] = os.stat('{}-{}'.format(thread_title, file_name)).st_size
            udp_send_response(response, client_udp_socket)

        if response['status'] == 'OK':
            # download the file
            with open('{}-{}'.format(thread_title, file_name), 'rb') as f:
                data = f.read(1024)
                while data:
                    client_tcp_socket.send(data)
                    data = f.read(1024)
            
                response = client_tcp_socket.recv(1024)
                response = json.loads(response.decode('utf-8'))
                
                if response['status'] == 'OK':
                    print('{} downloaded from Thread {}'.format(file_name, thread_title))
                else:
                    print('File {} has been corrupted'.format(file_name))
        
    
def RMV(request, threads, client_udp_socket):
    response = {
        'status': 'OK',
    }
    thread_title = request['thread_name']
    thread_creator = request['user']

    # if the thread title is not in the threads list, then return FAIL
    if thread_title not in threads:
        response['status'] = 'FAIL'
        print('Thread {} does not exist'.format(thread_title))
        udp_send_response(response, client_udp_socket)

    with open(thread_title, 'r') as f:
        lines = f.readlines()
    
    # if the user is not the creator of the thread, then return FAIL
    if thread_creator != lines[0].split(' ')[0].rstrip():
        response['status'] = 'FAIL'
        print('Thread {} cannot be removed by {}'.format(thread_title, thread_creator))
    
    # if the user is the creator of the thread, then remove the thread
    else:
        response['status'] = 'OK'
        print('Thread {} has been removed'.format(thread_title))
        os.remove(thread_title)
        threads.remove(thread_title)

    udp_send_response(response, client_udp_socket)
    return threads
  
########################################################################################################################
#                                                                                                                      #
#                                                  MAIN FUNCTION                                                       #                                                                                                                                                           
#                                                                                                                      #
########################################################################################################################
if __name__ == '__main__':
    PORT = port_checker()
    process_credentials()
    # initialize the threads
    threads = []
    # start the server
    server_startup(PORT)
