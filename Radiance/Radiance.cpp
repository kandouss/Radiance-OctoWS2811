
#include "Arduino.h"
#include "Radiance.h"

//#include <SPI.h>
#include <Ethernet.h>
#include <EthernetUdp.h>
byte TESTMAC[] = {
  0xDE, 0xAD, 0xBE, 0xEF, 0xFE, 0xED
};

byte testx[] = {
  0x00, 0x01, 0x02, 0x03, 0x04, 0x05
};

// Constructor
Radiance::Radiance()
{
}



void copyArray(byte* src, byte* dst, int len) {
    memcpy(dst, src, sizeof(src[0])*len);
}


// Dot function
void Radiance::begin()
{
  copyArray(TESTMAC, local_mac, 6);
  Ethernet.begin(local_mac);
  delay(100);
  local_ip = Ethernet.localIP();
  Udp.begin(RADIANCE_LOCAL_PORT);
  Serial.printf("Begun. at %d.%d.%d.%d\n", local_ip[0], local_ip[1], local_ip[2], local_ip[3]);
}
// Dash function
void Radiance::begin(byte mac[])
{
  copyArray(mac, local_mac, 6);
  Ethernet.begin(local_mac);
  delay(100);
  local_ip = Ethernet.localIP();
  Udp.begin(RADIANCE_LOCAL_PORT);
  Serial.printf("Begun. at %d.%d.%d.%d\n", local_ip[0], local_ip[1], local_ip[2], local_ip[3]);
}

// Dash function
void Radiance::begin(byte mac[], IPAddress ip)
{
  copyArray(mac, local_mac, 6);
  local_ip = ip;
  Ethernet.begin(local_mac, local_ip);
  delay(100);
  local_ip = Ethernet.localIP();
  Udp.begin(RADIANCE_LOCAL_PORT);
  Serial.printf("Begun. at %d.%d.%d.%d\n", local_ip[0], local_ip[1], local_ip[2], local_ip[3]);
}



void Radiance::setServerIP(IPAddress srv){
  server_ip = srv;
}

uint8_t Radiance::read(){
  packetSize = Udp.parsePacket();
//  remoteIP = Udp.remoteIP();

  if (packetSize <= MAX_BUFFER_RADIANCE && packetSize > 0)
  {
    
//    Serial.printf("Got packet of size %lu\n", packetSize);
    Udp.read(radiancePacket, MAX_BUFFER_RADIANCE);
//    Serial.printf("<<<%.80s>>>\r\n", radiancePacket);
    
    if (0!=strncmp((char *)radiancePacket, RADIANCE_ID, 8))
      return 0;

    opcode = radiancePacket[8] | radiancePacket[9]<<8;  
    
    if(opcode==RAD_DATA) {
//      Serial.println("Data match");
      data_channel = radiancePacket[10];
      data_offset = radiancePacket[11] | radiancePacket[12]<<8;
      data_length = radiancePacket[13] | radiancePacket[14]<<8;
      
//      Serial.printf("Channel %d, offset %d, length %d\n", data_channel, data_offset, data_length);
      
      if(pixelUpdateCallback) (*pixelUpdateCallback)(data_channel, data_offset, data_length, radiancePacket+15);
      
    } else if (opcode == RAD_FRAMESYNC) {
      if(frameShowCallback) (*frameShowCallback)();
    }
  } else if (packetSize > MAX_BUFFER_RADIANCE){
//    Serial.println("Packet too big!");
  }else if (packetSize > 0) {
//    Serial.println("Got wrong sized packet.");
  }

  
  return 0;
}

void Radiance::printPacketHeader(){
  
}

void Radiance::printPacketContent(){
  
}
