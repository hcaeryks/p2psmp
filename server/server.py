import socket
import sys
import threading

# tamanho do header que contém o tamanho da mensagem
HEADERSIZE = 10

class Socket():
    userCount = 0
    # associa um número a cada usuário
    clientIDs = {}
    # [(conexão, (ip,porta)), lista de músicas, ativo]
    clients = []

    def __init__(self, pair):
        self.pair = pair
        self.sckt = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sckt.bind(self.pair)
        self.sckt.listen()
        threading.Thread(target=self.accept).start()

    # retorna lista de músicas apenas dos usuários ativos
    def getSongList(self):
        songList = []
        for x in range(len(self.clients)):
            for y in range(len(self.clients[x][1])):
                if(self.clients[x][2] and self.clients[x][1] != []):
                    songList.append(self.clients[x][1][y])
        return songList
    
    # retorna lista de músicas de um usuário específico
    def getUserSongList(self, user):
        return self.clients[self.clientIDs.get(user)][1]

    # encapsula o payload
    def getPDU(self, payload):
        return bytes(f"{len(payload):<{HEADERSIZE}}" + payload, 'utf-8')

    # aceita conexões novas a todo momento
    def accept(self):
        while True:
            connected = False
            client, address = self.sckt.accept()
            # checa se o cliente já existe e está ativo
            for clientI in self.clients:
                if clientI[0][1] == address and clientI[2]:
                    connected = True
                    client.send(self.getPDU('close'))
                    client.close()
            if not connected:
                self.clients.append([(client, address), [], True, 0])
                self.clientIDs[address] = self.userCount
                self.userCount += 1
                client.send(self.getPDU(f"Connected to the server."))
                client.send(self.getPDU(f"Successfully registered."))
                threading.Thread(target=self.recvfrom, args=(client, address,)).start()
                print(f">> {address}")

    # recebe mensagens novas de uma conexão específica
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
                    songlist = full_msg[HEADERSIZE:][7:][:msglen-7].split(';;;')
                    self.clients[self.clientIDs.get(address)][1] = songlist
                elif full_msg[HEADERSIZE:][:4] == 'list':
                    ip, port = full_msg[HEADERSIZE:][5:][:msglen-5].split(':')
                    user = (ip, int(port))
                    connection.send(self.getPDU('list ' + ';;;'.join(self.getUserSongList(user))))
                elif full_msg[HEADERSIZE:][:4] == 'user':
                    clientList = []
                    for client in self.clients:
                        if client[2] and client[0][1] != address:
                            clientList.append(str(client[0][1][0])+':'+str(client[0][1][1])+':'+str(client[3]))
                    connection.send(self.getPDU('user ' + ';;;'.join(clientList)))
                elif full_msg[HEADERSIZE:][:4] == 'port':
                    port = full_msg[HEADERSIZE:][5:][:msglen-5]
                    self.clients[self.clientIDs.get(address)][3] = port
                #print(full_msg[HEADERSIZE:msglen + HEADERSIZE])
                full_msg = full_msg[HEADERSIZE + msglen:]
                if len(full_msg) > 10:
                    msglen = int(full_msg[:HEADERSIZE])

    # envia mensagem para a conexão especificada
    def send(self, connection, pdu):
        connection.send(pdu)

# parâmetro 1 = ip, 2 = porta (que o servidor vai rodar)
sckt = Socket((sys.argv[1], int(sys.argv[2])))