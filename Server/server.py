'''
Created Mar 15, 2022

@author: Wang Liao, z5306312

Usage: python3 server.py [port]

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
'''

'''
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

'''

from http import client
import sys
import threading
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
clients = set()
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
    # create a UDP socket
    udp_socket = socket(AF_INET, SOCK_DGRAM)
    udp_socket.bind(('', port))
    udp_socket.settimeout(5) 

    print("Waiting for clients")

    while True:
        try:
            data, add = udp_receive_data(udp_socket)
            clients.add(add)
            thread = threading.Thread(target=client_handler, args=(udp_socket, data, add))
            thread.daemon = True 
            thread.start()

        except timeout:
            pass

    # close the sockets
    udp_socket.close()

    print("Server is shutting down")
def client_handler(client_udp_socket, data, add):
    global threads
    global users
    global online_users
    global files
    # global messages

    user = data['username']
    command = data['command']

    print("{} issued {} command".format(user, command))

    if command == 'AUTH':
        users, online_users = AUTH_USER(data, add, users, online_users, client_udp_socket)
        return
    elif command == 'CRT':
        threads = CREATE_THREAD(data, add, threads, client_udp_socket)
        return
    elif command == 'LST':
        LIST_THREADS(threads, add, client_udp_socket)
        return
    elif command == 'MSG':
        POST_MESSAGE(data, add, threads, client_udp_socket)
        return
    elif command == 'DLT':
        DELETE_MESSAGE(data, add, threads, client_udp_socket)
        return
    elif command == 'RDT':
        READ_THREAD(data, add, threads, client_udp_socket)
        return
    elif command == 'EDT':
        EDIT_MESSAGE(data, add, threads, client_udp_socket)
        return
    elif command == 'UPD':
        files = UPLOAD_FILE(data, add, files, threads, client_udp_socket)
        return
    elif command == 'DWN':
        DOWNLOAD_FILE(data, add, threads, files, client_udp_socket)
        return
    elif command == 'RMV':
        threads = REMOVE_THREAD(data, add, threads, client_udp_socket)
        return
    elif command == 'XIT':
        online_users = EXIT_USER(data, add, online_users, client_udp_socket)
        return

def udp_send_response(udp_soc, response, client_add):
    udp_soc.sendto(json.dumps(response).encode('utf-8'), client_add)
    print('Sent response {} to client'.format(response))

def udp_receive_data(udp_soc):
    while True:
        try:
            data, add = udp_soc.recvfrom(1024)
            data = json.loads(data.decode('utf-8'))
            print('Received data {} from client'.format(data))
            return data, add
        except timeout:
            continue

########################################################################################################################
#                                                                                                                      #
#                                                COMMAND FUNCTIONS                                                     #                                                                                                       
#                                                                                                                      #
########################################################################################################################
def AUTH_USER(data, add, users, online_users, client_udp_socket):
    global PORT
    response = {
        'type': '',
        'status': 'OK',
    }
    username = data['username']
    print("Client authenticating")

    # if the username is in online_users, then the user is already logged in 
    if username in online_users:
        response['type'] = 'ONLINE'
        response['status'] = 'ERROR'
        print('{} has already logged in'.format(username))

        udp_send_response(client_udp_socket, response, add)
        return users, online_users
    elif username in users:
        response['type'] = 'OLD'
        response['status'] = 'PWDNEED'
        udp_send_response(client_udp_socket, response, add)
    # if the username is not in online_users, then the user is not logged in
    elif username not in users:
        response['type'] = 'NEW'
        response['status'] = 'PWDNEED'
        udp_send_response(client_udp_socket, response, add)

    data, add = udp_receive_data(client_udp_socket)

    password = data['password']

    if username in users:
        if password == users[username]:
            # if the password is correct, then the user is logged in
            response['type'] = 'OLD_SUC'
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
        response['type'] = 'NEW_SUC'
        response['status'] = 'OK'
        print('Welcome, {}'.format(username))
        
        # add the new user to the users dictionary
        users[username] = password
        online_users.append(username)

        # write the new user to credentials.txt
        with open('credentials.txt', 'a+') as f:
            f.write('\n{} {}'.format(username, password))
    
    udp_send_response(client_udp_socket, response, add)

    return users, online_users

def CREATE_THREAD(data, add, threads, client_udp_socket):
    global PORT
    response = {
        'status': 'OK'
    }
    thread_title = data['thread_title']
    thread_creator = data['username']

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
    
    udp_send_response(client_udp_socket, response, add)
    return threads
        
def LIST_THREADS(threads, add, client_udp_socket):
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
    
    udp_send_response(client_udp_socket, response, add)

def POST_MESSAGE(data, add, threads, client_udp_socket):
    global PORT
    response = {
        'status': 'OK',
    }
    thread_title = data['thread_title']
    thread_creator = data['username']
    msg_content = data['message']
    # if the thread title is not in the threads list, then the thread does not exist
    if thread_title not in threads:
        response['status'] = 'FAIL'
        print('Thread {} does not exist'.format(thread_title))
    else:
        # if the thread title is in the threads list, then add the message to the thread
        response['status'] = 'OK'
        msg_index = 0
        with open(thread_title, 'r') as f:
            for line in f:
                msg_index += 1
        with open(thread_title, 'a+') as f:
            f.write('{} {}: {}\n'.format(str(msg_index), thread_creator, msg_content))
        print('{} posted to {} thread'.format(thread_creator, thread_title))

    udp_send_response(client_udp_socket, response, add)
    return threads
        
def DELETE_MESSAGE(data, add, threads, client_udp_socket):
    global PORT
    response = {
        'status': 'OK',
    }
    thread_title = data['thread_title']
    thread_creator = data['username']
    msg_index = data['message_id']

    # if the thread title is not in the threads list and the msg is not in the thread, then return FAIL
    if thread_title not in threads:
        response['status'] = 'NO_THREAD'
        print('Thread {} does not exist'.format(thread_title))
        udp_send_response(client_udp_socket, response, add)
    
    else:
        # if the msg index is out of range, then return FAIL
        if int(msg_index) <= 0:
            response['status'] = 'NO_MSG'
            print('Index of message: {} is out of range'.format(msg_index))
            udp_send_response(client_udp_socket, response, add)

        # find the line that contains the message index
        line_to_remove = ''
        line_num = 0
        with open(thread_title, 'r') as f:
            lines = f.readlines()
            for line in lines:
                if msg_index == line.split()[0]:
                    line_to_remove = line
                    line_num = lines.index(line)
                    break

        # if msg is not in the thread, then return FAIL
        if line_to_remove == '':
            response['status'] = 'NO_MSG'
            print('The message does not exist') 
        # if the user is not the creator of the thread, then return FAIL
        elif thread_creator != lines[line_num].split(' ')[1][:-1]:
            response['status'] = 'FAIL'
            print('Message cannot be deleted')
        # if the user is the creator of the thread, then delete the message
        else:
            response['status'] = 'OK'
            print('Message has been deleted')

            # remove the message from the thread
            with open(thread_title, 'r') as f:
                lines = f.readlines()
                lines.remove(line_to_remove)
            with open(thread_title, 'w') as f:
                f.writelines(lines)
    
        udp_send_response(client_udp_socket, response, add)

def READ_THREAD(data, add, threads, client_udp_socket):
    global PORT
    response = {
        'status': 'OK',
    }
    thread_title = data['thread_title']

    # if the thread title is not in the threads list, then the thread does not exist
    if thread_title not in threads:
        response['status'] = 'FAIL'
        print('Incorrect thread specified')
    else:
        # if the thread title is in the threads list, then get the messages from the thread
        response['messages'] = []
        with open(thread_title, 'r') as f:
            lines = f.readlines()
        response['messages'] = lines[1:]
    
        # if the thread is empty, then return FAIL
        if len(response['messages']) == 0:
            response['status'] = 'NO_MSG'
            print('Thread {} is empty'.format(thread_title))
        else:
            response['status'] = 'OK'
            print('Thread {} has been read'.format(thread_title))

    udp_send_response(client_udp_socket, response, add)

def EDIT_MESSAGE(data, add, threads, client_udp_socket):
    global PORT
    response = {
        'status': 'OK',
    }
    thread_title = data['thread_title']
    thread_creator = data['username']
    msg_index = data['message_id']
    msg_content = data['message']

    # if the thread title is not in the threads list and the msg is not in the thread, then return FAIL
    if thread_title not in threads:
        response['status'] = 'NO_THREAD'
        print('Thread {} does not exist'.format(thread_title))
        udp_send_response(client_udp_socket, response, add)
    
    # if thread exists
    else:
        # if the msg index is out of range, then return FAIL
        if int(msg_index) <= 0:
            response['status'] = 'NO_MSG'
            print('Index of message: {} is out of range'.format(msg_index))
            udp_send_response(client_udp_socket, response, add)
    
        # find the line that contains the message index
        line_to_edit = ''
        line_num = 0
        with open(thread_title, 'r') as f:
            lines = f.readlines()
            for line in lines:
                if msg_index == line.split()[0]:
                    line_to_edit = line
                    line_num = lines.index(line)
                    break

        # if msg is not in the thread, then return FAIL
        if line_to_edit == '':
            response['status'] = 'NO_MSG'
            print('Message does not exist'.format(msg_index))
        # if the user is not the creator of the thread, then return FAIL
        elif thread_creator != lines[line_num].split(' ')[1][:-1]:
            response['status'] = 'FAIL'
            print('Message cannot be edited')
        
        # if the user is the creator of the thread, then edit the message
        else:
            response['status'] = 'OK'
            print('Message has been edited'.format(msg_index))

            # edit the message in the thread
            lines[line_num] = '{} {}: {}\n'.format(msg_index, thread_creator, msg_content)
            
            # add the messages to the thread
            with open(thread_title, 'w+') as f:
                f.writelines(lines)
        
        udp_send_response(client_udp_socket, response, add)
    
    return threads

def UPLOAD_FILE(data, add, files, threads, client_udp_socket):
    global PORT
    response = {
        'status': 'OK',
    }
    thread_title = data['thread_title']
    thread_creator = data['username']
    file_name = data['file_name']
    file_size = data['file_size']

    # if the thread title is not in the threads list and the msg is not in the thread, then return FAIL
    if thread_title not in threads:
        response['status'] = 'FAIL'
        print('Thread {} does not exist'.format(thread_title))
        udp_send_response(client_udp_socket, response, add)
    else:
        # if the thread title is in the threads list, then get the messages from the thread
        response['status'] = 'UPLOAD_FILE'
        udp_send_response(client_udp_socket, response, add)

        # create tcp socket to receive the file
        tcp_receive_socket = socket(AF_INET, SOCK_STREAM)
        tcp_receive_socket.bind(('', PORT))
        tcp_receive_socket.listen(1)
        tcp_receive_socket.settimeout(5)
        tcp_client_socket, tcp_client_address = tcp_receive_socket.accept()

        # receive the file
        download_file = open('{}-{}'.format(thread_title, file_name), 'wb')
        while True:
            try:
                data = tcp_client_socket.recv(1024)
                if not data:
                    break
                download_file.write(data)
            except:
                break
        tcp_client_socket.close()
        download_file.close()

        # if the file size is not the same as the one in the request, then return FAIL
        if int(file_size) != os.path.getsize('{}-{}'.format(thread_title, file_name)):
            response['status'] = 'FAIL'
            udp_send_response(client_udp_socket, response, add)
        else:
            # if the file size is the same as the one in the request, then add the file to the thread
            response['status'] = 'OK'
            with open(thread_title, 'a') as f:
                f.write('{} uploaded {}\n'.format(thread_creator, file_name))
            print('{} uploaded file {} to {} thread'.format(thread_creator, file_name, thread_title))
            # add the file to the files list
            files.append('{}-{}'.format(thread_title, file_name))

            udp_send_response(client_udp_socket, response, add)

    return files

def DOWNLOAD_FILE(data, add, threads, files, client_udp_socket):
    response = {
        'status': 'OK',
    }
    thread_title = data['thread_title']
    file_name = data['file_name']

    # if the thread title is not in the threads list and the msg is not in the thread, then return FAIL
    if thread_title not in threads:
        response['status'] = 'FAIL'
        print('Thread {} does not exist'.format(thread_title))
        udp_send_response(client_udp_socket, response, add)
    else:
        # if the file is not in the files list, then return FAIL
        if '{}-{}'.format(thread_title, file_name) not in files:
            response['status'] = 'FILE_NOT_FOUND'
            print('File {} does not exist'.format(file_name))
            udp_send_response(client_udp_socket, response, add)
        else:
            # if the file is in the files list, then send the file
            response['status'] = 'FILE_FOUND'
            response['file_size'] = os.stat('{}-{}'.format(thread_title, file_name)).st_size
            udp_send_response(client_udp_socket, response, add)

            # create tcp socket to send the file to the client
            tcp_send_socket = socket(AF_INET, SOCK_STREAM)
            tcp_send_socket.bind(('', PORT))
            tcp_send_socket.listen(1)
            tcp_send_socket.settimeout(5)
            tcp_client_socket, tcp_client_address = tcp_send_socket.accept()

            # send the file
            with open('{}-{}'.format(thread_title, file_name), 'rb') as f:
                while True:
                    data = f.read(1024)
                    if not data:
                        break
                    tcp_client_socket.send(data)
            tcp_client_socket.close()
            tcp_send_socket.close()

            data, add = udp_receive_data(client_udp_socket)
            if data['status'] == 'OK':
                print('{} downloaded file {} from {} thread'.format(data['username'], file_name, thread_title))
            elif data['status'] == 'FAIL':
                print('{} failed to download file {} from {} thread'.format(data['username'], file_name, thread_title))

def REMOVE_THREAD(data, add, threads, client_udp_socket):
    response = {
        'status': 'OK',
    }
    thread_title = data['thread_title']
    thread_creator = data['username']

    # if the thread title is not in the threads list, then return FAIL
    if thread_title not in threads:
        response['status'] = 'NO_THREAD'
        print('Thread {} does not exist'.format(thread_title))
        udp_send_response(client_udp_socket, response, add)
    else:
        with open(thread_title, 'r') as f:
            lines = f.readlines()
    
        # if the user is not the creator of the thread, then return FAIL
        if thread_creator != lines[0].split(' ')[0].rstrip():
            response['status'] = 'FAIL'
            print('Thread {} cannot be removed'.format(thread_title))
        
        # if the user is the creator of the thread, then remove the thread
        else:
            response['status'] = 'OK'
            print('Thread {} removed'.format(thread_title))
            os.remove(thread_title)
            threads.remove(thread_title)

        udp_send_response(client_udp_socket, response, add)
    return threads

def EXIT_USER(data, add, online_users, client_udp_socket):
    response = {
        'status': 'OK',
    }
    user_name = data['username']

    # if the user is not in the online users list, then return FAIL
    if user_name not in online_users:
        response['status'] = 'FAIL'
        print('User {} is not online'.format(user_name))
    else:
        response['status'] = 'OK'
        print('{} exited'.format(user_name))
        online_users.remove(user_name)

    udp_send_response(client_udp_socket, response, add)
    return online_users

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