import hashlib
import random
import time
import math
import socket
import string
HEADERSIZE = 10
from tcpServer import *
# Node class
class Node:

    # Function to initialise the node object
    def __init__(self, data):
        self.data = data  # Assign data
        self.next = None  # Initialize next as null

# Linked List class contains a Node object
class LinkedList:
    # Function to initialize head
    def __init__(self):
        self.head = None
    def printList(self):
        counter = 1
        temp = self.head
        while (temp):
            print("Block {}:".format(counter))
            x = temp.data.split("***")
            print("Transactions: {}".format(x[0]))
            print("Pointer and Hash: ({})".format(x[1]))
            print("Nonce: {}".format(x[2]))
            temp = temp.next
            counter +=1
    def getSize(self):
        cursor = self.head
        count = 0
        while cursor:
            cursor = cursor.next
            count += 1
        return count

#Finds highest promised ballot
def extractVal(promises):
    highestBallot = 0
    fin = None
    for promise in promises:
        x = promise.split(',')
        if x[5] != "None":
            if(int(x[3]) > highestBallot):
                highestBallot = int(x[3])
                fin = promise
    if fin == None:
        return None
    else:
        return fin

#Adds next Block
def addNewBlock(ll, block, balance, portNum, idToPort):
    #Update Balance
    transactions = block.split('?')
    transactions = transactions[0].split('{')
    transactions = transactions[1:]
    for transaction in transactions:
        transaction = transaction.replace('}','')
        component = transaction.split('/')
        if int(idToPort[component[0]]) == int(portNum):
            balance[0] -= int(component[2])
        if int(idToPort[component[1]]) == int(portNum):
            balance[0] += int(component[2])

    block = block.split('?')
    block = block[0] + block[1]
    #Update List
    if ll.head == None:
        ll.head = Node(block)
    elif ll.head.next == None:
        ll.head.next = Node(block)
    else:
        cursor = ll.head
        while(cursor.next != None):
            cursor = cursor.next
        cursor.next = Node(block)

def calcHash_Nonce(llist, val):
    sha = ""
    pointer = ""
    #Calculate Hash of previous block
    if llist.head == None:
        sha = hashlib.sha256("".encode()).hexdigest()
        pointer = str(None)
    elif llist.head.next == None:
        sha = hashlib.sha256(llist.head.data.encode()).hexdigest()
        pointer = str(llist.head)
    else:
        cursor = llist.head
        while(cursor.next!=None):
            cursor = cursor.next
        pointer = str(cursor)
        sha = hashlib.sha256(cursor.data.encode()).hexdigest()
    #Calculate Nonce
    print("Calculating Nonce")
    counter = 1
    calculating = True
    approvedValues = set(['0','1','2','3','4'])
    while calculating:
        nonce = ''.join(random.choices(string.ascii_letters + string.digits, k=5))
        temp = nonce + val + sha
        check = hashlib.sha256(temp.encode()).hexdigest()
        if check[-1] in approvedValues:
            print("Found Nonce in {} attempts.".format(counter))
            print("SHA256({}||{}||{}) == {}".format(val, nonce, sha, check))
            calculating = False
        else:
            counter += 1
    return "?***" + pointer + "/" + str(sha) + "***" + nonce


def sendMessage(msg, portNum,fails, sendSockets, sleep=True):
    try:
        if not fails[portNum]:
            if sleep:
                time.sleep(2)
            sendSockets[portNum].send(bytes(msg, "utf-8"))
    except:
        print("No connection to {}!".format(portNum))


def processingThread(
    portNum, q, sendSockets,  idToPort, transactions, llist, balance, estimatedBalance, trans_condition, q_condition, printable):
    #Variable Declaring
    ballotNum = ballotId = acceptBallot = acceptId = 0
    acceptDepth = depth = llist.getSize()
    acceptVal = None
    lastValue = ""
    promisesReceived = 1
    promises = []
    acceptedReceived = 1
    val = ""
    majority = math.ceil(float(len(idToPort)) / 2.0)
    fails = {}
    for peer in sendSockets:
        fails[peer] = False
    while True:
        if q.empty():
            with q_condition:
                q_condition.wait()
        else:
            command = q.get()
            component = command.split(',')
            #Election command
            if component[0] == "election":
                #Reset Values
                val = ''
                promisesReceived = 1
                acceptedReceived = 1
                promises = []
                #Update ballotNum
                ballotNum +=1
                ballotId = portNum
                #Send Prepare Messages to all non-failed Channels
                msg = "prepare," + str(ballotNum) + ',' + str(portNum) + ',' + str(depth)
                msg = f'{len(msg):<{HEADERSIZE}}' + msg
                for peer in sendSockets:
                    sendMessage(msg, peer, fails, sendSockets)
            #Prepare Response
            elif component[0] == "prepare":
                #Promise to not accept any smaller ballots
                if (int(component[1]) > ballotNum or (int(component[1]) == ballotNum and int(component[2]) > ballotId)) and int(component[3]) >= depth:
                    ballotNum = int(component[1])
                    ballotId = int(component[2])
                    depth = int(component[3])
                    #Send message back to proposer
                    msg = "promise," + str(ballotNum) + "," + str(ballotId) + ',' + str(acceptBallot) + ',' + str(acceptId) + ',' + str(acceptVal) + ',' + str(depth)
                    msg = f'{len(msg):<{HEADERSIZE}}' + msg
                    sendMessage(msg, ballotId, fails, sendSockets)

                else:
                    msg = "nack"
                    msg = f'{len(msg):<{HEADERSIZE}}' + msg
                    sendMessage(msg, int(component[2]), fails, sendSockets)

            #Promise Response
            elif component[0] == "promise":
                promisesReceived += 1
                promises.append(command)
                #Once Proposer recieves promises back from a majority
                if promisesReceived == majority:
                    print("\nPausing Transactions")
                    while not transactions.empty():
                        val += '{' + str(transactions.get()) + '}'

                    hashANDnonce = calcHash_Nonce(llist, val)
                    val+= hashANDnonce

                    #Find the highest ranking promise
                    myVal = extractVal(promises)
                    #If highest ranking promise is null
                    if myVal == None:
                        x = promises[0]
                        x = x.split(',')
                        msg = "accept," + str(x[1]) + "," + str(portNum) + ',' + val + ',' + str(depth)
                    #Otherwise
                    else:
                        myVal = myVal.split(",")
                        msg = "accept," + str(ballotNum) + "," + str(ballotId) + "," + str(myVal[5]) + "," + str(myVal[6])
                    #Send accept message to all nodes
                    msg = f'{len(msg):<{HEADERSIZE}}' + msg
                    for peer in sendSockets:
                        sendMessage(msg, peer, fails, sendSockets)
            #Accept response
            elif component[0] == "accept":
                if (int(component[1]) > ballotNum  or (int(component[1]) == ballotNum and int(component[2]) >= ballotId)) and int(component[4]) >= depth:
                    acceptBallot = int(component[1])
                    acceptId = int(component[2])
                    acceptVal = component[3]
                    acceptDepth = depth
                    msg = "accepted," + str(acceptBallot) + "," + str(acceptId) + "," + acceptVal
                    msg = f'{len(msg):<{HEADERSIZE}}' + msg
                    #Weird Edge Case
                    if int(acceptId) != portNum:
                        sendMessage(msg, acceptId, fails, sendSockets)
            #Accepted response
            elif component[0] == "accepted":
                acceptedReceived += 1
                if(acceptedReceived == majority):
                    acceptBallot = int(component[1])
                    acceptId = int(component[2])
                    acceptVal = lastValue = component[3]
                    printTrans = acceptVal.split("?")[0]
                    print("Consensus Reached!")
                    print("Deciding Value: {}".format(printTrans))
                    msg = "decide," + str(acceptBallot) + "," + str(acceptId) + "," + acceptVal
                    msg = f'{len(msg):<{HEADERSIZE}}' + msg
                    #Update propser's balance here
                    addNewBlock(llist, acceptVal, balance, portNum, idToPort)
                    depth += 1
                    acceptDepth = depth
                    estimatedBalance[0] = balance[0]

                    #Check to see if you inherited the val
                    if acceptVal != val:
                        #If so Put your transactions back onto the queue
                        temp = val.split("?")
                        temp = temp[0]
                        temp = temp.split("{")
                        temp = temp[1:]
                        for t in temp:
                            t = t.replace('}','')
                            transactions.put(t)
                        if not transactions.empty():
                            with trans_condition:
                                trans_condition.notify()
                    else:
                        printable.clear()
                        print("Resuming Transactions!")


                    #Reset Paxos varaibles
                    ballotNum = ballotId = acceptBallot = acceptId = 0
                    acceptVal = None
                    val = ""
                    for peer in sendSockets:
                        sendMessage(msg, peer, fails, sendSockets)
            #Decide Reaction
            elif component[0] == "decide":
                acceptVal = component[3]
                if acceptVal != lastValue:
                    lastValue = acceptVal
                    printTrans = acceptVal.split("?")[0]
                    print("Deciding Value: {}".format(printTrans))
                    #Send "decideM" message to all nodes on the network
                    #Make Sure everyone has new value
                    msg = command
                    msg = f'{len(msg):<{HEADERSIZE}}' + msg
                    for peer in sendSockets:
                        sendMessage(msg, peer, fails, sendSockets)

                    addNewBlock(llist, acceptVal, balance, portNum, idToPort)
                    depth += 1
                    acceptDepth = depth
                    estimatedBalance[0] = balance[0]
                    #Reset Paxos Varaibles
                    ballotNum = ballotId = acceptBallot = acceptId = 0
                    acceptVal = None

                    #Upload left over Transactions
                    if val != "":
                        temp = val.split("?")
                        temp = temp[0]
                        temp = temp.split("{")
                        temp = temp[1:]
                        for t in temp:
                            t = t.replace('}','')
                            transactions.put(t)
                        print("Resuming Transactions!")
                    val = ""
                    #Notify election of left-over transactions
                    if not transactions.empty():
                        with trans_condition:
                            trans_condition.notify()

            #Nack Reaction
            elif component[0] == "nack":
                acceptedReceived = -5
                promisesReceived = -5

            #Failure Between Link
            elif component[0] == "failure":
                if len(component) < 3:
                    fails[int(idToPort[component[1]])] = True
                    msg = "failure," + str(portNum) + ",r"
                    msg = f'{len(msg):<{HEADERSIZE}}' + msg
                    sendSockets[int(idToPort[component[1]])].send(bytes(msg, "utf-8"))
                else:
                    fails[int(component[1])] = True
                print(fails)
            #Fixed Link
            elif component[0] == "fixed":
                if len(component) < 3:
                    fails[int(idToPort[component[1]])] = False
                    #Send Block Chain
                    blockChain = ""
                    cursor = llist.head
                    while(cursor != None):
                        blockChain += cursor.data + "|||"
                        cursor = cursor.next

                    msg = "fixed," + str(portNum) + "," + str(depth) + "," + blockChain + "," + str(ballotNum)
                    msg = f'{len(msg):<{HEADERSIZE}}' + msg
                    sendSockets[int(idToPort[component[1]])].send(bytes(msg, "utf-8"))
                else:
                    flag = True
                    for key in fails:
                        flag = flag and fails[key]

                    if int(component[4]) > ballotNum:
                        ballotNum = int(component[4])
                    #If Incoming Depth is greater
                    if int(component[2]) > depth and flag:
                        updateBlocks = component[3].split('|||')
                        updateBlocks = updateBlocks[:-1]
                        updateCounter = depth
                        while(updateCounter < int(component[2])):
                            temp = updateBlocks[updateCounter]
                            index = temp.find('***')
                            temp = temp[:index] + '?' + temp[index:]
                            addNewBlock(llist, temp, balance, portNum, idToPort)
                            updateCounter +=1
                        estimatedBalance[0] = balance[0]
                        depth = acceptDepth = int(component[2])
                    elif int(component[2]) < depth:
                        blockChain = ""
                        cursor = llist.head
                        while(cursor != None):
                            blockChain += cursor.data + "|||"
                            cursor = cursor.next
                        msg = "update," + str(depth) + "," + blockChain + "," + str(ballotNum)
                        msg = f'{len(msg):<{HEADERSIZE}}' + msg
                        sendMessage(msg, int(component[1]), fails, sendSockets, False)
                    fails[int(component[1])] = False
                print(fails)
            #Restart command, so peers rejoin your server
            elif component[0] == "join":
                if len(component) == 1:
                    msg = "join," + str(portNum)
                    msg = f'{len(msg):<{HEADERSIZE}}' + msg
                    for peer in sendSockets:
                        sendMessage(msg, peer, fails, sendSockets, False)
                else:
                    sendSockets[int(component[1])] = joinPeer(int(component[1]))
                    blockChain = ""
                    cursor = llist.head
                    while(cursor != None):
                        blockChain += cursor.data + "|||"
                        cursor = cursor.next
                    msg = "update," + str(depth) + "," + blockChain + "," + str(ballotNum)
                    msg = f'{len(msg):<{HEADERSIZE}}' + msg
                    sendMessage(msg, int(component[1]), fails, sendSockets, False)
            #Update Message
            elif component[0] == "update":
                if int(component[3]) > ballotNum:
                    ballotNum = int(component[3])
                if depth < int(component[1]):
                    updateBlocks = component[2].split('|||')
                    updateBlocks = updateBlocks[:-1]
                    updateCounter = depth
                    while(updateCounter < int(component[1])):
                        temp = updateBlocks[updateCounter]
                        index = temp.find('***')
                        temp = temp[:index] + '?' + temp[index:]
                        addNewBlock(llist, temp, balance, portNum, idToPort)
                        updateCounter +=1
                    estimatedBalance[0] = balance[0]
                    depth = acceptDepth = int(component[1])
            else:
                pass

def transactionTimeOut(transactions, trans_condition, q, q_condition):
    while True:
        #Block Until Transaction is in the queue
        with trans_condition:
            trans_condition.wait()
        #Start Timer
        randomTime = random.randint(6, 12)
        print('\nTime out started! {} seconds unitl election.'.format(randomTime))
        time.sleep(randomTime)
        if q.empty():
            q.put('election')
            with q_condition:
                q_condition.notify()
        else:
            q.put('election')
    trans_condition.release()

def saveValues(fileName, printable, llist, balance):
    saveFile = open(fileName, 'w')
    saveFile.write("Transaction:")
    for x in printable:
        saveFile.write(x + ",")
    saveFile.write("\n")
    blockChain = ""
    cursor = llist.head
    while(cursor != None):
        blockChain += cursor.data + "|||"
        cursor = cursor.next
    saveFile.write(blockChain + "\n")
    saveFile.write('Balance:'+str(balance[0]))
    saveFile.close()
