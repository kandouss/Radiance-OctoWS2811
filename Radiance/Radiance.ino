#include "Radiance.h"

#include <SPI.h>
#include <Ethernet.h>
#include <EthernetUdp.h>


#define USE_OCTOWS2811
#include <OctoWS2811.h>
#include <FastLED.h>

// OctoWS2811 settings
#define LEDS_PER_CHANNEL 512
#define NUM_CHANNELS 8

CRGB leds[LEDS_PER_CHANNEL * NUM_CHANNELS];

// Radiance settings
Radiance rad;

void setup() {
//  Serial.begin(19200);
  delay(500);
//  Serial.println("Beginning.");
  rad.begin();
  rad.setPixelUpdateCallback(updatePixels);
  rad.setFrameShowCallback(showFrame);
  
  LEDS.addLeds<OCTOWS2811>(leds, LEDS_PER_CHANNEL);
  LEDS.setBrightness(200);

  for(uint16_t i=0; i<LEDS_PER_CHANNEL * NUM_CHANNELS; i++) {
    leds[i] = CRGB(0,0,0);
  }
  LEDS.show();
  LEDS.delay(10);
  
}

void loop() {
  rad.read();
}

void updatePixels(uint8_t data_channel, uint16_t data_offset, uint16_t data_length, uint8_t *data){
    // send to leds
//    Serial.printf("Updating channel %d length %d\n", data_channel, data_length);
    data_length = data_offset+data_length>LEDS_PER_CHANNEL ? LEDS_PER_CHANNEL - data_offset : data_length;
//    Serial.printf("clipped data_length is %d\n", data_length);
    memcpy( &leds[data_channel*LEDS_PER_CHANNEL + data_offset], data, 3*data_length);
//  LEDS.delay(10);
}

void showFrame() {
    LEDS.show();
}
