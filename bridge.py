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
def data_message(data, channel=0, offset=0):
    # print(int_list)
    message = (b'RADIANCE'
    + struct.pack('<h', 0x2000) # data opcode
    + struct.pack('B', channel) # channel
    + struct.pack('<h', offset) # offset
    + struct.pack('<h', len(data)) # length
    )
    if len(data[0])==4:
        for r,g,b,a in data:
            message += struct.pack('BBB', r, g, b)
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

class RadianceTeensyBridge(radiance.LightOutputNode):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.clients = []

        # This tells Radiance the name of our device, and how big the sampled canvas should be.
        self.description = {
            "name": "Teensy Bridge",
            "size": [100, 100]
        }

        # This would request 5 pixels at the corners and center.
        #self.lookup_2d([(0, 0), (0, 1), (1, 0), (1, 1), (0.5, 0.5)])

        # Instead, lets request 120 pixels around the border.
        N = 30
        self.lookup_2d = [(0, i / N) for i in range(N)]
        self.lookup_2d += [(i / N, 1) for i in range(N)]
        self.lookup_2d += [(1, 1 - i / N) for i in range(N)]
        self.lookup_2d += [(1 - i / N, 0) for i in range(N)]

        # If we stopped here, Radiance would visualize this display using the lookup coordinates
        # and show a square.
        # If the physical display looks different, we tell Radiance about it with the
        # "physical coordinates" command.
        # Lets tell Radiance to visualize the points as a circle instead.

        def moveToCircle(x, y):
            l = math.hypot(x - 0.5, y - 0.5)
            return (0.5 * (x - 0.5) / l + 0.5, 0.5 * (y - 0.5) / l + 0.5)
        self.physical_2d = [moveToCircle(x, y) for (x, y) in self.lookup_2d]

        # We can send radiance a PNG file to be used as a background image for visualization.
        # This logo image is not very useful, but perhaps some line-art of your venue would work well.

        #with open("../resources/library/images/logo.png", "rb") as f:
        #    self.geometry_2d = f.read()

        # Ask for frames from Radiance every 20 ms (50 FPS).
        # On flaky connections, set this to zero.
        # Doing so will request frames one-by-one in a synchronous manner,
        # which will avoid network congestion.
        self.period = 20
    def send_data(self, client_dict, values, channel, offset=0):
        if len(values) > 256:
            for k,packet in enumerate(grouper(256, values)):
                self.send_data(client_dict, packet, channel, offset+k*256)

        client_dict['sock'].sendto(
              data_message(values, channel=channel, offset=offset)
            , client_dict['ipport']
        )

    def send_frame_show(self, client_dict):
        client_dict['sock'].sendto(
            frame_show_message
          , client_dict['ipport']
        )
    def add_client(self, ip, port):
        cli_sock = socket.socket(socket.AF_INET, # Internet
                             socket.SOCK_DGRAM) # UDP
        # cli_sock.bicnd((ip, port))
        self.clients.append({
            'sock': cli_sock,
            'ipport': (ip, port)
        })
    # This gets called every time a frame is received.
    def on_frame(self, frame):
        for channel in range(8):
            for client_dict in self.clients:
                self.send_data(client_dict, frame, channel, 0)
        for client_dict in self.clients:
            self.send_frame_show(client_dict)

# Turn on logging so we can see debug messages
logging.basicConfig(level=logging.DEBUG)

# Construct our device
device = RadianceTeensyBridge()
device.add_client("192.168.86.47", 8888)

# Start it going
device.serve_forever()
