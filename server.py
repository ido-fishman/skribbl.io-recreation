import base64
import datetime
import hashlib
import math
import random
import socket
import time
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from tcp_by_size import send_with_size, recv_by_size
import threading
import wx

users = {} #name:[socket, addr, isDrawing, points, placement, guessed correct, DH_KEY]
players = []
game_stopped = False

drawable_words = [
    "apple", "airplane", "ant", "Banana", "Ball", "Bear", "Bed", "Bee", "Bell", "Bird",
    "Book", "Boat","Bow", "Bread", "Bridge", "Broom", "Butterfly", "Cake", "Camera", "Car", "Castle",
    "Cat", "Chair", "Cheese", "Clock", "Cloud", "Computer", "Cookie", "Cow", "Crown", "Cup",
    "Dinosaur", "Dog", "Door", "Dragon", "Dress", "Duck", "Egg", "Elephant", "Fire", "Fish",
    "Flag", "Flower", "Fork", "Frog", "Ghost", "Glasses", "Giraffe", "Guitar", "Hamburger", "Hammer",
    "Hat", "Helicopter", "House", "Ice cream", "Island", "Jacket", "Jellyfish", "Key", "Kite", "Knife",
    "Ladder", "Lamp", "Laptop", "Leaf", "Lion", "Lollipop", "Magnet", "Mailbox", "Map",
    "Milk", "Mirror", "Moon", "Mountain", "Mushroom", "Music", "Octopus", "Paint", "Panda", "Pants",
    "Parrot", "Pencil", "Phone", "Pig", "Pizza", "Plane", "Planet", "Police", "Rainbow", "Robot",
    "Rocket", "Sandwich", "Shark", "Shoe", "Snowman", "Spoon", "Sun", "Table", "Toothbrush", "Train",
    "Phone", "Desk", "Zebra", "Water", "WhatsApp", "Carrot", "Cucumber", "Fishbowl", "Glove",
    "Hotdog", "Jumper", "Kangaroo", "Koala", "Lighthouse", "Marshmallow", "Mango", "Ninja", "Owl",
    "Pineapple", "Popcorn", "Skateboard", "Snowflake", "Spider", "Telescope",
    "Tent", "Turtle", "Umbrella", "Vase", "Whale", "puzzle", "sword", "goat", "youtube", "gun",
    "tree", "bush", "card", "king", "google", "sock","queen", "speaker", "cinema", "cup"
]
Rounds = 0
Round_len = 0
users_a = 0
lock = threading.Lock()
"""
def handle_client(c_socket, rounds, round_len):
    global users
    global names

    name = recv_by_size(c_socket).decode()
    if name not in users.keys():
        users[name] = (False, 0, 1)
        names.append(name)
        send_with_size(c_socket, "ok".encode())
        print()
    send_with_size(c_socket, "notok".encode())
    while len(users) < 2:
        pass
"""
def decrypt_data(encrypted_data: bytes, key: bytes):
    aesgcm = AESGCM(key)
    nonce = encrypted_data[:12]
    ciphertext = encrypted_data[12:]
    plaintext = aesgcm.decrypt(nonce, ciphertext, None)
    return plaintext

def generate_prime():
    print("start")
    prime_numbers = [1000000000033, 1000000000093, 1000000000167, 1000000000573, 1000000000617, 1000000000693, 1000000001093, 1000000001143, 1000000001297, 1000000001423]
    num = random.randint(0, 6)
    print(prime_numbers[num])
    return prime_numbers[num]

def get_divisors(n):
    divisors = []
    for i in range(1, int(math.sqrt(n)) + 1):
        if n % i == 0:
            divisors.append(i)
            if i != n // i:
                divisors.append(n // i)
    return divisors

def check_primitive_root(g, num, divisors):
    for divisor in divisors:
        if divisor == 1:
            continue
        if pow(g, (num - 1) // divisor, num) == 1:
            return False
    return True

def find_primitive_root(num):
    divisors = get_divisors(num - 1)
    for g in range(2, num):
        if check_primitive_root(g, num, divisors):
            return g
    return None

def diffie_hellman(socket):
    try:
        global diffie_hellman_keys
        print("diffie hellman")
        p = generate_prime()
        g = find_primitive_root(p)

        a = random.randint(70000, 1000000)
        A = pow(g,a,p)

        send_with_size(socket, (f"{p},{g},{A}".encode()))
        B = int(recv_by_size(socket).decode())
        key = pow(B,a,p)
        #diffie_hellman_keys[socket] = hashlib.sha256(str(key).encode()).hexdigest()[:16]
        print("key " + str(hashlib.sha256(str(key).encode()).hexdigest()[:16]))
        return hashlib.sha256(str(key).encode()).hexdigest()[:16]
    except Exception as e:
        print(e)
        return



def send_to_all(data):
    for i in users:
        send_with_size(users[i][0], f"MSG_{data}")

def send_exit_to_all(data):
    for i in users:
        send_with_size(users[i][0], f"EXR_{data}")

def send_canvas(data):
    for i in users:
        send_with_size(users[i][0], f"PRT_{data}")


def get_placement():
    global users

    player_points = [(player, users[player][3]) for player in users]

    sorted_players = sorted(player_points, key=lambda x: x[1], reverse=True)

    placement = 1
    prev_points = None
    same_rank_count = 0

    for i, (player, points) in enumerate(sorted_players):
        if points == prev_points:

            users[player][4] = placement
            same_rank_count += 1
        else:

            placement = i + 1
            users[player][4] = placement
            prev_points = points
            same_rank_count = 1

def all_correct():
    for i in users:
        if users[i][5] == False and users[i][2] == False:
            return False
    return True

def send_correct(data):
    for i in users:
        send_with_size(users[i][0], f"GOT_{data}")



def get_word_len(word):
    print(word)
    all_words = word.split(" ")
    to_return = ""
    for i in all_words:
        to_return += f"{len(i)} "
    return to_return


def send_ok_massage():
    last_send = datetime.datetime.now()
    while not game_stopped:
        if datetime.datetime.now() - last_send >= datetime.timedelta(seconds=1.5):
            for i in users:
                send_with_size(users[i][0], "SOK_server is ok")
            last_send = datetime.datetime.now()
        time.sleep(0.1)


def main():
    global users
    global players
    global game_stopped


    app = wx.App(False)
    dialog = WxChatClient(-1, "Game Settings")

    if dialog.continue_flag:
        print("Starting game...")
        print("ROUNDS:", Rounds, "ROUND_TIME:", Round_len, "PLAYERS:", users_a)
    else:
        print("User closed window without starting. Exiting.")
        return

    print('server start\n')
    s = socket.socket()
    s.bind(('0.0.0.0', 5555))
    s.listen(1)


    #connectiom loop
    u_connected = 0
    while u_connected < users_a:
        lock.acquire()
        c, addr = s.accept()
        name = recv_by_size(c).decode()
        if name not in users.keys():
            u_connected += 1
            send_with_size(c, "CON_ok".encode())
            k = diffie_hellman(c)
            print("diffi ", k)

            users[name] = [c, addr, False, 0, 1, False, k]
            players.append(name)
            c.settimeout(0.2)
            for x in users:
                print(x)
                send_with_size(users[x][0], f"MSG_{name} is connected ☺")
        lock.release()
        ok_t = threading.Thread(target=send_ok_massage)
        ok_t.start()

    #loop start
    for r in range(len(users) * Rounds):
        for i in users:
            users[i][2] = False
        drawing = players[r % len(users)]
        users[drawing][2] = True
        word = random.choice(drawable_words)

        #sends you your mission
        for i in users:
            users[i][5] = False
            if users[i][2] == True:
                send_with_size(users[i][0], f"DRW_you are drawing!_{word}")
            else:
                send_with_size(users[i][0], f"GUS_you are not drawing!")

        #sends word and round len to every player
        word_len = get_word_len(word)
        print(f"STR_{word_len}_{Round_len}")
        for name in users:
            send_with_size(users[name][0], f"STR_{word_len}_{Round_len}")
        start_time = datetime.datetime.now()
        end_time = start_time + datetime.timedelta(seconds=Round_len)
        all_guessed = False
        middle = 0
        amount = 0

        #starts the waiting loop until all guessed or time ended
        while datetime.datetime.now() < end_time and not all_guessed:

            for name in users:
                try:
                    data = recv_by_size(users[name][0]).decode()
                    action = data[:3]
                    data = data[4:]
                    if action == "EXT":
                        print(f"{name} exited, game stops")
                        data = f"{name} exited, game stops"
                        game_stopped = True
                        threading.Thread(target=send_exit_to_all, args=(data,)).start()
                        exit()
                    elif action == "WRD":
                        d = data.split("-> ")[1]
                        print("d1", d)
                        data2 = ""
                        try:
                            encrypted_bytes = base64.b64decode(d)  # decode base64 string to bytes
                            data2 = decrypt_data(encrypted_bytes, hashlib.sha256(users[name][6].encode()).digest())
                            print("data2", data2)
                        except Exception as e:
                            print("error AES:", e)
                        d = data2.decode().lower()
                        print("d", d)
                        #print("dddasdsd",d)
                        #print("aaaa", users[name][6])
                        if len(d) > 20:
                            print("too long")
                            send_with_size(users[name][0], "ER1_massage is to long")
                        elif d.lower() == word.lower():
                            print("good")
                            msg_to_send = f'{name}'
                            t1 = threading.Thread(target=send_correct, args=(msg_to_send,))
                            t1.start()
                            current_time = datetime.datetime.now()
                            time_difference = end_time - current_time
                            time = time_difference.total_seconds()
                            print(time)
                            users[name][3] += int(time * 10)
                            middle += int(time * 10)
                            amount += 1
                            users[name][5] = True
                            if all_correct():
                                all_guessed = True
                                break
                        else:
                            print("not good")
                            t1 = threading.Thread(target=send_to_all, args=(f'{name} -> {d}',))
                            t1.start()

                    if action == "CNV":
                        t2 = threading.Thread(target=send_canvas, args=(data,))
                        t2.start()

                except Exception:
                    pass
        if amount>0:
            users[drawing][3] += int((middle/amount)*0.8)


        for name in users:
            print(users[name][3])
            to_send = "USD_"
            get_placement()
            for x in users:
                to_send += f"{x}:{users[x][3]}:{users[x][4]}|"
            send_with_size(users[name][0], to_send)

    for name in users:
        print(users[name][3])
        to_send = "FIN_"
        get_placement()
        for x in users:
            to_send += f"{x}:{users[x][3]}:{users[x][4]}|"
        send_with_size(users[name][0], to_send)
        game_stopped = True
    return






class WxChatClient(wx.Dialog):

    def __init__(self, id, title):
        super().__init__(None, id, title, size=(1000, 562))
        self.panel = wx.Panel(self)
        self.bg_image = wx.Bitmap("skribbl-io.jpg", wx.BITMAP_TYPE_JPEG)
        self.panel.Bind(wx.EVT_PAINT, self.onPaint)

        self.rounds = wx.TextCtrl(self.panel, pos=(350, 20), size=(300, 60), style=wx.TE_PROCESS_ENTER)
        self.rounds.SetFont(wx.Font(25, wx.FONTFAMILY_DECORATIVE, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_BOLD))
        self.rounds.SetForegroundColour(wx.Colour(19, 63, 138))
        self.rounds.SetHint("rounds")

        self.RT = wx.TextCtrl(self.panel, pos=(350, 100), size=(300, 60), style=wx.TE_PROCESS_ENTER)
        self.RT.SetFont(wx.Font(25, wx.FONTFAMILY_DECORATIVE, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_BOLD))
        self.RT.SetForegroundColour(wx.Colour(19, 63, 138))
        self.RT.SetHint("round time")

        self.PA = wx.TextCtrl(self.panel, pos=(350, 180), size=(300, 60), style=wx.TE_PROCESS_ENTER)
        self.PA.SetFont(wx.Font(25, wx.FONTFAMILY_DECORATIVE, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_BOLD))
        self.PA.SetForegroundColour(wx.Colour(19, 63, 138))
        self.PA.SetHint("players amount")

        self.StartBTN = wx.Button(self.panel, 10, 'connect', (390, 340), (220, 60))
        self.StartBTN.SetBackgroundColour(wx.Colour(0, 0, 255))
        self.StartBTN.SetForegroundColour(wx.Colour(180, 180, 180))
        self.StartBTN.SetFont(wx.Font(30, wx.FONTFAMILY_DECORATIVE, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_BOLD))

        self.StartBTN.Bind(wx.EVT_BUTTON, self.on_connect)
        self.Bind(wx.EVT_CLOSE, self.on_close)
        self.continue_flag = False

        self.Centre()
        self.ShowModal()

    def onPaint(self, event):
        dc = wx.PaintDC(self.panel)
        dc.DrawBitmap(self.bg_image, 0, 0)


    def on_connect(self, event):
        global Rounds, Round_len, users_a
        try:
            r = int(self.rounds.GetValue())
            rt = int(self.RT.GetValue())
            pa = int(self.PA.GetValue())
        except ValueError:
            print("Please enter only numbers.")
            return

        if rt < 30:
            print("Put some more time, less than 30 is hard")
        elif pa < 2:
            print("You can't play alone")
        else:
            Rounds = r
            Round_len = rt
            users_a = pa
            self.continue_flag = True
            self.Destroy()

    def on_close(self, event):
        self.Destroy()

if __name__ == '__main__':
    main()