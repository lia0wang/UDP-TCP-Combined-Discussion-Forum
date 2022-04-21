'''
Created Mar 15, 2022

@author: Wang Liao, z5306312

Usage: python3 client.py [port]
'''

########################################################################################################################
#                                                                                                                      #
#                                                      LIBRARIES                                                       #                                                                                       
#                                                                                                                      #
########################################################################################################################
import os
import sys
import json
import time
from socket import *
from _thread import *

########################################################################################################################
#                                                                                                                      #
#                                                   GLOBAL VARIABLES                                                   #                                                                                                       
#                                                                                                                      #
########################################################################################################################
PORT = None
commands = ['CRT', 'LST', 'MSG', 'DLT', 'RDT', 'EDT', 'UPD', 'DWN', 'RMV', 'XIT']
user_info = {}
user_info['username'] = ''
user_info['password'] = ''

########################################################################################################################
#                                                                                                                      #
#                                                    HELPER FUNCTIONS                                                  #                                                                                                       
#                                                                                                                      #
########################################################################################################################
def port_checker():
    '''
    Check if the port is valid.
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
    Check if the command is valid.
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
    Execute the input commands.
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
    Start the client.
    '''
    # create a UDP socket
    udp_socket = socket(AF_INET, SOCK_DGRAM)
    udp_socket.settimeout(5)

    AUTH_USER(udp_socket)
    
    is_error = False
    while True:
        input_commands = input('Enter one of the following commands: CRT, MSG, DLT, EDT, LST, RDT, UPD, DWN, RMV, XIT:').strip()
        is_error = command_error_checker(input_commands)
        if is_error: # if the command has error, re-enter the command
            continue
        command_executer(input_commands, udp_socket)

    udp_socket.close()

def udp_send_request(client_udp_socket, request):
    '''
    send the request to the server and get the response.
    '''
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
            # print('Received response {} from server'.format(response))
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
    '''
    get the response from the server.
    '''
    global PORT
    con_trails = 0
    while 1:
        print('Waiting for response...')
        try:
            con_trails = 0
            response, server_address = client_udp_socket.recvfrom(1024)
            response = json.loads(response.decode('utf-8'))
            # print('Received response {} from server'.format(response))
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

########################################################################################################################
#                                                                                                                      #
#                                                 COMMANDS FUNCTIONS                                                   #                                                                                                                                                           
#                                                                                                                      #
########################################################################################################################
def AUTH_USER(udp_socket):
    '''
    User authentication.
    '''
    while True:
        username = input('Enter username: ')
        username = username.strip()
        password = ''

        request = {'command': 'AUTH', 'username': username}
        response = udp_send_request(udp_socket, request)

        # if the user is already logged in, ask re-enter the username
        if response['type'] == 'ONLINE':
            print('{} has already logged in'.format(username))
            continue
        elif response['type'] == 'OLD': # if the user is registered
            password = input('Enter password: ')
        # if the user is a new user
        elif response['type'] == 'NEW':
            password = input('New user, enter password: ')
        
        # get the password and send it to the server
        request = {'command': 'AUTH', 'username': username, 'password': password}
        response = udp_send_request(udp_socket, request)

        # if authentication success
        if response['status'] == 'OK':
            print('Welcome to the forum')
            global user_info
            # get the user info
            user_info['username'] = username
            user_info['password'] = password
            break
        elif response['status'] == 'FAIL':
            print('Wrong username or password')
            continue

def CREATE_THREAD(input_commands, udp_s):
    '''
    Create a new thread.
    '''
    global user_info
    thread_title = input_commands.split()[1]
    thread_request = {
        'command': 'CRT',
        'username': user_info['username'],
        'password': user_info['password'],
        'thread_title': thread_title
    }

    response = udp_send_request(udp_s, thread_request)

    # if the thread is created successfully
    if response['status'] == 'OK':
        print('Thread {} created'.format(thread_title))
    elif response['status'] == 'FAIL':
        print('Thread {} exists'.format(thread_title))

def LIST_THREADS(input_commands, udp_s):
    '''
    List all the threads.
    '''
    global user_info
    thread_request = {
        'command': 'LST',
        'username': user_info['username'],
        'password': user_info['password']
    }

    response = udp_send_request(udp_s, thread_request)

    # if the threads is not empty, list them
    if response['status'] == 'OK':
        print('The list of active threads:')
        for thread in response['threads']:
            print('{}'.format(thread))
    elif response['status'] == 'FAIL':
        print('No threads to list')

def POST_MESSAGE(input_commands, udp_s):
    '''
    Post a message to a thread.
    '''
    global user_info
    thread_title = input_commands.split()[1]
    message = input_commands.split()[2:]
    message_request = {
        'command': 'MSG',
        'username': user_info['username'],
        'password': user_info['password'],
        'thread_title': thread_title,
        'message': ' '.join(message)
    }

    response = udp_send_request(udp_s, message_request)

    # if the message is posted successfully
    if response['status'] == 'OK':
        print('Message posted to {} thread'.format(thread_title))
    # if the thread does not exist
    elif response['status'] == 'FAIL':
        print('Thread {} does not exist'.format(thread_title))

def DELETE_MESSAGE(input_commands, udp_s):
    '''
    Delete a message from a thread.
    '''
    global user_info
    thread_title = input_commands.split()[1]
    message_id = input_commands.split()[2]
    message_request = {
        'command': 'DLT',
        'username': user_info['username'],
        'password': user_info['password'],
        'thread_title': thread_title,
        'message_id': message_id
    }

    response = udp_send_request(udp_s, message_request)
    
    # if the message is deleted successfully
    if response['status'] == 'OK':
        print('The message has been deleted')
    # if the message is not created by the user
    elif response['status'] == 'FAIL':
        print('The message belongs to another user and cannot be edited')
    # if the message does not exist
    elif response['status'] == 'NO_MSG':
        print('The message does not exist')
    # if the thread does not exist
    elif response['status'] == 'NO_THREAD':
        print('The thread does not exist')

def READ_THREAD(input_commands, udp_s):
    '''
    Return the messages in the thread.
    '''
    global user_info
    thread_title = input_commands.split()[1]
    thread_request = {
        'command': 'RDT',
        'username': user_info['username'],
        'password': user_info['password'],
        'thread_title': thread_title
    }

    response = udp_send_request(udp_s, thread_request)

    # if the thread is not empty, list them
    if response['status'] == 'OK':
        print('The messages in {} thread:'.format(thread_title))
        for message in response['messages']:
            print('{}'.format(message.strip()))
    # if the thread does not exist
    elif response['status'] == 'FAIL':
        print('Thread {} does not exist'.format(thread_title))
    # if the thread exists but is empty
    elif response['status'] == 'NO_MSG':
        print('No messages in the thread {}'.format(thread_title))

def EDIT_MESSAGE(input_commands, udp_s):
    '''
    Edit a message in a thread.
    '''
    global user_info
    thread_title = input_commands.split()[1]
    message_id = input_commands.split()[2]
    message = input_commands.split()[3:]
    message_request = {
        'command': 'EDT',
        'username': user_info['username'],
        'password': user_info['password'],
        'thread_title': thread_title,
        'message_id': message_id,
        'message': ' '.join(message)
    }

    response = udp_send_request(udp_s, message_request)

    # if the message is edited successfully
    if response['status'] == 'OK':
        print('The message has been edited')
    # if the message is not created by the user
    elif response['status'] == 'FAIL':
        print('The message belongs to another user and cannot be edited')
    # if the message does not exist
    elif response['status'] == 'NO_MSG':
        print('The message does not exist')
    # if the thread does not exist
    elif response['status'] == 'NO_THREAD':
        print('The thread does not exist')

def UPLOAD_FILE(input_commands, udp_s):
    '''
    Upload a file to the thread.
    '''
    global user_info
    global PORT
    thread_title = input_commands.split()[1]
    file_name = input_commands.split()[2]

    # check if the file exists in the current path
    if not os.path.exists(file_name):
        print('File {} does not exist'.format(file_name))
        return

    # get the file size
    file_size = os.path.getsize(file_name)

    file_request = {
        'command': 'UPD',
        'username': user_info['username'],
        'password': user_info['password'],
        'thread_title': thread_title,
        'file_name': file_name,
        'file_size': file_size
    }

    response = udp_send_request(udp_s, file_request)

    # if the thread does not exist
    if response['status'] == 'FAIL':
        print('Thread {} does not exist'.format(thread_title))
    else:
        # the thread exists, create a tcp socket to send the file
        file_s = socket(AF_INET, SOCK_STREAM)
        file_s.connect(('', PORT))

        # send the file to the server
        with open(file_name, 'rb') as f:
            file_s.sendall(f.read())
        file_s.close() # close the socket immediately after file transfer

        response = udp_receive_response(udp_s)

        # if the file is uploaded successfully
        if response['status'] == 'OK':
            print('{} uploaded {}'.format(thread_title, file_name))
        # if the file size is incorrect
        elif response['status'] == 'FAIL':
            print('{} has been corrupted'.format(file_name))

def DOWNLOAD_FILE(input_commands, udp_s):
    '''
    Download a file from the thread.
    '''
    global user_info
    global PORT
    thread_title = input_commands.split()[1]
    file_name = input_commands.split()[2]
    file_request = {
        'command': 'DWN',
        'username': user_info['username'],
        'password': user_info['password'],
        'thread_title': thread_title,
        'file_name': file_name,
        'status': ''
    }

    response = udp_send_request(udp_s, file_request)

    # if the thread does not exist
    if response['status'] == 'FAIL':
        print('Thread {} does not exist'.format(thread_title))
    # if the file does not exist
    elif response['status'] == 'FILE_NOT_FOUND':
        print('File {} does not exist'.format(file_name))
    # if the file exists
    elif response['status'] == 'FILE_FOUND':

        # create a tcp socket to receive the file from the server
        file_s = socket(AF_INET, SOCK_STREAM)
        file_s.connect(('', PORT))

        # receive the file
        with open(file_name, 'wb') as f:
            while True:
                data = file_s.recv(1024)
                if not data:
                    break
                f.write(data)
        file_s.close() # close the socket immediately after file transfer

        file_size = response['file_size'] # get the file size

        # if the size of downloaded file is same as the size of the file in the server
        if os.path.getsize(file_name) == int(file_size):
            print('{} downloaded {}'.format(thread_title, file_name))
            file_request['status'] = 'OK'
        else:
            print('{} has been corrupted'.format(file_name))
            file_request['status'] = 'FAIL'

        udp_s.sendto(json.dumps(file_request).encode('utf-8'), ('', PORT))

def REMOVE_THREAD(input_commands, udp_s):
    '''
    Remove a thread.
    '''
    global user_info
    thread_title = input_commands.split()[1]
    thread_request = {
        'command': 'RMV',
        'username': user_info['username'],
        'password': user_info['password'],
        'thread_title': thread_title
    }

    response = udp_send_request(udp_s, thread_request)

    # if the thread does not exist
    if response['status'] == 'NO_THREAD':
        print('Thread does not exist')
    # if the thread is not created by the user
    elif response['status'] == 'FAIL':
        print('Thread cannot be removed')
    elif response['status'] == 'OK':
        print('Thread removed')

def EXIT_USER(input_commands, udp_s):
    '''
    This function is used to exit the program.
    '''
    global user_info
    thread_request = {
        'command': 'XIT',
        'username': user_info['username'],
        'password': user_info['password']
    }

    response = udp_send_request(udp_s, thread_request)

    # if the user is online
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