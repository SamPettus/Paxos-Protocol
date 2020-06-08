from queue import Queue
import threading
import sys
from tcpServer import *
from processing import *
import os.path

def main():
    llist = LinkedList()
    balance = [100]
    estimatedBalance = [100]
    #Process id
    processID = int(sys.argv[1])
    #Reads config.txt to pair process Id and port Num
    portNum, nodesInNetwork = parseConfigFile(processID)

    #Transaction Queue
    transactions = Queue()
    #Printable Transaction Queue()
    printTrans = []
    #Shared Queue
    q = Queue()
    #Queue Conditition
    q_condition = threading.Condition()
    #Sets recieve Server
    recieve = threading.Thread(target=initializeSocket, args=(portNum, q, q_condition))
    recieve.daemon = True
    recieve.start()

    #Wait for other servers to initialize
    time.sleep(4)

    sendSockets = {}
    for x in nodesInNetwork:
        s = joinPeer(int(x[1]))
        sendSockets[int(x[1])] = s

    #Add yourself to the Dict
    idToPort = {}
    idToPort[str(processID)] = str(portNum)
    for x in nodesInNetwork:
        idToPort[x[0]] = x[1]

    #Check to see if you have previously failed
    fileName = str(processID) + "crash.txt"
    if os.path.exists(fileName):
        q.put("join")
        f = open(fileName, 'r')
        temp_1 = []
        temp_2 = []
        #Get Saved Transactions
        temp_1 = f.readline().split(':')
        if len(temp_1) > 1:
            temp_1 = temp_1[1].split(',')
            temp_1 = temp_1[:-1]
        #Get Saved BlockChain
        temp_2 = f.readline().split('|||')
        if len(temp_2) > 1:
            temp_2 = temp_2[:-1]
        #Get Saved Balnace
        temp_3 = f.readline().split(':')
        balance[0] = int(temp_3[1])
        estimatedBalance[0] = int(temp_3[1])

        f.close()
        #Update Transaction Queue and Printable Version
        printTrans = temp_1
        for x in temp_1:
            transactions.put(x)

        if temp_2[0] != '\n':
            llist.head = Node(temp_2[0])
            cursor = llist.head
            if len(temp_2) > 1:
                for x in temp_2[1:]:
                    cursor.next = Node(x)
                    cursor = cursor.next


    #Transaction Conditition
    trans_condition = threading.Condition()
    #Initiate Processing Thread
    processing= threading.Thread(
        target=processingThread, args=(
            portNum, q, sendSockets, idToPort, transactions, llist, balance, estimatedBalance, trans_condition, q_condition, printTrans))
    processing.daemon = True
    processing.start()

    #Initiate Transactions thread
    electionBlock = threading.Thread(
        target=transactionTimeOut, args = (transactions, trans_condition, q, q_condition))
    electionBlock.daemon = True
    electionBlock.start()

    if not transactions.empty():
        with trans_condition:
            trans_condition.notify()
    run = True
    while run:
        x = int(input('1 moneyTransfer, 2 failLink, 3 fixLink, 4 failProcess, 5 printBlockChain, 6 printBalance, 7 print pending Transactions: '))
        if x == 1:
            credit_node, amount = input('Enter destination and amount: ').split()
            #Check to see if amount is greater that percieved balance
            if int(amount) > estimatedBalance[0]:
                print("Transaction Failed. Amount is greated than estimated balance!")
            else:
                estimatedBalance[0] -= int(amount)
                transaction = str(processID) + '/' + str(credit_node) + '/' + str(amount)
                #Printable Version
                printTrans.append(transaction)
                #Add transaction to transactions Queue
                if transactions.empty():
                    transactions.put(transaction)
                    with trans_condition:
                        trans_condition.notify()
                else:
                    transactions.put(transaction)
        if x==2:
            failedNode = input('Enter failed Link: ')
            command = 'failure,' + failedNode
            if q.empty():
                q.put(command)
                with q_condition:
                    q_condition.notify()
            else:
                q.put(command)
        if x == 3:
            fixedNode = input('Enter fixed Link: ')
            command = 'fixed,' + fixedNode
            if q.empty():
                q.put(command)
                with q_condition:
                    q_condition.notify()
            else:
                q.put(command)
        if x==4:
            print("Crashing!")
            saveValues(fileName, printTrans, llist, balance)
            run = False
        if x==5:
            llist.printList()
        if x==6:
            print('Balance: $' + str(balance[0]))
        if x==7:
            #Print printTrans
            print('Pending Transactions: {}'.format(printTrans))




main()
