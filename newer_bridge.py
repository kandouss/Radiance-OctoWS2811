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
        return self
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
        """
        # This tells Radiance the name of our device, and how big the sampled canvas should be.

        """
        self.description = { "name":"Teensy Bridge","size":300.}


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

sqrt_3_4 = (3**0.5)/4
sqrt_2_2 = (2**0.5)/2
top_tet_verts = np.asarray([[0,0.5,0],[sqrt_3_4,-0.25,0],[-sqrt_3_4,-0.25,0],[0,0,sqrt_2_2]])
bottom_tet_verts = [top_tet_verts + top - top_tet_verts[-1] for top in top_tet_verts[0:3]]

top_edges = np.asarray([[top_tet_verts[i],top_tet_verts[(i+1)%3]] for i in range(3)] + [[top_tet_verts[i],top_tet_verts[-1]] for i in range(3)])

bottom_edges = np.concatenate([top_edges]+[np.asarray([[verts[i],verts[-1]] for i in range(3)])for verts in bottom_tet_verts])

all_edges = np.concatenate([top_edges,bottom_edges])

def rot2(angle):
    c = np.cos(angle)
    s = np.sin(angle)
    return np.asarray([[c,-s],[s,c]])

def rot3(angle,axis):
    ind = [0,1,2]
    ind.remove(axis)
    i = np.identity(3)
    row = [[ind[0],ind[0]],[ind[1],ind[1]]]
    col = [ind,ind]
    i[(row,col)] = rot2(angle)
    return i

lookup_edges   = all_edges * (3**-.5) + np.asarray([[[.5,.5,0]]])
physical_edges = (all_edges * (3**-.5)).dot(rot3(np.pi/6,2)).dot(rot3(np.pi/3,0)) + np.asarray([[[.5,.5,0]]])

segs = [Segment(x[::,[0,1]],y[::,[0,1]]) for x,y in zip(lookup_edges,physical_edges)]

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
while True:
    try:
        device.serve_forever()
    except KeyboardInterrupt:
        break
    except Exception as e:
        logging.exception(e)

