/*
  Morse.h - Library for flashing Morse code.
  Created by David A. Mellis, November 2, 2007.
  Released into the public domain.
*/
#ifndef Radiance_h
#define Radiance_h

#include "Arduino.h"

#include <SPI.h>
#include <Ethernet.h>
#include <EthernetUdp.h>

#define MAX_BUFFER_RADIANCE 1024
#define RADIANCE_LOCAL_PORT 8888



#define RAD_DATA 0x2000
#define RAD_FRAMESYNC 0x5000


#define RADIANCE_ID "RADIANCE"

void copyArray(byte* src, byte* dst, int len);

class Radiance
{
  public:
    Radiance();

    void begin();
    void begin(byte mac[], byte ip[]);
    void setServerIP(IPAddress srv);

    uint8_t read();
    void printPacketHeader();
    void printPacketContent();
    
    
    inline void setPixelUpdateCallback(void (*fptr)(uint8_t data_channel, uint16_t data_offset, uint16_t data_length, uint8_t *data))
    {
      pixelUpdateCallback = fptr;
    }
    inline void setFrameShowCallback(void (*fptr)(void))
    {
      frameShowCallback = fptr;
    }
    uint8_t radiancePacket[MAX_BUFFER_RADIANCE];
    
  private:
    byte local_mac[];
    IPAddress local_ip;
    IPAddress server_ip;

    EthernetUDP Udp;
    
    uint16_t packetSize;

    uint16_t opcode;
    uint8_t data_channel;
    uint16_t data_offset;
    uint16_t data_length;

    void (*pixelUpdateCallback)(uint8_t channel, uint16_t data_offset, uint16_t data_length, uint8_t *data);
    void (*frameShowCallback)(void);
};

#endif
