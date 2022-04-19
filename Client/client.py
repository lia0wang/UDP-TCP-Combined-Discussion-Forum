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

from random import random
import sys
import select
import time
import os
import json
from socket import *
from _thread import *
from urllib import response

########################################################################################################################
#                                                                                                                      #
#                                                   GLOBAL VARIABLES                                                   #                                                                                                       
#                                                                                                                      #
########################################################################################################################
PORT = None # the port number of the server
CLIENT_PORT = 9999
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

def client_startup(port):
    '''
    This function is used to start the client.
    '''
    # create a tcp socket for UPD and DWN to make the transfer of file reliable
    tcp_socket = socket(AF_INET, SOCK_STREAM)
    tcp_socket.connect(('localhost', port))
    tcp_socket.settimeout(5)

    # create a udp socket for the client to send the request to the server
    udp_socket = socket(AF_INET, SOCK_DGRAM)

    AUTH(udp_socket)

    print('Connection closed')
    tcp_socket.close()
    udp_socket.close()

########################################################################################################################
#                                                                                                                      #
#                                                 COMMANDS CLASS                                                       #                                                                                                                                                           
#                                                                                                                      #
########################################################################################################################
def AUTH(udp_socket):
    '''
    This function is used to authenticate the user.
    '''
    username = input('Enter username: ')
    username = username.strip()
    password = ''

    request = {'command': 'AUTH', 'username': username}
    udp_send_request(request, udp_socket)
    
    response = udp_receive_response(udp_socket)
    print('here')

    # if the user is already logged in
    if response['type'] == 'OLD':
        print('{} has already logged in'.format(username))
        AUTH(udp_socket)
    # if the user is not online
    elif response['type'] == 'NEW':
        password = input('New user, enter password: ')
    else:
        password = input('Enter password: ')
    
    # send the password to the server
    request = {'command': 'AUTH', 'username': username, 'password': password}
    response = udp_send_request(request, udp_socket)

    # if response is correct
    if response['status'] == 'OK':
        print('Welcome to the forum')
        global user_info
        user_info['username'] = username
        user_info['password'] = password
    
    else:
        if response['status'] == 'FAIL':
            print('Invalid password')
            AUTH(udp_socket)

def udp_send_request(request, udp_socket):
    '''
    This function is used to send the request to the server.
    '''
    global PORT
    request = bytes(json.dumps(request), encoding='utf-8')
    udp_socket.sendto(request, ('localhost', PORT))
    print('send request {} to port {}'.format(request, PORT))

def udp_receive_response(udp_socket):
    '''
    This function is used to receive the response from the server.
    '''
    global PORT
    response = udp_socket.recvfrom(1024)[0]
    request = request.decode('utf-8')
    request = json.loads(request)
    print('receive response {} from port {}'.format(response, PORT))
    return response

def tcp_send_request(request, tcp_socket):
    '''
    This function is used to send the request to the server.
    '''
    global PORT
    request = bytes(json.dumps(request), 'utf-8')
    tcp_socket.send(request)


########################################################################################################################
#                                                                                                                      #
#                                                  MAIN FUNCTION                                                       #                                                                                                                                                           
#                                                                                                                      #
########################################################################################################################
if __name__ == '__main__':
    PORT = port_checker()
    client_startup(PORT)