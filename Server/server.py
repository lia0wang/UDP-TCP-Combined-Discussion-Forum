'''
Created Mar 15, 2022

@author: Wang Liao, z5306312

Usage: python3 server.py [port]

Python 3.9.7
'''

########################################################################################################################
#                                                                                                                      #
#                                                      LIBRARIES                                                       #                                                                                       
#                                                                                                                      #
########################################################################################################################
import os
import sys
import threading
import json
import time
from socket import *
from _thread import *

########################################################################################################################
#                                                                                                                      #
#                                                  GLOBAL VARIABLES                                                    #                                                                                                       
#                                                                                                                      #
########################################################################################################################
PORT = None
clients = set()
threads = []
users = {}
online_users = [] 
files = [] 

########################################################################################################################
#                                                                                                                      #
#                                                  HELPER FUNCTIONS                                                    #                                                                                                       
#                                                                                                                      #
########################################################################################################################
def port_checker():
    '''
    Check if the port number is valid.
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
    '''
    Process the credentials file.
    ''' 
    # if the credentials file does not exist
    if not os.path.exists('credentials.txt'):
        print('File not found: credentials.txt')
        exit()

    # read the credentials file
    with open('credentials.txt', 'r+') as f:
        for user_info in f.readlines():
            user_info = user_info.strip().split(' ')
            users[user_info[0]] = user_info[1]

def server_startup(port):
    '''
    Start up the server.
    '''
    # create a UDP socket
    udp_socket = socket(AF_INET, SOCK_DGRAM)
    udp_socket.bind(('', port))
    udp_socket.settimeout(5) 
    print("Waiting for clients")

    while True:
        try:
            data, add = udp_receive_data(udp_socket)
            clients.add(add)
            thread = threading.Thread(target=client_handler, args=(udp_socket, data, add)) # create a new thread for each client
            thread.daemon = True # the main thread can exit when the server is stopped
            thread.start()

        except timeout:
            pass

    udp_socket.close()

def client_handler(client_udp_socket, data, add):
    ''' 
    Handle the client requests.
    '''
    global threads
    global users
    global online_users
    global files

    user, command = data['username'], data['command']

    if command != 'AUTH':
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
    ''' 
    Send the response to the client.
    '''
    udp_soc.sendto(json.dumps(response).encode('utf-8'), client_add)
    # print('Sent response {} to client'.format(response))

def udp_receive_data(udp_soc):
    ''' 
    Receive the data from the client.
    '''
    while True:
        try:
            data, add = udp_soc.recvfrom(1024)
            data = json.loads(data.decode('utf-8'))
            # print('Received data {} from client'.format(data))
            return data, add
        except timeout:
            continue

########################################################################################################################
#                                                                                                                      #
#                                                COMMAND FUNCTIONS                                                     #                                                                                                       
#                                                                                                                      #
########################################################################################################################
def AUTH_USER(data, add, users, online_users, client_udp_socket):
    '''
    User authentication.
    '''
    global PORT
    response = {
        'type': '',
        'status': 'OK',
    }
    username = data['username']

    # if the username is in online_users, then the user is already logged in 
    if username in online_users:
        response['type'] = 'ONLINE'
        response['status'] = 'ERROR'
        print('{} has already logged in'.format(username))
        return users, online_users
    elif username in users:
        # if the username is in users list then the user is an old user
        response['type'] = 'OLD'
        response['status'] = 'PWDNEED'
    elif username not in users:
        # if the username is not in users then create a new user
        response['type'] = 'NEW'
        response['status'] = 'PWDNEED'
    udp_send_response(client_udp_socket, response, add)

    data, add = udp_receive_data(client_udp_socket)
    password = data['password']

    print("Client authenticating")

    # for the old user
    if username in users:
        if password == users[username]:
            response['type'] = 'OLD_SUC'
            response['status'] = 'OK'
            print('{} successful login'.format(username))
            online_users.append(username)
        else:
        # if the password is incorrect, then the user is not logged in
            response['type'] = 'PWD'
            response['status'] = 'FAIL'
            print('Incorrect password')
    # for the new user
    else:
        response['type'] = 'NEW_SUC'
        response['status'] = 'OK'
        print('Welcome, {}'.format(username))
        
        users[username] = password # update the users list
        online_users.append(username)

        # write the new user to credentials.txt
        with open('credentials.txt', 'a+') as f:
            f.write('\n{} {}'.format(username, password))
    
    udp_send_response(client_udp_socket, response, add)
    return users, online_users

def CREATE_THREAD(data, add, threads, client_udp_socket):
    '''
    Create a new thread.
    '''
    global PORT
    response = {
        'status': 'OK'
    }
    thread_title, thread_creator = data['thread_title'], data['username']

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
            f.write('{}\n'.format(thread_creator)) # write the thread creator to the thread
    
    udp_send_response(client_udp_socket, response, add)
    return threads
        
def LIST_THREADS(threads, add, client_udp_socket):
    '''
    List all the threads.
    '''
    global PORT
    response = {
        'status': 'OK',
    }
    
    # if there are no threads to list
    if len(threads) == 0:
        response['status'] = 'FAIL'
    else:
        # if there are threads, then list them
        response['status'] = 'OK'
        response['threads'] = threads
    
    udp_send_response(client_udp_socket, response, add)

def POST_MESSAGE(data, add, threads, client_udp_socket):
    '''
    Post a message to a thread.
    '''
    global PORT
    response = {
        'status': 'OK',
    }
    thread_title, thread_creator, msg_content = data['thread_title'], data['username'], data['message']

    # if the thread title is not in the threads list, then the thread does not exist
    if thread_title not in threads:
        response['status'] = 'FAIL'
        print('Incorrect thread specified')
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

    udp_send_response(client_udp_socket, response, add)
    return threads
        
def DELETE_MESSAGE(data, add, threads, client_udp_socket):
    '''
    Delete a message from a thread.
    '''
    global PORT
    response = {
        'status': 'OK',
    }
    thread_title, thread_creator, msg_index = data['thread_title'], data['username'], data['message_id']

    # if the thread title is not in the threads list
    if thread_title not in threads:
        response['status'] = 'NO_THREAD'
        print('Thread {} does not exist'.format(thread_title))
        udp_send_response(client_udp_socket, response, add)
    
    else:
        # if the msg index is out of range
        if int(msg_index) <= 0:
            response['status'] = 'NO_MSG'
            print('Index of message: {} is out of range'.format(msg_index))
            udp_send_response(client_udp_socket, response, add)

        # find the line that contains the message index and corresponding line number
        line_to_remove = ''
        line_num = 0
        with open(thread_title, 'r') as f:
            lines = f.readlines()
            for line in lines:
                if msg_index == line.split()[0]:
                    line_to_remove = line
                    line_num = lines.index(line)
                    break

        # if thread is empty, no msg in the thread
        if line_to_remove == '':
            response['status'] = 'NO_MSG'
            print('The message does not exist') 
        # if the user is not the creator of the thread
        elif thread_creator != lines[line_num].split(' ')[1][:-1]:
            response['status'] = 'FAIL'
            print('Message cannot be deleted')
        else:
            # if the user is the creator of the thread, then delete the message
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
    '''
    Return the messages in the thread.
    '''
    global PORT
    response = {
        'status': 'OK',
    }
    thread_title = data['thread_title']

    # if the thread title is not in the threads list, then the thread does not exist
    if thread_title not in threads:
        response['status'] = 'FAIL'
        print('Thread {} does not exist'.format(thread_title))
    else:
        # if the thread title exists, then get the messages from the thread
        response['messages'] = []
        with open(thread_title, 'r') as f:
            lines = f.readlines()
        response['messages'] = lines[1:]
    
        # if the thread is empty,
        if len(response['messages']) == 0:
            response['status'] = 'NO_MSG'
            print('Thread {} read'.format(thread_title))
        else:
            response['status'] = 'OK'
            print('Thread {} read'.format(thread_title))

    udp_send_response(client_udp_socket, response, add)

def EDIT_MESSAGE(data, add, threads, client_udp_socket):
    '''
    Edit a message in a thread.
    '''
    global PORT
    response = {
        'status': 'OK',
    }
    thread_title, thread_creator, msg_index, msg_content = data['thread_title'], data['username'], data['message_id'], data['message']

    # if the thread title is not in the threads list
    if thread_title not in threads:
        response['status'] = 'NO_THREAD'
        print('Thread {} does not exist'.format(thread_title))
        udp_send_response(client_udp_socket, response, add)
    else:
    # if thread exists
        # if the msg index is out of range
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

        # if msg is not in the thread
        if line_to_edit == '':
            response['status'] = 'NO_MSG'
            print('Message does not exist'.format(msg_index))
        # if the user is not the creator of the thread
        elif thread_creator != lines[line_num].split(' ')[1][:-1]:
            response['status'] = 'FAIL'
            print('Message cannot be edited') 
        else:
        # if the user is the creator of the thread, then edit the message
            response['status'] = 'OK'
            print('Message has been edited'.format(msg_index))

            # rewrite the message
            lines[line_num] = '{} {}: {}\n'.format(msg_index, thread_creator, msg_content)
            
            # add the messages to the thread
            with open(thread_title, 'w+') as f:
                f.writelines(lines)
        
        udp_send_response(client_udp_socket, response, add)
    return threads

def UPLOAD_FILE(data, add, files, threads, client_udp_socket):
    '''
    Upload a file to the thread.
    '''
    global PORT
    response = {
        'status': 'OK',
    }
    thread_title, thread_creator, file_name, file_size = data['thread_title'], data['username'], data['file_name'], data['file_size']
    
    # if the thread title is not in the threads list
    if thread_title not in threads:
        response['status'] = 'FAIL'
        print('Thread {} does not exist'.format(thread_title))
        udp_send_response(client_udp_socket, response, add)
    else:
    # if the thread title is in the threads list, then upload the file
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

        # if the file size is not the same
        if int(file_size) != os.path.getsize('{}-{}'.format(thread_title, file_name)):
            response['status'] = 'FAIL'
            udp_send_response(client_udp_socket, response, add)
        else:
            # if the file size is the same, then add the file to the thread
            response['status'] = 'OK'
            with open(thread_title, 'a') as f:
                f.write('{} uploaded {}\n'.format(thread_creator, file_name))
            print('{} uploaded file {} to {} thread'.format(thread_creator, file_name, thread_title))
            files.append('{}-{}'.format(thread_title, file_name)) # add the file to the files list
            udp_send_response(client_udp_socket, response, add)

    return files

def DOWNLOAD_FILE(data, add, threads, files, client_udp_socket):
    '''
    Download a file from the thread.
    '''
    response = {
        'status': 'OK',
    }
    thread_title, file_name = data['thread_title'], data['file_name']

    # if the thread title is not in the threads list
    if thread_title not in threads:
        response['status'] = 'FAIL'
        print('Thread {} does not exist'.format(thread_title))
        udp_send_response(client_udp_socket, response, add)
    else:
        # if the file is not in the files list
        if '{}-{}'.format(thread_title, file_name) not in files:
            response['status'] = 'FILE_NOT_FOUND'
            print('{} does not exist in Thread {}'.format(file_name, thread_title))
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
                print('{} downloaded from Thread {}'.format(file_name, thread_title))
            elif data['status'] == 'FAIL':
                print('{} failed to download file {} from {} thread'.format(data['username'], file_name, thread_title))

def REMOVE_THREAD(data, add, threads, client_udp_socket):
    '''
    Remove a thread.
    '''
    response = {
        'status': 'OK',
    }
    thread_title, thread_creator = data['thread_title'], data['username']

    # if the thread title is not in the threads list
    if thread_title not in threads:
        response['status'] = 'NO_THREAD'
        print('Thread {} does not exist'.format(thread_title))
        udp_send_response(client_udp_socket, response, add)
    else:
        with open(thread_title, 'r') as f:
            lines = f.readlines()
    
        # if the user is not the creator of the thread
        if thread_creator != lines[0].split(' ')[0].rstrip():
            response['status'] = 'FAIL'
            print('Thread {} cannot be removed'.format(thread_title))     
        else:
            # if the user is the creator of the thread, then remove the thread
            response['status'] = 'OK'
            print('Thread {} removed'.format(thread_title))
            os.remove(thread_title)
            threads.remove(thread_title)

        udp_send_response(client_udp_socket, response, add)
    return threads

def EXIT_USER(data, add, online_users, client_udp_socket):
    '''
    Exit the user.
    '''
    response = {
        'status': 'OK',
    }
    user_name = data['username']

    # if the user is not in the online users list
    if user_name not in online_users:
        response['status'] = 'FAIL'
        print('User {} is not online'.format(user_name))
    else:
        response['status'] = 'OK'
        print('{} exited'.format(user_name))
        online_users.remove(user_name)

    print("Waiting for clients")
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
    server_startup(PORT)