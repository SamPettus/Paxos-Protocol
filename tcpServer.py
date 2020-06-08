import socket
from queue import Queue
import threading

HEADERSIZE = 10
#Read config file and return portNums
def parseConfigFile(processID):
    #Config file contains all processIDs with corresponding portNums
    f = open("config.txt","r")
    nodesInNetwork = []
    for x in f:
        s = x.split(':')
        if processID != int(s[0]):
            list = []
            list.append(s[0])
            list.append(s[1].rstrip("\n"))
            nodesInNetwork.append(list)
        else:
            portNum = int(s[1].rstrip("\n"))
    f.close()
    print("I am port {}!".format(portNum))
    return portNum, nodesInNetwork

#Initialize TCP server for personal Port Num
def initializeSocket(portNum, q, q_condition):
    process = socket.socket(socket.AF_INET, socket.SOCK_STREAM) #TCP socket
    process.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    process.bind((socket.gethostbyname('localhost'), portNum))
    process.listen(5)
    while True:
        #Establish connection with client
        clientsocket, address = process.accept()
        print("\nConnection from {} has been established!".format(address))
        #Creates a thread for each incoming channel
        listen1 = threading.Thread(target=listen, args=(clientsocket, q, q_condition))
        listen1.daemon = True
        listen1.start()
    process.close()

#Listen on Port
def listen(clientsocket, q, q_condition):
    run = True
    while run:
        try:
            #Recieve data in small chunks
            full_msg = ''
            new_msg = True
            while True: #Buffers data
                msg = clientsocket.recv(16) #Determines chunk size
                if new_msg:
                    msglen = int(msg[:HEADERSIZE])
                    new_msg = False

                full_msg += msg.decode("utf-8")

                if len(full_msg) - HEADERSIZE == msglen:
                    msg = full_msg[HEADERSIZE:]
                    if q.empty():
                        q.put(msg)
                        with q_condition:
                            q_condition.notify()
                    else:
                        q.put(msg)
                    new_msg = True
                    full_msg = ''
        except:
            run = False
        finally:
            print('Peer Process Crashed!')

def joinPeer(portNum):
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM) #TCP socket
    try:
        s.connect((socket.gethostbyname('localhost'), portNum))
        return s
    except:
        print("No server {}!".format(portNum))
        return None
