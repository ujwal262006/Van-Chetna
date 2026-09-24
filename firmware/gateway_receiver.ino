/*
 * Van-Chetna — Gateway / Receiver Node
 * Receives LoRa packets from all hazard nodes (Forest, Urban, Riverine) and
 * forwards them over Serial to the backend for ingestion.
 *
 * Hardware: ESP32 DevKit V1 (WROOM-32) + Ai-Thinker Ra-01H (SX1276, 868MHz)
 * Wiring: identical to Van-Chetna_Hardware_Integration_Guide.md, Section 1
 *
 * Required library: "LoRa" by Sandeep Mistry (install via Arduino Library Manager)
 *
 * Output format (one line per received packet), forwarded over Serial at 115200 baud:
 *   VCN1,<NODE_ID>,<HAZARD_TYPE>,<RISK_SCORE>,<SEVERITY>,<CONFIDENCE>,...,<TIMESTAMP_MS>|RSSI=<rssi>|SNR=<snr>
 */

#include <SPI.h>
#include <LoRa.h>

#define LORA_SCK   18
#define LORA_MISO  19
#define LORA_MOSI  23
#define LORA_NSS   5
#define LORA_RESET 14
#define LORA_DIO0  26
#define LORA_FREQ  866E6  // MUST match existing forest node (lora_sender.ino/node_main.ino) — India ISM band

void setup() {
  Serial.begin(115200);
  delay(500);
  Serial.println("[GATEWAY] Van-Chetna Gateway booting...");

  SPI.begin(LORA_SCK, LORA_MISO, LORA_MOSI, LORA_NSS);
  LoRa.setPins(LORA_NSS, LORA_RESET, LORA_DIO0);

  if (!LoRa.begin(LORA_FREQ)) {
    Serial.println("[GATEWAY] ERROR: LoRa init failed. Check wiring.");
    while (true) { delay(1000); }
  }
  LoRa.setSyncWord(0x34);   // MUST match existing forest node's default (it never calls setSyncWord, so library default 0x34 applies)
  Serial.println("[GATEWAY] LoRa initialized OK. Listening for node packets...");
}

void loop() {
  int packetSize = LoRa.parsePacket();
  if (packetSize) {
    String received = "";
    while (LoRa.available()) {
      received += (char)LoRa.read();
    }

    int rssi = LoRa.packetRssi();
    float snr = LoRa.packetSnr();

    // Basic protocol validation before forwarding to backend
    if (received.startsWith("VCN1,")) {
      Serial.println(received + "|RSSI=" + String(rssi) + "|SNR=" + String(snr, 1));
    } else {
      Serial.println("[GATEWAY] WARNING: dropped malformed packet: " + received);
    }
  }
}
