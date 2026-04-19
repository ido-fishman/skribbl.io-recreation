import base64
import datetime
import hashlib
import random
import threading

from cryptography.hazmat.primitives.ciphers.aead import AESGCM

import pygame
import wx
import socket
# from pygame.draw import lines
# from scapy.contrib.tcpao import calc_tcpao_traffic_key
# from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
# from cryptography.hazmat.backends import default_backend
# from cryptography.hazmat.primitives import padding
import os



from tcp_by_size import send_with_size, recv_by_size

drawing = False
time_with_no_server = 0
DH_KEY = ""
connected = False
def encrypt_data(plaintext: bytes, key: bytes):
    aesgcm = AESGCM(key)
    nonce = os.urandom(12)  # GCM standard nonce size
    ciphertext = aesgcm.encrypt(nonce, plaintext, None)
    return nonce + ciphertext  # send both nonce and ciphertext


def diffie_hellman(socket):
    global DH_KEY
    print("diffie hellman")

    data = recv_by_size(socket).decode()
    p,g,A = data.split(",")
    p = int(p)
    g = int(g)
    A = int(A)
    b = random.randint(70000, 1000000)
    B = pow(g,b,p)
    send_with_size(socket, (f"{B}".encode()))
    key = pow(A,b,p)
    print("key " + str(key))
    DH_KEY = hashlib.sha256(str(key).encode()).hexdigest()[:16]
    print("xxxxxx: ", DH_KEY)


class WxChatClient(wx.Dialog):

    def __init__(self, parent, id, title, ip):
        super().__init__(parent, id, title, size=(1000, 562))
        self.ip = ip
        self.word = ""
        self.word_len = ""
        self.panel = wx.Panel(self)
        self.bg_image = wx.Bitmap("skribbl-io.jpg", wx.BITMAP_TYPE_JPEG)
        self.panel.Bind(wx.EVT_PAINT, self.onPaint)
        self.send_lock = threading.Lock()
        self.game_stopped = False
        self.canvas_width = 600
        self.canvas_height = 350
        self.canvas = wx.Panel(self.panel, size=(self.canvas_width, self.canvas_height))
        self.canvas.SetPosition((180, 100))
        self.canvas.SetBackgroundColour("white")
        self.canvas.Hide()

        self.drawing_enabled = False
        self.is_drawing = False
        self.lines = []
        self.current_line = []
        self.pen_color = wx.Colour(0, 0, 0)
        self.client_sock = socket.socket()

        #time:

        self.time = wx.TextCtrl(self.panel, pos=(200, 20), size=(60, 40), style=wx.TE_READONLY)
        self.time.SetFont(wx.Font(20, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_BOLD))
        self.time.SetValue("50")
        self.time.Hide()
        self.round_time = -1
        self.end_time = datetime.datetime.now()

        self.canvas.Bind(wx.EVT_LEFT_DOWN, self.on_mouse_down)
        self.canvas.Bind(wx.EVT_MOTION, self.on_mouse_move)
        self.canvas.Bind(wx.EVT_LEFT_UP, self.on_mouse_up)
        self.canvas.Bind(wx.EVT_PAINT, self.onCanvasPaint)

        self.name = wx.TextCtrl(self.panel, pos=(350, 20), size=(300, 60), style=wx.TE_PROCESS_ENTER)
        self.name.SetFont(wx.Font(30, wx.FONTFAMILY_DECORATIVE, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_BOLD))
        self.name.SetForegroundColour(wx.Colour(19,63,138))
        self.name.SetHint("name")

        self.IP = wx.TextCtrl(self.panel, value="127.0.0.1", pos=(350, 100), size=(300, 60), style=wx.TE_PROCESS_ENTER)
        self.IP.SetFont(wx.Font(30, wx.FONTFAMILY_DECORATIVE, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_BOLD))
        self.IP.SetForegroundColour(wx.Colour(19,63,138))
        self.IP.SetHint("IP")

        self.ConnectBTN = wx.Button(self.panel, 10, 'connect', (390, 170), (220, 60))
        self.ConnectBTN.SetBackgroundColour(wx.Colour(0, 0, 255))
        self.ConnectBTN.SetForegroundColour(wx.Colour(180, 180, 180))
        self.ConnectBTN.SetFont(wx.Font(30, wx.FONTFAMILY_DECORATIVE, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_BOLD))

        self.undo_btn = wx.Button(self.panel, label="Undo", pos=(660, 480), size=(60, 40))
        self.undo_btn.Bind(wx.EVT_BUTTON, self.onUndo)

        self.color_buttons = {
            "Black": wx.Button(self.panel, label="Black", pos=(40, 480), size=(50, 40)),
            "Red": wx.Button(self.panel, label="Red", pos=(100, 480), size=(50, 40)),
            "Green": wx.Button(self.panel, label="Green", pos=(160, 480), size=(50, 40)),
            "Blue": wx.Button(self.panel, label="Blue", pos=(220, 480), size=(50, 40)),
            "Brown": wx.Button(self.panel, label="Brown", pos=(280, 480), size=(50, 40)),
            "Pink": wx.Button(self.panel, label="Pink", pos=(340, 480), size=(50, 40)),
            "Cyan": wx.Button(self.panel, label="Cyan", pos=(400, 480), size=(50, 40)),
            "Orange": wx.Button(self.panel, label="Orange", pos=(460, 480), size=(50, 40)),
            "Gray": wx.Button(self.panel, label="Gray", pos=(520, 480), size=(50, 40)),
            "Yellow": wx.Button(self.panel, label="Yellow", pos=(580, 480), size=(50, 40)),
        }

        self.color_buttons["Black"].Bind(wx.EVT_BUTTON, self.on_color_button)
        self.color_buttons["Black"].SetBackgroundColour((0, 0, 0))
        self.color_buttons["Black"].SetForegroundColour((255, 255, 255))
        self.color_buttons["Red"].Bind(wx.EVT_BUTTON, self.on_color_button)
        self.color_buttons["Red"].SetBackgroundColour((255, 0, 0))
        self.color_buttons["Green"].Bind(wx.EVT_BUTTON, self.on_color_button)
        self.color_buttons["Green"].SetBackgroundColour((0, 255, 0))
        self.color_buttons["Blue"].Bind(wx.EVT_BUTTON, self.on_color_button)
        self.color_buttons["Blue"].SetBackgroundColour((0, 0, 255))
        self.color_buttons["Brown"].Bind(wx.EVT_BUTTON, self.on_color_button)
        self.color_buttons["Brown"].SetBackgroundColour((139, 69, 19))
        self.color_buttons["Pink"].Bind(wx.EVT_BUTTON, self.on_color_button)
        self.color_buttons["Pink"].SetBackgroundColour((255, 105, 180))
        self.color_buttons["Cyan"].Bind(wx.EVT_BUTTON, self.on_color_button)
        self.color_buttons["Cyan"].SetBackgroundColour((0, 255, 255))
        self.color_buttons["Orange"].Bind(wx.EVT_BUTTON, self.on_color_button)
        self.color_buttons["Orange"].SetBackgroundColour((255, 165, 0))
        self.color_buttons["Gray"].Bind(wx.EVT_BUTTON, self.on_color_button)
        self.color_buttons["Gray"].SetBackgroundColour((169, 169, 169))
        self.color_buttons["Yellow"].Bind(wx.EVT_BUTTON, self.on_color_button)
        self.color_buttons["Yellow"].SetBackgroundColour((255, 255, 0))

        for k in self.color_buttons:
            self.color_buttons[k].Hide()
        self.undo_btn.Hide()

        self.chat = wx.ListBox(self.panel, pos=(800, 20), size=(180, 400))
        self.chat.Hide()
        self.user_data = wx.ListBox(self.panel, pos=(20, 100), size=(140, 200))
        self.user_data.Hide()
        self.guess = wx.TextCtrl(self.panel, pos=(820, 440), size=(140, 60), style=wx.TE_PROCESS_ENTER)
        self.guess.Hide()
        self.guess.Hint = "only low chars"

        self.secret = wx.ListBox(self.panel, pos=(400, 20), size=(120, 20), style=wx.TE_PASSWORD)
        self.secret.Hide()

        self.fill_enabled = False

        self.fill_button = wx.ToggleButton(self.panel, label="Fill: Off", pos=(740, 480), size=(60, 40))
        self.fill_button.Bind(wx.EVT_TOGGLEBUTTON, self.on_toggle_fill)
        self.fill_button.Hide()


        # music
        pygame.mixer.init()
        pygame.mixer.music.load("music2.mp3")
        pygame.mixer.music.play(-1)
        pygame.mixer.music.set_volume(0)



        self.guess.Bind(wx.EVT_TEXT_ENTER, self.onGuessEnter)
        self.ConnectBTN.Bind(wx.EVT_BUTTON, self.onConnect)
        self.fill_places = []
        #self.Bind(wx.EVT_CLOSE, self.onExit)
        self.Bind(wx.EVT_CLOSE, self.on_close)
        self.Centre()
        self.ShowModal()
        self.last_guess = ""

    def on_close(self, event):
        if connected:
            if not self.game_stopped:
                send_with_size(self.client_sock, "EXT_")
                self.client_sock.settimeout(None)
                try:
                    recv_by_size(self.client_sock)
                except Exception:
                    pass
                pygame.mixer.music.set_volume(0)
        self.Destroy()

    def send_canvas(self):
        if not hasattr(self, 'send_lock'):
            print("send_lock missing, skipping send_canvas")
            return
        with self.send_lock:
            try:
                data = "CNV_"
                for line, color in self.lines:
                    data += "|"
                    for pt in line:
                        r = color.Red()
                        g = color.Green()
                        b = color.Blue()
                        data += f"{pt.x},{pt.y},{r},{g},{b}_"
                    data = data[:-1]
                print(data)
                send_with_size(self.client_sock, data)

            except Exception:
                print("not sent")

    def onPaint(self, event):
        dc = wx.PaintDC(self.panel)
        dc.DrawBitmap(self.bg_image, 0, 0)

    def on_toggle_fill(self, event):
        self.fill_enabled = self.fill_button.GetValue()
        label = ""
        if self.fill_enabled:
            label = "Fill: On"
        else:
            label = "Fill: Off"
        self.fill_button.SetLabel(label)


    def onCanvasPaint(self, event):
        dc = wx.PaintDC(self.canvas)
        for line, color in self.lines:
            dc.SetPen(wx.Pen(color, 2))
            dc.DrawLines(line)
        if self.current_line:
            dc.SetPen(wx.Pen(self.pen_color, 2))
            dc.DrawLines(self.current_line)


    def on_mouse_down(self, event):
        if not self.drawing_enabled:
            return
        if not self.fill_enabled:
            self.is_drawing = True
            self.current_line = [event.GetPosition()]
            self.canvas.Refresh()
        elif self.drawing_enabled:
            print("fill3")
            dc = wx.ClientDC(self)
            color = dc.GetPixel(event.GetPosition().x, event.GetPosition().y)
            threading.Thread(target=self.fill, args=(event.GetPosition().x, event.GetPosition().y, color, self.pen_color)).start()


    def on_mouse_move(self, event):
        if not self.drawing_enabled:
            return
        if self.is_drawing and event.Dragging() and event.LeftIsDown() and not self.fill_enabled:
            self.current_line.append(event.GetPosition())
            self.canvas.Refresh(False)




    def on_mouse_up(self, event):
        if not self.drawing_enabled:
            return
        if self.is_drawing:
            if not self.fill_enabled:
                self.is_drawing = False
                self.lines.append((self.current_line, self.pen_color))
                self.current_line = []
                self.canvas.Refresh()
                threading.Thread(target=self.send_canvas).start()



    def fill(self, x, y, back_color, new_color):
        print(f"Filling from ({x},{y})...")
        dc = wx.ClientDC(self.canvas)
        stack = [(x, y)]
        visited = set()
        points = []

        if back_color == new_color:
            return

        while stack:
            cx, cy = stack.pop()
            if (cx, cy) in visited:
                continue
            visited.add((cx, cy))

            if not (0 <= cx < self.canvas_width and 0 <= cy < self.canvas_height):
                continue

            current_color = dc.GetPixel(cx, cy)
            if current_color != back_color:
                continue

            dc.SetPen(wx.Pen(new_color))
            dc.DrawPoint(cx, cy)
            points.append(wx.Point(cx, cy))  # Collect points for sending

            # Push neighbors
            stack.append((cx + 1, cy))
            stack.append((cx - 1, cy))
            stack.append((cx, cy + 1))
            stack.append((cx, cy - 1))

        self.canvas.Refresh()

        # Add the filled region to lines so it can be sent with send_canvas()
        if points:
            self.lines.append((points, new_color))
            threading.Thread(target=self.send_canvas).start()



    def onUndo(self, event):
        if self.lines:
            self.lines.pop()
            self.canvas.Refresh()
            threading.Thread(target=self.send_canvas).start()


    def on_color_button(self, event):
        color_label = event.GetEventObject().GetLabel()
        if color_label == "Black":
            self.pen_color = wx.Colour(0, 0, 0)
        elif color_label == "Red":
            self.pen_color = wx.Colour(255, 0, 0)
        elif color_label == "Green":
            self.pen_color = wx.Colour(0, 255, 0)
        elif color_label == "Blue":
            self.pen_color = wx.Colour(0, 0, 255)
        elif color_label == "Brown":
            self.pen_color = wx.Colour(139, 69, 19)
        elif color_label == "Pink":
            self.pen_color = wx.Colour(255, 105, 180)
        elif color_label == "Cyan":
            self.pen_color = wx.Colour(0, 255, 255)
        elif color_label == "Orange":
            self.pen_color = wx.Colour(255, 165, 0)
        elif color_label == "Gray":
            self.pen_color = wx.Colour(169, 169, 169)
        elif color_label == "Yellow":
            self.pen_color = wx.Colour(230, 230, 0)
        self.canvas.Refresh()  # Refresh to apply the new pen color

    def onGuessEnter(self, event):
        text = self.guess.GetValue().strip()
        if text:
            encrypted_bytes = encrypt_data(text.encode(), hashlib.sha256(DH_KEY.encode()).digest())
            b64_text = base64.b64encode(encrypted_bytes).decode()  # bytes -> base64 string
            send_with_size(self.client_sock, f"WRD_{self.name.Value} -> {b64_text}".encode())
            self.last_guess = self.guess.Value
            self.guess.SetValue("")

        # text = self.guess.GetValue().strip()
        # if text:
        #     # self.chat.Append(text)
        #     if text == self.word.lower():
        #         self.secret.Clear()
        #         self.secret.Append(self.word)
        #         # self.chat.Append("you guessed it!")
        #         self.guess.Hide()
        #         send_with_size(self.client_sock, f"GOT_{self.name.Value} guessed correct!")
        #     else:
        #         send_with_size(self.client_sock, f"WRD_{self.name.Value} -> {self.guess.Value}")




    def onConnect(self, event):
        global connected
        global DH_KEY
        if self.name.Value == "" or self.IP.Value == "":
            print("insert name & ip")
        else:
            try:
                self.client_sock = socket.socket()
                self.client_sock.settimeout(0.1)
                self.client_sock.connect((self.IP.Value, 5555))
                send_with_size(self.client_sock, self.name.Value.encode())
                data = recv_by_size(self.client_sock).decode()
                print(data)
                if "CON_ok" in data:
                    diffie_hellman(self.client_sock)
                    print("diffi ", DH_KEY)
                    self.IP.Hide()
                    self.ConnectBTN.Hide()
                    self.name.Hide()
                    self.SetTitle(self.name.Value + "'s skribble window")

                    self.listener = threading.Thread(target=self.listen)
                    self.listener.start()
                    connected = True
            except Exception:
                print("problem with connection, try again")

    def listen(self):
        global time_with_no_server
        global drawing
        global connected
        while True:
            if self.round_time != -1:
                remaining = self.end_time - datetime.datetime.now()
                seconds_left = int(remaining.total_seconds())
                try:
                    self.time.SetValue(str(seconds_left))
                except Exception:
                    pass

            try:

                bdata = recv_by_size(self.client_sock)
                data = bdata.decode()
                print("data11111111111111111111111: " + data)
                if data == "":
                    break
                else:
                    action = data[:3]
                    data = data[4:]
                    print("ac = " + action)
                    if action.startswith("ER"):
                        if "1" in action:
                            print("message is too long")
                            self.chat.Append("server->msg is too long")
                    elif action == "MSG":
                        self.chat.Append(data)

                    elif action == "EXR":
                        self.chat.Append(data)
                        self.game_stopped = True
                        self.drawing_enabled = False

                    elif action == "SOK":
                        time_with_no_server = 0

                    elif action == "STR":
                        #self.guess.Show()
                        self.chat.Show()
                        self.canvas.Show()
                        self.secret.Show()
                        self.user_data.Show()
                        if not drawing:
                            self.guess.Show()
                        sdata = data.split("_")
                        self.word_len = sdata[0]
                        self.round_time = sdata[1]

                        self.secret.Clear()
                        if not drawing:
                            secured_data = ""
                            for i in self.word_len.split(" ")[:-1]:
                                secured_data += "_ " * int(i)
                            secured_data += self.word_len
                            self.secret.Append(secured_data)

                        else:
                            print("word2: ", self.word)
                            self.secret.Append(self.word)

                        self.end_time = datetime.datetime.now() + datetime.timedelta(seconds=int(self.round_time))
                        self.time.Show()


                    elif action == "USD":
                        self.user_data.Clear()
                        for i in data.split("|"):
                            name, points, placement = i.split(":")
                            self.user_data.Append(f"{name} -> {points} -> {placement}")

                        print(data)


                    elif action == "GOT":
                        if data == self.name.Value:
                            self.secret.Clear()
                            self.secret.Append(self.last_guess)
                            self.chat.Append("you guessed it!")
                            self.guess.Hide()
                        else:
                            self.chat.Append(f"{data} guessed it!")


                    elif action == "DRW":
                        self.word = data.split("_")[-1]
                        print("word: ",self.word)

                        while len(self.lines) > 0:
                            self.lines.pop(0)
                        self.chat.Append("you are drawing")
                        drawing = True
                        self.drawing_enabled = True
                        self.guess.Hide()
                        self.canvas.Refresh()
                        self.fill_button.Show()
                        for k in self.color_buttons:
                            self.color_buttons[k].Show()
                        self.undo_btn.Show()





                    elif action == "GUS":
                        while len(self.lines) > 0:
                            self.lines.pop(0)
                        self.chat.Append("you are guessing")
                        drawing = False
                        self.drawing_enabled = False
                        self.canvas.Refresh()
                        self.fill_button.Hide()
                        for k in self.color_buttons:
                            self.color_buttons[k].Hide()
                        self.undo_btn.Hide()

                    elif action == "PRT":
                        if self.drawing_enabled == False:
                            print("Clearing previous lines")
                            self.lines.clear()

                            try:
                                dc = wx.ClientDC(self.canvas)
                            except Exception as e:
                                print(e)

                            print("Drawing new lines")

                            for line_data in data.split("|")[1:]:
                                points = line_data.split("_")
                                if not points:
                                    continue

                                temp_line = []
                                last_color = None

                                for point in points:
                                    x, y, r, g, b = map(int, point.split(
                                        ","))
                                    pos = wx.Point(x, y)
                                    color = wx.Colour(r, g, b)
                                    dc.SetPen(wx.Pen(color))
                                    dc.DrawPoint(pos)

                                    if last_color is None:
                                        last_color = color

                                    if color != last_color:
                                        if temp_line:
                                            self.lines.append(
                                                (temp_line, last_color))
                                            temp_line = []
                                        last_color = color

                                    temp_line.append(pos)

                                if temp_line:
                                    self.lines.append((temp_line, last_color))

                            self.canvas.Refresh()
                    elif action == "FIN":
                        print("finish started")
                        connected = False
                        self.game_stopped = True
                        self.user_data.Clear()
                        for i in data.split("|"):
                            name, points, placement = i.split(":")
                            self.user_data.Append(f"{name} -> {points} -> {placement}")
                        self.chat.Hide()
                        for k in self.color_buttons:
                            self.color_buttons[k].Hide()




                    else:
                        print("bad code")
            except Exception as e:
                #print("no")
                time_with_no_server += 1
                if time_with_no_server > 20:
                    self.chat.Append("server disconnected game stops")
                    print("server disconnected game stops")
                    connected = False
                    while True:
                        pass

                continue


def main():
    app = wx.App(0)
    ip = "127.0.0.1"
    WxChatClient(None, -1, 'skribbl', ip)
    app.MainLoop()


if __name__ == '__main__':
    main()
