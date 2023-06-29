import threading, socket, sys, os, pyaudio, wave, time, queue
from PyQt5.QtCore import *
from PyQt5.QtGui import *
from PyQt5.QtWidgets import *

# tamanho do header que contém o tamanho da mensagem
HEADERSIZE = 10

# caminho para a pasta de músicas
MUSICFOLDER = "./music"

class ServerSide():
    def __init__(self, port):
        self.sckt = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sckt.bind(('localhost', port))
        threading.Thread(target=self.listen, daemon=True).start()

    def listen(self):
        full_msg = ''
        new_msg = True
        while True:
            msg, addr = self.sckt.recvfrom(1024)
            if new_msg and len(msg) >= HEADERSIZE:
                msglen = int(msg[:HEADERSIZE])
                new_msg = False
            full_msg += msg.decode("utf-8")
            while len(full_msg[HEADERSIZE:msglen + HEADERSIZE]) == msglen:
                new_msg = True
                if full_msg[HEADERSIZE:][:4] == 'play':
                    song = full_msg[HEADERSIZE:][5:][:msglen-5]
                    threading.Thread(target=self.stream(song, addr,)).start()
                full_msg = full_msg[HEADERSIZE + msglen:]
                if len(full_msg) > 10:
                    msglen = int(full_msg[:HEADERSIZE])
    
    def stream(self, song, address):
        with wave.open(os.path.join(MUSICFOLDER, song), 'rb') as wf:
            sample_rate = wf.getframerate()
            while len(data := wf.readframes(1024)):
                self.sckt.sendto(data, address)
                time.sleep(0.8*1024/sample_rate)
            self.sckt.sendto(b"stop"*50, address)

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
        self.customSend(self.getPDU('port ' + sys.argv[3]))

        self.outerLayout = QHBoxLayout()

        self.layout = QVBoxLayout()
        self.listView = QListWidget()
        self.userView = QListWidget()
        self.listView.itemClicked.connect(self.selectSong)
        self.listView.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.listView.setObjectName("Song List")
        self.userView.itemClicked.connect(self.getFileNames)
        self.userView.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.userView.setObjectName("User List")
        self.userView.setMaximumHeight(75)

        self.rightLayout = QVBoxLayout()
        self.playButton = QPushButton('Play File', self.mainwindow)
        self.playButton.clicked.connect(self.playSong)
        self.exposeButton = QPushButton('Expose Files', self.mainwindow)
        self.exposeButton.clicked.connect(self.exposeAllFiles)
        self.updateButton = QPushButton('Refresh', self.mainwindow)
        self.updateButton.clicked.connect(self.loadUserList)
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

        # variáveis de auxílio para pedir pela música
        self.selectedUser = None
        self.selectedSong = None
        self.server = ServerSide(int(sys.argv[3]))

        self.app.aboutToQuit.connect(self.disconnect)
        self.app.exec()
    
    # plays song
    def playSong(self):
        if self.selectedSong != None and self.selectedUser != None:
            ip, port = self.selectedUser.split(':')
            pair = (ip, int(port))
            sckt = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sckt.sendto(self.getPDU("play " + self.selectedSong), pair)
            self.q = queue.Queue(maxsize=2000)
            self.stopFlag = False
            self.playingSocket = threading.Thread(target=self.playUdpSong).start()
            self.listeningSocket = threading.Thread(target=self.getUdpSong(sckt,)).start()

    def getUdpSong(self, sckt):
        data = sckt.recvfrom(1024*4)
        print(data)
        while b"stop" not in data[0]:
            self.q.put(data[0])
            data = sckt.recvfrom(1024*4)
            print(data[0])
        
        self.q.put(data[0])
        sckt.close()
        print("OK")
        self.stopFlag = True

    def playUdpSong(self):
        p = pyaudio.PyAudio()
        stream = p.open(format=p.get_format_from_width(2),
					channels=2,
					rate=44100,
					output=True,
					frames_per_buffer=1024)
        while True:
            stream.write(self.q.get())
            if self.stopFlag and self.q.qsize() == 0:
                break
        print("OK")

    # seleciona música
    def selectSong(self, item):
        self.selectedSong = item.text()

    # pede a lista de arquivos de um usuário específico
    def getFileNames(self, item):
        ip, port = item.text().split(' ')[0].split(':')
        sport = item.text().split(' ')[1].replace('(','').replace(')','')
        self.selectedUser = ip+':'+sport
        self.customSend(self.getPDU('list ' + ip+':'+port))

    # envia ao servidor a própria lista de arquivos
    def exposeAllFiles(self):
        self.customSend(self.getPDU('export ' + ';;;'.join(self.getMySongs())))

    # pede ao servidor a lista de arquivos disponíveis
    def loadUserList(self):
        self.userView.clear()
        self.listView.clear()
        self.selectedUser = None
        self.selectedSong = None
        self.customSend(self.getPDU('user'))

    # anda pela pasta de músicas especificadas e retorna uma lista pro caminho de cada uma delas
    def getMySongs(self):
        filelist = []
        for root, dirs, files in os.walk(MUSICFOLDER):
            for file in files:
                if file.endswith('.wav'):
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
                    self.listView.clear()
                    for song in songList:
                        self.listView.addItem(song)
                elif full_msg[HEADERSIZE:][:4] == "user":
                    userList = full_msg[HEADERSIZE:][5:][:msglen-5].split(';;;')
                    self.userView.clear()
                    for user in userList:
                        if ":" in user:
                            ip, port, sport = user.split(":")
                            self.userView.addItem(f'{ip}:{port} ({sport})')
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