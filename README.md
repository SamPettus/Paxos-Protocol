# Paxos-Protocol
Run 5 node.py with sys arugments {1,2,3,4,5} respectively. Creates a peer to peer network that allows for transcations across a distributed system.
The protocol uses paxos to elect a transaction blocks which is then added to a blockchain that is then broadcasted to all peers in the network.
Program is fault tolerant and saves blockchain and transaction information in a save file denoted by "proccess id"crash.txt
May also partition the network by failing/fixing individual connections.
