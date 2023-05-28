import socket
import sys
import threading

HEADERSIZE = 10

class Socket():
    userCount = 0
    clientIDs = {}
    clients = []

    def __init__(self, pair):
        self.pair = pair
        self.sckt = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sckt.bind(self.pair)
        self.sckt.listen()
        threading.Thread(target=self.accept).start()

    def getSongList(self):
        songList = []
        for x in range(len(self.clients)):
            for y in range(len(self.clients[x][1])):
                if self.clients[x][2]:
                    songList.append(str(x) + ' ' + self.clients[x][1][y])
        return songList

    def getPDU(self, payload):
        return bytes(f"{len(payload):<{HEADERSIZE}}" + payload, 'utf-8')

    def accept(self):
        while True:
            client, address = self.sckt.accept()
            if(address in self.clientIDs):
                self.clients[self.clientIDs.get(address)][2] = True
                client.send(self.getPDU(f"Connected to the server."))
            else:
                self.clients.append([(client, address), [], True])
                self.clientIDs[address] = self.userCount
                self.userCount += 1
                client.send(self.getPDU(f"Connected to the server."))
                client.send(self.getPDU(f"Successfully registered."))
            threading.Thread(target=self.recvfrom, args=(client, address,)).start()
            print(f">> {address}")

    def recvfrom(self, connection, address):
        full_msg = ''
        new_msg = True
        while True:
            msg = connection.recv(1024)
            if new_msg:
                msglen = int(msg[:HEADERSIZE])
                new_msg = False
            full_msg += msg.decode("utf-8")
            while len(full_msg[HEADERSIZE:msglen + HEADERSIZE]) == msglen:
                new_msg = True
                if full_msg[HEADERSIZE:msglen + HEADERSIZE] == 'close':
                    connection.send(self.getPDU('close'))
                    connection.close()
                    self.clients[self.clientIDs.get(address)][2] = False
                    print(f"<< {address}")
                    break
                elif full_msg[HEADERSIZE:][:6] == 'export':
                    songlist = full_msg[HEADERSIZE:][7:].split(';;;')
                    self.clients[self.clientIDs.get(address)][1] = songlist
                elif full_msg[HEADERSIZE:][:4] == 'list':
                    connection.send(self.getPDU('list ' + ';;;'.join(self.getSongList())))
                #print(full_msg[HEADERSIZE:msglen + HEADERSIZE])
                full_msg = full_msg[HEADERSIZE + msglen:]

    def send(self, connection, pdu):
        connection.send(pdu)

sckt = Socket((sys.argv[1], int(sys.argv[2])))