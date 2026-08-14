#include <SPI.h>
#include <LoRa.h>
#include <ArduinoJson.h>

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
  Serial.println("LoRa sender ready");
}

void loop() {
  StaticJsonDocument<256> doc;
  doc["node_id"] = "NODE_01";
  doc["event_id"] = "evt_test001";
  doc["timestamp"] = "2026-08-17T10:00:00Z";
  doc["sensor_type"] = "acoustic";
  doc["class"] = "normal";
  doc["confidence"] = 0.0;
  doc["battery_pct"] = 100;
  doc["lat"] = 30.4520;
  doc["lon"] = 77.5890;

  String payload;
  serializeJson(doc, payload);

  LoRa.beginPacket();
  LoRa.print(payload);
  LoRa.endPacket();

  Serial.println("Sent: " + payload);
  delay(3000);
}