// =====================================================================
// NODE B — LoRa Receiver (ESP32 + RA-01H only)
// =====================================================================
// Simple receiver. Build and test this node FIRST to confirm the LoRa
// link works before adding the mic to Node A.
//
// RA-01H (SX127x) wiring on Node B:
//   RA-01H  ->  ESP32
//   3.3V    ->  3V3
//   GND     ->  GND
//   SCK     ->  D18   (VSPI SCK  - handled by the SPI library default)
//   MISO    ->  D19   (VSPI MISO - handled by the SPI library default)
//   MOSI    ->  D23   (VSPI MOSI - handled by the SPI library default)
//   NSS     ->  D5
//   RESET   ->  D14
//   DIO0    ->  D26
//   Antenna ->  soldered on module
//
// Receives JSON packets from Node A and prints them to Serial so the
// gateway host can read them and POST to the backend /events endpoint.
// =====================================================================

#include <SPI.h>
#include <LoRa.h>

// --- LoRa (RA-01H / SX127x) control pins ---
// SCK/MISO/MOSI use the ESP32 default VSPI pins (18/19/23) automatically.
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

  Serial.println("Node B ready — LoRa receiver listening at 866 MHz");
}

void loop() {
  int packetSize = LoRa.parsePacket();
  if (packetSize) {
    String received = "";
    while (LoRa.available()) {
      received += (char)LoRa.read();
    }
    // Gateway host reads this line off serial and forwards it to the backend.
    Serial.println("Received: " + received);
    Serial.print("RSSI: ");
    Serial.println(LoRa.packetRssi());
  }
}
