import socket
import struct
import sys
import argparse
import numpy as np
import radiance
import logging
import math
import itertools

frame_show_message = (b'RADIANCE'
    + struct.pack('<h',0x5000)
)
def data_message(data, channel=0, offset=0, swap_rg=False):
    # print(int_list)
    message = (b'RADIANCE'
    + struct.pack('<h', 0x2000) # data opcode
    + struct.pack('B', channel) # channel
    + struct.pack('<h', offset) # offset
    + struct.pack('<h', len(data)) # length
    )
    if len(data[0])==4:
        if not swap_rg:
            for r,g,b,a in data:
                message += struct.pack('BBB', r, g, b)
        else:
            for r,g,b,a in data:
                message += struct.pack('BBB', g, r, b)
    return message

# def send_data(client, values, channel, offset):
#     message = data_message(values, channel=args.channel, offset=args.offset)
#     sock.sendto(message, (ip, port))
def grouper(n, iterable):
    it = iter(iterable)
    while True:
       chunk = tuple(itertools.islice(it, n))
       if not chunk:
           return
       yield chunk

class Channel:
    def __init__(self, device_ip, port_no, channel_no, leds_no, swap_rg=False):
        self.device_ip = device_ip
        self.port_no = port_no
        self.channel_no = channel_no
        self.leds_no = leds_no
        self.swap_rg = swap_rg

class Segment:
    def __init__(self, path=None, preview=None):
        if path is None:
            path = []
        if preview is None:
            preview = path
        self.path = path
        self.preview = preview
        self.lookup = []
        self.physica = []
        self.channels = []

    def add_channel(self, device_ip, port_no, channel_no, leds_no, swap_rg=False):
        self.channels += [Channel(device_ip, port_no, channel_no, leds_no, swap_rg)]
        
    def create_lookup(self, leds_no=None):
        if leds_no is None:
            leds_no = 0
            for channel in self.channels:
                leds_no += channel.leds_no

        interpVal = lambda x,y,pfrac: x*(1-pfrac) + y*pfrac
        interp = lambda x,y,pfrac: tuple( interpVal(xv,yv,pfrac) for xv,yv in zip(x,y))
        def interpPath(path, leds_no, i):
            if len(path) < 2:
                return path[0]
            p = (i * len(path)/(leds_no - 1)) if leds_no else 0.5
            ppos = min(math.floor(p), len(path) - 2)
            pfrac = min(p-ppos,1.0)
            return interp(path[ppos],path[ppos+1],pfrac)

        assert(len(self.path) > 0)
        assert(leds_no > 0)
        self.lookup = list(interpPath(self.path,leds_no,i) for i in range(leds_no))
        self.physical = list(interpPath(self.preview,leds_no,i) for i in range(leds_no))
#        for i in range(leds_no):
#            self.lookup = 
#        for i in range(leds_no):
#            p = i * len(self.path) / (leds_no - 1)
#            ppos = min(math.floor(p), len(self.path) - 2)
#            pfrac = min(p - ppos, 1.0)
#            self.lookup += [(self.path[ppos][0] * (1 - pfrac) + self.path[ppos+1][0] * pfrac,
#                             self.path[ppos][1] * (1 - pfrac) + self.path[ppos+1][1] * pfrac)]

        self.lookup = []
        for i in range(leds_no):
            p = i * len(self.path) / (leds_no - 1)
            ppos = min(math.floor(p), len(self.path) - 2)
            pfrac = min(p - ppos, 1.0)
            self.lookup += [(self.path[ppos][0] * (1 - pfrac) + self.path[ppos+1][0] * pfrac,
                             self.path[ppos][1] * (1 - pfrac) + self.path[ppos+1][1] * pfrac)]

class RadianceTeensyBridge(radiance.LightOutputNode):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.segments = []
        self.sockets = {}
        self.clients = {}

        self.MAX_NUM_VALUES=20
        self.description = { "name":"Teensy Bridge","size":300.}
        """
        # This tells Radiance the name of our device, and how big the sampled canvas should be.
        self.description = {
            "name": "Teensy Bridge",
            "size": [100, 100]
        }

        # This would request 5 pixels at the corners and center.
        #self.lookup_2d([(0, 0), (0, 1), (1, 0), (1, 1), (0.5, 0.5)])

        # Instead, lets request 120 pixels around the border.
        N = 150
        self.lookup_2d = [(0.2, i / N) for i in range(N)]
        self.lookup_2d += [(i / N, 0.8) for i in range(N)]
        self.lookup_2d += [(0.8, 1 - i / N) for i in range(N)]
        self.lookup_2d += [(1 - i / N, 0) for i in range(N)]
        self.lookup_2d = self.lookup_2d[:512]

        # If we stopped here, Radiance would visualize this display using the lookup coordinates
        # and show a square.
        # If the physical display looks different, we tell Radiance about it with the
        # "physical coordinates" command.
        # Lets tell Radiance to visualize the points as a circle instead.

        def moveToCircle(x, y):
            l = math.hypot(x - 0.5, y - 0.5)
            return (0.5 * (x - 0.5) / (l*3) + 0.5, 0.5 * (y - 0.5) / l + 0.5)
        self.physical_2d = [moveToCircle(x, y) for (x, y) in self.lookup_2d]
        self.lookup_2d = self.physical_2d[:]

        # We can send radiance a PNG file to be used as a background image for visualization.
        # This logo image is not very useful, but perhaps some line-art of your venue would work well.

        #with open("../resources/library/images/logo.png", "rb") as f:
        #    self.geometry_2d = f.read()
        """

        # Ask for frames from Radiance every 20 ms (50 FPS).
        # On flaky connections, set this to zero.
        # Doing so will request frames one-by-one in a synchronous manner,
        # which will avoid network congestion.
        self.period = 0
        # 0.8

    def send_data(self, socket, client, values, channel, offset=0, swap_rg=False):
        print(len(values))
        for slice in range((len(values) + self.MAX_NUM_VALUES - 1) // self.MAX_NUM_VALUES):
            socket.sendto(data_message(values[slice*self.MAX_NUM_VALUES:min(len(values), (slice+1)*self.MAX_NUM_VALUES)], channel=channel, offset=offset+slice*self.MAX_NUM_VALUES, swap_rg=swap_rg), client)

    def send_frame_show(self, socket, client):
        socket.sendto(frame_show_message, client)

    """
    def add_client(self, ip, port):
        cli_sock = socket.socket(socket.AF_INET, # Internet
                             socket.SOCK_DGRAM) # UDP
        cli_sock.connect((ip, port))
        self.clients.append({
            'sock': cli_sock,
            'ipport': (ip, port)
        })
    """

    def create_radiance_lookup(self):
        self.lookup_2d = []
        self.physical_2d = []
        for segment in self.segments:
            segment.create_lookup()
            self.lookup_2d += segment.lookup
            self.physical_2d += [_[:2] for _ in segment.physical]

    def init_clients(self):
        self.sockets = {}
        self.clients = {}
        for segment in self.segments:
            for channel in segment.channels:
                client = (channel.device_ip, channel.port_no) 
                if client in self.clients:
                    continue
                cli_sock = socket.socket(socket.AF_INET, # Internet
                                         socket.SOCK_DGRAM) # UDP
                cli_sock.connect(client)
                self.sockets[cli_sock] = client
                self.clients[client] = cli_sock
                print(channel.device_ip, channel.port_no, cli_sock)

    # This gets called every time a frame is received.
    def on_frame(self, frame):
        frame_pos = 0
        for segment in self.segments:
            for channel in segment.channels:
                client = (channel.device_ip, channel.port_no) 
                self.send_data(self.clients[client], client, frame[frame_pos:frame_pos+channel.leds_no], channel.channel_no, 0, channel.swap_rg)
    
        for client, socket in self.clients.items():
            self.send_frame_show(socket, client)

        """
        for channel in range(7, 8):
            for client_dict in self.clients:
                self.send_data(client_dict, frame, channel, 0)
        for client_dict in self.clients:
            self.send_frame_show(client_dict)
        """

# Turn on logging so we can see debug messages
logging.basicConfig(level=logging.DEBUG)

# "192.168.0.101", 8888, 4 # xmas lights
# "192.168.0.101", 8888, 5 # short strip
# "192.168.0.102", 8888, 7 # tube strip

# Construct our device
device = RadianceTeensyBridge()

unit= np.e**complex(0,np.pi*2/3)
mid = np.e**complex(0,np.pi*1/3)

part = 0.25*np.asarray([[0,1],[1,unit],[1,2],[unit,mid],[1.,mid]],dtype=np.complex64)*unit**-0.25
full = np.concatenate([part,part*unit,part*unit*unit]) + complex(0.5,0.5)

coords = np.dstack([full.real,full.imag])

segs = [Segment(x,x) for x in coords]

for i,seg in enumerate(segs):
    seg.add_channel("192.168.0.101",8888,i,300,True)
device.segments.extend(segs)
#seg_a = Segment([(.1, .1),(.8,.8)],[(.1,.1),(.1,.8)])
#seg_a.add_channel("192.168.0.101", 8888, 4, 300, True)
#seg_a.add_channel("192.168.0.101", 8888, 5, 8, True)

#seg_b = Segment([(.1, .8), (.8, .1)],[(.1,.8),(.8,.8)])
#seg_b.add_channel("192.168.0.102", 8888, 7, 250, )

#device.segments += [seg_a]
#device.segments += [seg_b]

device.create_radiance_lookup()
device.init_clients()

# Start it going
device.serve_forever()
