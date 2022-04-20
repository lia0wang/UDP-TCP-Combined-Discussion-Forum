'''
Created Mar 15, 2022
@author: Wang Liao, z5306312
Usage: python3 client.py [port]
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
'''


'''
Design:
    Upon initiation, the client should first execute the user authentication process,
    following authentication, the user should be prompted to enter the commands.
    almost all commands require request/response, so the client should send the request to the server
    the client should not maintain any state about the discussion forum
'''

import hashlib
from re import T
import sys
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
state = False # a boolean variable to check if the client is connected to the server
commands = ['CRT', 'LST', 'MSG', 'DLT', 'RDT', 'EDT', 'UPD', 'DWN', 'RMV', 'XIT']
user_info = {} # a dictionary to store the information of the user
user_info['username'] = ''
user_info['password'] = ''

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
        print('Usage: python3 client.py [port]')
        sys.exit()

    port = int(sys.argv[1])
    if port < 1024 or port > 65535:
        print('Port number must be between 1024 and 65535')
        sys.exit()
    
    return port

def command_error_checker(input_commands):
    '''
    This function is used to check if the command is valid.
    '''
    command = input_commands.split()[0]
    len_command = len(input_commands.split())
    if command not in commands:
        print('Invalid command')
        return True
    elif command == 'LST' and len_command != 1:
        print('Invalid usage of {}'.format(command))
        return True
    elif command in ['CRT','RDT', 'RMV'] and len_command != 2:
        print('Invalid usage of {}'.format(command))
        return True
    elif command == 'DLT' and len_command != 3:
        print('Invalid usage of {}'.format(command))
        return True
    elif command in ['MSG', 'UPD', 'DWN'] and len_command < 3:
        print('Invalid usage of {}'.format(command))
        return True
    elif command == 'EDT' and len_command < 4:
        print('Invalid usage of {}'.format(command))
        return True
    elif command == 'XIT' and len_command != 1:
        print('Invalid usage of {}'.format(command))
        return True
    return False

def command_executer(input_commands, udp_s):
    '''
    This function is used to execute the command.
    '''
    command = input_commands.split()[0]
    if command == 'CRT':
        CREATE_THREAD(input_commands, udp_s)
    elif command == 'LST':
        LIST_THREADS(input_commands, udp_s)
    elif command == 'MSG':
        POST_MESSAGE(input_commands, udp_s)
    elif command == 'DLT':
        DELETE_MESSAGE(input_commands, udp_s)
    elif command == 'RDT':
        READ_THREAD(input_commands, udp_s)
    elif command == 'EDT':
        EDIT_MESSAGE(input_commands, udp_s)
    elif command == 'UPD':
        UPLOAD_FILE(input_commands, udp_s)
    elif command == 'DWN':
        DOWNLOAD_FILE(input_commands, udp_s)
    elif command == 'RMV':
        REMOVE_THREAD(input_commands, udp_s)
    elif command == 'XIT':
        EXIT_USER(input_commands, udp_s)

def client_startup(port):
    '''
    This function is used to start the client.
    '''

    # create a udp socket for the client to send the request to the server
    udp_socket = socket(AF_INET, SOCK_DGRAM)
    # udp_socket.settimeout(1)

    AUTH_USER(udp_socket)
    
    is_continue = False
    while True:
        input_commands = input('Enter one of the following commands: CRT, MSG, DLT, EDT, LST, RDT, UPD, DWN, RMV, XIT:').strip()
        is_continue = command_error_checker(input_commands)
        if is_continue:
            continue
        command_executer(input_commands, udp_socket)

    print('Connection closed')
    udp_socket.close()

def udp_send_request(client_udp_socket, request):
    global PORT
    con_trails = 0
    client_udp_socket.sendto(json.dumps(request).encode('utf-8'), ('', PORT))
    print('Sent request {} to server'.format(request))  

    while 1:
        print('Waiting for response...')
        try:
            con_trails = 0
            response, server_address = client_udp_socket.recvfrom(1024)
            response = json.loads(response.decode('utf-8'))
            print('Received response {} from server'.format(response))
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

def udp_receive_response(client_udp_socket):
    global PORT
    con_trails = 0
    while 1:
        print('Waiting for response...')
        try:
            con_trails = 0
            response, server_address = client_udp_socket.recvfrom(1024)
            response = json.loads(response.decode('utf-8'))
            print('Received response {} from server'.format(response))
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

    # while True:
    #     try:
    #         if i < 11:
                
    #             i=i+1
    #             client_udp_socket.settimeout(2)

    #             response, server_address = client_udp_socket.recvfrom(1024)
    #             response = json.loads(response.decode('utf-8'))
    #             print('Received response {} from server'.format(response))

    #             return response
    #     except timeout:
    #         print('CLIENT: Request timeout, retransmission')
    #         continue

########################################################################################################################
#                                                                                                                      #
#                                                 COMMANDS CLASS                                                       #                                                                                                                                                           
#                                                                                                                      #
########################################################################################################################
def AUTH_USER(udp_socket):
    '''
    This function is used to authenticate the user.
    '''
    while True:
        username = input('Enter username: ')
        username = username.strip()
        password = ''

        request = {'command': 'AUTH', 'username': username}
        response = udp_send_request(udp_socket, request)
        # response = udp_receive_response(udp_socket)

        # if the user is already logged in
        if response['type'] == 'ONLINE':
            print('{} has already logged in'.format(username))
            continue
        elif response['type'] == 'OLD':
            password = input('Enter password: ')
        # if the user is not online
        elif response['type'] == 'NEW':
            password = input('New user, enter password: ')
        
        # send the password to the server
        request = {'command': 'AUTH', 'username': username, 'password': password}
        response = udp_send_request(udp_socket, request)
        # response = udp_receive_response(udp_socket)

        # if response is correct
        if response['status'] == 'OK':
            print('Welcome to the forum')
            global user_info
            user_info['username'] = username
            user_info['password'] = password
            break
        elif response['status'] == 'FAIL':
            print('Wrong username or password')
            continue

def CREATE_THREAD(input_commands, udp_s):
    '''
    This function is used to create a thread.
    '''
    global user_info
    # get the thread title
    thread_title = input_commands.split()[1]
    # create a thread request
    thread_request = {
        'command': 'CRT',
        'username': user_info['username'],
        'password': user_info['password'],
        'thread_title': thread_title
    }
    # send the request to the server and get the response
    response = udp_send_request(udp_s, thread_request)

    # check if the thread is created successfully
    if response['status'] == 'OK':
        print('Thread {} created'.format(thread_title))
    elif response['status'] == 'FAIL':
        print('Thread {} exists'.format(thread_title))

def LIST_THREADS(input_commands, udp_s):
    '''
    This function is used to list all the threads.
    '''
    global user_info
    # create a thread request
    thread_request = {
        'command': 'LST',
        'username': user_info['username'],
        'password': user_info['password']
    }
    # send the request to the server and get the response
    response = udp_send_request(udp_s, thread_request)

    # check if the thread is created successfully
    if response['status'] == 'OK':
        print('The list of active threads:')
        for thread in response['threads']:
            print('{}'.format(thread))
    elif response['status'] == 'FAIL':
        print('No threads to list')

def POST_MESSAGE(input_commands, udp_s):
    '''
    This function is used to post a message.
    '''
    global user_info
    # get the thread title
    thread_title = input_commands.split()[1]
    # get the message
    message = input_commands.split()[2:]
    # create a message request
    message_request = {
        'command': 'MSG',
        'username': user_info['username'],
        'password': user_info['password'],
        'thread_title': thread_title,
        'message': ' '.join(message)
    }
    # send the request to the server and get the response
    response = udp_send_request(udp_s, message_request)

    # check if the message is posted successfully
    if response['status'] == 'OK':
        print('Message posted to {} thread'.format(thread_title))
    elif response['status'] == 'FAIL':
        print('Thread {} does not exist'.format(thread_title))

def DELETE_MESSAGE(input_commands, udp_s):
    '''
    This function is used to delete a message.
    '''
    global user_info
    # get the thread title
    thread_title = input_commands.split()[1]
    # get the message id
    message_id = input_commands.split()[2]
    # create a message request
    message_request = {
        'command': 'DLT',
        'username': user_info['username'],
        'password': user_info['password'],
        'thread_title': thread_title,
        'message_id': message_id
    }
    # send the request to the server and get the response
    response = udp_send_request(udp_s, message_request)
    
    # check if the message is deleted successfully
    if response['status'] == 'OK':
        print('The message has been deleted')
    elif response['status'] == 'FAIL':
        print('The message belongs to another user and cannot be edited')
    elif response['status'] == 'NO_MSG':
        print('The message does not exist')
    elif response['status'] == 'NO_THREAD':
        print('The thread does not exist')

def READ_THREAD(input_commands, udp_s):
    '''
    This function is used to read a thread.
    '''
    global user_info
    # get the thread title
    thread_title = input_commands.split()[1]
    # create a thread request
    thread_request = {
        'command': 'RDT',
        'username': user_info['username'],
        'password': user_info['password'],
        'thread_title': thread_title
    }
    # send the request to the server and get the response
    response = udp_send_request(udp_s, thread_request)

    # check if the thread is read successfully
    if response['status'] == 'OK':
        print('The messages in {} thread:'.format(thread_title))
        for message in response['messages']:
            print('{}'.format(message.strip()))
    elif response['status'] == 'FAIL':
        print('Thread {} does not exist'.format(thread_title))
    elif response['status'] == 'NO_MSG':
        print('No messages in the thread {}'.format(thread_title))

def EDIT_MESSAGE(input_commands, udp_s):
    '''
    This function is used to edit a message.
    '''
    global user_info
    # get the thread title
    thread_title = input_commands.split()[1]
    # get the message id
    message_id = input_commands.split()[2]
    # get the message
    message = input_commands.split()[3:]
    # create a message request
    message_request = {
        'command': 'EDT',
        'username': user_info['username'],
        'password': user_info['password'],
        'thread_title': thread_title,
        'message_id': message_id,
        'message': ' '.join(message)
    }
    # send the request to the server and get the response
    response = udp_send_request(udp_s, message_request)

    # check if the message is edited successfully
    if response['status'] == 'OK':
        print('The message has been edited')
    elif response['status'] == 'FAIL':
        print('The message belongs to another user and cannot be edited')
    elif response['status'] == 'NO_MSG':
        print('The message does not exist')
    elif response['status'] == 'NO_THREAD':
        print('The thread does not exist')

def UPLOAD_FILE(input_commands, udp_s):
    '''
    This function is used to upload a file.
    '''
    global user_info
    global PORT
    # get the thread title
    thread_title = input_commands.split()[1]
    # get the file name
    file_name = input_commands.split()[2]

    # check if the file exists
    if not os.path.exists(file_name):
        print('File {} does not exist'.format(file_name))
        return

    # get the file size
    file_size = os.path.getsize(file_name)
    # create a file request
    file_request = {
        'command': 'UPD',
        'username': user_info['username'],
        'password': user_info['password'],
        'thread_title': thread_title,
        'file_name': file_name,
        'file_size': file_size
    }
    # send the request to the server and get the response
    response = udp_send_request(udp_s, file_request)

    # check if the file is uploaded successfully
    if response['status'] == 'FAIL':
        print('Thread {} does not exist'.format(thread_title))
    else:
        # create a socket to send the file
        file_s = socket(AF_INET, SOCK_STREAM)
        file_s.connect(('', PORT))
        # send the file
        with open(file_name, 'rb') as f:
            file_s.sendall(f.read())
        # close the socket
        file_s.close()

        # receive the response from the server
        response = udp_receive_response(udp_s)

        # check if the file is uploaded successfully
        if response['status'] == 'OK':
            print('{} uploaded {}'.format(thread_title, file_name))
        elif response['status'] == 'FAIL':
            print('{} has been corrupted'.format(file_name))

def DOWNLOAD_FILE(input_commands, udp_s):
    '''
    This function is used to download a file.
    '''
    global user_info
    global PORT
    # get the thread title
    thread_title = input_commands.split()[1]
    # get the file name
    file_name = input_commands.split()[2]
    # create a file request
    file_request = {
        'command': 'DWN',
        'username': user_info['username'],
        'password': user_info['password'],
        'thread_title': thread_title,
        'file_name': file_name,
        'status': ''
    }
    # send the request to the server and get the response
    response = udp_send_request(udp_s, file_request)

    # check if the file is found
    if response['status'] == 'FAIL':
        print('Thread {} does not exist'.format(thread_title))
    elif response['status'] == 'FILE_NOT_FOUND':
        print('File {} does not exist'.format(file_name))
    elif response['status'] == 'FILE_FOUND':

        # create a socket to receive the file
        file_s = socket(AF_INET, SOCK_STREAM)
        file_s.connect(('', PORT))

        # receive the file
        with open(file_name, 'wb') as f:
            while True:
                data = file_s.recv(1024)
                if not data:
                    break
                f.write(data)
        # close the socket
        file_s.close()

        file_size = response['file_size']
        # check if the file is downloaded successfully
        if os.path.getsize(file_name) == int(file_size):
            print('{} downloaded {}'.format(thread_title, file_name))
            file_request['status'] = 'OK'
        else:
            print('{} has been corrupted'.format(file_name))
            file_request['status'] = 'FAIL'
        # send the request to the server and get the response
        udp_s.sendto(json.dumps(file_request).encode('utf-8'), ('', PORT))

def REMOVE_THREAD(input_commands, udp_s):
    '''
    This function is used to remove a thread.
    '''
    global user_info
    # get the thread title
    thread_title = input_commands.split()[1]
    # create a thread request
    thread_request = {
        'command': 'RMV',
        'username': user_info['username'],
        'password': user_info['password'],
        'thread_title': thread_title
    }
    # send the request to the server and get the response
    response = udp_send_request(udp_s, thread_request)

    # check if the thread is removed successfully
    if response['status'] == 'NO_THREAD':
        print('Thread does not exist')
    elif response['status'] == 'FAIL':
        print('Thread cannot be removed')
    elif response['status'] == 'OK':
        print('Thread removed')

def EXIT_USER(input_commands, udp_s):
    '''
    This function is used to exit the program.
    '''
    global user_info
    # create a thread request
    thread_request = {
        'command': 'XIT',
        'username': user_info['username'],
        'password': user_info['password']
    }
    # send the request to the server and get the response
    response = udp_send_request(udp_s, thread_request)

    # check if the thread is removed successfully
    if response['status'] == 'OK':
        print('Goodbye')
        sys.exit()
    elif response['status'] == 'FAIL':
        print('Uer {} is not online'.format(user_info['username']))

########################################################################################################################
#                                                                                                                      #
#                                                  MAIN FUNCTION                                                       #                                                                                                                                                           
#                                                                                                                      #
########################################################################################################################
if __name__ == '__main__':
    PORT = port_checker()
    client_startup(PORT)