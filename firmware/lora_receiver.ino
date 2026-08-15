#include <SPI.h>
#include <LoRa.h>

#define LORA_NSS  5
#define LORA_RST  14
#define LORA_DIO0 2

void setup() {
  Serial.begin(115200);
  LoRa.setPins(LORA_NSS, LORA_RST, LORA_DIO0);

  if (!LoRa.begin(866E6)) {
    Serial.println("LoRa init failed. Check wiring.");
    while (1);
  }
  Serial.println("LoRa receiver ready");
}

void loop() {
  int packetSize = LoRa.parsePacket();
  if (packetSize) {
    String received = "";
    while (LoRa.available()) {
      received += (char)LoRa.read();
    }
    Serial.println("Received: " + received);
  }
}