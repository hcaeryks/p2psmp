import threading, socket, sys, os
from PyQt5.QtCore import *
from PyQt5.QtGui import *
from PyQt5.QtWidgets import *

# tamanho do header que contém o tamanho da mensagem
HEADERSIZE = 10

# caminho para a pasta de músicas
MUSICFOLDER = "./music"

class Program():
    def __init__(self, pair):
        self.app = QApplication([])
        self.mainwindow = QMainWindow()
        self.mainwindow.setWindowTitle('p2psmp')
        self.mainwindow.resize(700, 400)

        self.pair = pair
        self.sckt = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sckt.connect(self.pair)
        self.error = False
        self.recv(True)
        threading.Thread(target=self.recv, args=(False,)).start()
        #threading.Thread(target=self.send).start()
        if not self.error:
            self.spawnInfoDialog("Connected to the server!")
        else:
            self.spawnInfoDialog("User already registered, exiting...")
            self.mainwindow.close()
        self.error = 'passed'

        self.outerLayout = QHBoxLayout()

        self.layout = QVBoxLayout()
        self.listView = QListView()
        self.userView = QListView()
        self.modelSong = QStandardItemModel()
        self.modelUser = QStandardItemModel()
        self.listView.setModel(self.modelSong)
        self.listView.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.listView.setObjectName("Song List")
        self.userView.setModel(self.modelUser)
        self.userView.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.userView.setObjectName("User List")
        self.userView.setMaximumHeight(75)

        self.rightLayout = QVBoxLayout()
        self.playButton = QPushButton('Play File', self.mainwindow)
        self.exposeButton = QPushButton('Expose Files', self.mainwindow)
        self.exposeButton.clicked.connect(self.exposeAllFiles)
        self.updateButton = QPushButton('Refresh', self.mainwindow)
        self.updateButton.clicked.connect(self.loadFileList)
        self.rightLayout.addWidget(self.playButton)
        self.rightLayout.addWidget(self.exposeButton)
        self.rightLayout.addWidget(self.updateButton)
        self.rightLayout.addSpacerItem(QSpacerItem(0, 0, QSizePolicy.Minimum, QSizePolicy.Expanding))
        
        self.layout.addWidget(self.userView)
        self.layout.addWidget(self.listView)
        self.outerLayout.addLayout(self.layout)
        self.outerLayout.addLayout(self.rightLayout)
        
        self.widget = QWidget()
        self.widget.setLayout(self.outerLayout)
        self.mainwindow.setCentralWidget(self.widget)
        self.mainwindow.show()

        self.app.aboutToQuit.connect(self.disconnect)
        self.app.exec()

    # envia ao servidor a própria lista de arquivos
    def exposeAllFiles(self):
        self.customSend(self.getPDU('export ' + ';;;'.join(self.getMySongs())))

    # pede ao servidor a lista de arquivos disponíveis
    def loadFileList(self):
        self.customSend(self.getPDU('list'))

    # anda pela pasta de músicas especificadas e retorna uma lista pro caminho de cada uma delas
    def getMySongs(self):
        filelist = []
        for root, dirs, files in os.walk(MUSICFOLDER):
            for file in files:
                if file.endswith('.mp3'):
                    filelist.append(os.path.join(root, file)[8:])
        return filelist

    # spawna um dialog
    def spawnInfoDialog(self, text):
        dlg = QMessageBox(self.mainwindow)
        dlg.setWindowTitle('p2psmp')
        dlg.setText(text)
        dlg.exec()

    # pede para desconectar do servidor
    def disconnect(self):
        self.customSend(self.getPDU('close'))

    # encapsula o payload
    def getPDU(self, data):
        return bytes(f"{len(data):<{HEADERSIZE}}" + data, 'utf-8')

    # recebe mensagens novas do servidor, pode ser executado constantemente ou apenas uma vez (once = True)
    def recv(self, once):
        full_msg = ''
        new_msg = True
        while True:
            msg = self.sckt.recv(1024)
            if new_msg:
                msglen = int(msg[:HEADERSIZE])
                new_msg = False
            full_msg += msg.decode("utf-8")
            while len(full_msg[HEADERSIZE:msglen + HEADERSIZE]) == msglen:
                new_msg = True
                if full_msg[HEADERSIZE:msglen + HEADERSIZE] == "close":
                    self.sckt.close()
                    if self.error == False:
                        print("User already registered!")
                    else:
                        print("Disconnected from the server!")
                    self.error = True
                    exit()
                elif full_msg[HEADERSIZE:][:4] == "list":
                    songList = full_msg[HEADERSIZE:][5:][:msglen-5].split(';;;')
                    self.modelSong.clear()
                    for song in songList:
                        self.modelSong.appendRow(QStandardItem(song))
                elif full_msg[HEADERSIZE:][:4] == "user":
                    userList = full_msg[HEADERSIZE:][5:][:msglen-5].split(';;;')
                    self.modelUser.clear()
                    for user in userList:
                        self.modelUser.appendRow(QStandardItem(user))
                else: 
                    print(full_msg[HEADERSIZE:msglen + HEADERSIZE])
                full_msg = full_msg[HEADERSIZE + msglen:]
                if len(full_msg) > 10:
                    msglen = int(full_msg[:HEADERSIZE])
            if once: 
                break
    
    # recebe input do usuário constantemente e envia para o servidor (não é usado com interface gráfica)
    def send(self):
        while True:
            data = input()
            filelist = []
            if data == 'close':
                self.sckt.send(self.getPDU(data))
                break
            elif data[:7] == 'export ':
                if data[7:] == '*':
                    filelist = self.getMySongs()
                    data = data.replace('*', ';;;'.join(filelist))
            if filelist != []:
                self.sckt.send(self.getPDU(data))

    # envia mensagens específicas com a pdu como parâmetro
    def customSend(self, pdu):
        self.sckt.send(pdu)

# parâmetro 1 = ip, 2 = porta (do servidor)
program = Program((sys.argv[1], int(sys.argv[2])))