import threading, socket, sys, os
from PyQt5.QtCore import *
from PyQt5.QtGui import *
from PyQt5.QtWidgets import *

HEADERSIZE = 10
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
        threading.Thread(target=self.recv).start()
        #threading.Thread(target=self.send).start()
        # MORE BS
        self.spawnInfoDialog("Connected to the server!")

        # ui bullshit
        # ui bullshit
        # ui bullshit

        self.outerLayout = QHBoxLayout()

        self.layout = QHBoxLayout()
        self.listView = QListView()
        self.model = QStandardItemModel()
        self.listView.setModel(self.model)
        self.listView.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.listView.setObjectName("Song List")

        self.rightLayout = QVBoxLayout()
        self.playButton = QPushButton('Play File', self.mainwindow)
        self.exposeButton = QPushButton('Expose Files', self.mainwindow)
        self.exposeButton.clicked.connect(self.exposeAllFiles)
        self.updateButton = QPushButton('Refresh Files', self.mainwindow)
        self.updateButton.clicked.connect(self.loadFileList)
        self.rightLayout.addWidget(self.playButton)
        self.rightLayout.addWidget(self.exposeButton)
        self.rightLayout.addWidget(self.updateButton)
        self.rightLayout.addSpacerItem(QSpacerItem(0, 0, QSizePolicy.Minimum, QSizePolicy.Expanding))

        self.layout.addWidget(self.listView)
        self.outerLayout.addLayout(self.layout)
        self.outerLayout.addLayout(self.rightLayout)
        
        self.widget = QWidget()
        self.widget.setLayout(self.outerLayout)
        self.mainwindow.setCentralWidget(self.widget)
        self.mainwindow.show()

        self.app.aboutToQuit.connect(self.disconnect)
        self.app.exec()

    def exposeAllFiles(self):
        self.customSend(self.getPDU('export ' + ';;;'.join(self.getMySongs())))

    def loadFileList(self):
        self.customSend(self.getPDU('list'))

    def getMySongs(self):
        filelist = []
        for root, dirs, files in os.walk(MUSICFOLDER):
            for file in files:
                if file.endswith('.mp3'):
                    filelist.append(os.path.join(root, file)[8:])
        return filelist

    def spawnInfoDialog(self, text):
        dlg = QMessageBox(self.mainwindow)
        dlg.setWindowTitle('p2psmp')
        dlg.setText(text)
        dlg.exec()

    def disconnect(self):
        self.customSend(self.getPDU('close'))

    def getPDU(self, data):
        return bytes(f"{len(data):<{HEADERSIZE}}" + data, 'utf-8')

    def recv(self):
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
                    print("Disconnected from the server!")
                    exit()
                elif full_msg[HEADERSIZE:][:4] == "list":
                    songList = full_msg[HEADERSIZE:][5:].split(';;;')
                    self.model.clear()
                    for song in songList:
                        self.model.appendRow(QStandardItem(song))
                else: 
                    print(full_msg[HEADERSIZE:msglen + HEADERSIZE])
                full_msg = full_msg[HEADERSIZE + msglen:]

    def send(self):
        while True:
            data = input()
            if data == 'close':
                self.sckt.send(self.getPDU(data))
                break
            elif data[:7] == 'export ':
                filelist = []
                if data[7:] == '*':
                    filelist = self.getMySongs()
                    data = data.replace('*', ';;;'.join(filelist))
            self.sckt.send(self.getPDU(data))

    def customSend(self, pdu):
        self.sckt.send(pdu)

program = Program((sys.argv[1], int(sys.argv[2])))