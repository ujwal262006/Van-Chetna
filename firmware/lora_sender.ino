// =====================================================================
// NODE A — LoRa Sender test (ESP32 + RA-01H)
// =====================================================================
// Standalone LoRa transmit test for Node A. Sends a hardcoded event
// payload every 3 seconds so you can verify Node B receives it before
// wiring the mic and running the full node_main.ino pipeline.
//
// RA-01H (SX127x) wiring on Node A (identical to Node B):
//   RA-01H  ->  ESP32
//   3.3V    ->  3V3
//   GND     ->  GND
//   SCK     ->  D18   (VSPI SCK  - SPI library default)
//   MISO    ->  D19   (VSPI MISO - SPI library default)
//   MOSI    ->  D23   (VSPI MOSI - SPI library default)
//   NSS     ->  D5
//   RESET   ->  D14
//   DIO0    ->  D26
//   Antenna ->  soldered on module
// =====================================================================

#include <SPI.h>
#include <LoRa.h>
#include <ArduinoJson.h>

// --- LoRa (RA-01H / SX127x) control pins ---
#define LORA_NSS   5   // D5
#define LORA_RST   14  // D14
#define LORA_DIO0  26  // D26

#define LORA_FREQ  866E6  // 866 MHz — India ISM band

void setup() {
  Serial.begin(115200);

  LoRa.setPins(LORA_NSS, LORA_RST, LORA_DIO0);

  if (!LoRa.begin(LORA_FREQ)) {
    Serial.println("LoRa init failed. Check wiring.");
    while (1);
  }

  Serial.println("Node A ready — LoRa sender transmitting at 866 MHz");
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
