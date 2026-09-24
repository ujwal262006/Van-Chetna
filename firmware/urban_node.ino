/*
 * Van-Chetna — Urban/Industrial Hazard Node
 * Air Quality Monitoring (MQ-135) + LoRa Transmission
 * Node ID: URB01
 *
 * Hardware: ESP32 DevKit V1 (WROOM-32) + Ai-Thinker Ra-01H (SX1276, 868MHz) + MQ-135
 * Pin mapping: see Van-Chetna_Hardware_Integration_Guide.md, Section 3
 *
 * Required library: "LoRa" by Sandeep Mistry (install via Arduino Library Manager)
 */

#include <SPI.h>
#include <LoRa.h>

// ---------- Node Identity ----------
const char* NODE_ID = "URB01";
const char* HAZARD_TYPE = "AIR_QUALITY";

// ---------- LoRa Pins (Ra-01H) ----------
#define LORA_SCK   18
#define LORA_MISO  19
#define LORA_MOSI  23
#define LORA_NSS   5
#define LORA_RESET 14
#define LORA_DIO0  26
#define LORA_FREQ  866E6  // MUST match existing forest node (lora_sender.ino/node_main.ino) — India ISM band

// ---------- MQ-135 Pin ----------
#define MQ135_AO_PIN 35   // ADC1, input-only, via 10k+22k divider

// ---------- Timing ----------
const unsigned long READ_INTERVAL_MS = 5000;     // sensor sample every 5s
const unsigned long TX_INTERVAL_MS   = 10000;    // transmit every 10s
unsigned long lastReadTime = 0;
unsigned long lastTxTime = 0;

// ---------- Rolling Baseline for Anomaly Detection ----------
const int BASELINE_WINDOW = 20;     // number of samples for rolling baseline
int baselineBuffer[BASELINE_WINDOW];
int baselineIndex = 0;
float rollingBaseline = 0;

// ---------- Latest computed values ----------
int    latestRaw = 0;
int    latestRiskScore = 0;
int    latestConfidence = 0;
String latestSeverity = "NORMAL";

void setup() {
  Serial.begin(115200);
  delay(500);
  Serial.println("[URB01] Van-Chetna Urban Node booting...");

  pinMode(MQ135_AO_PIN, INPUT);

  // Initialize SPI with custom pins for Ra-01H
  SPI.begin(LORA_SCK, LORA_MISO, LORA_MOSI, LORA_NSS);
  LoRa.setPins(LORA_NSS, LORA_RESET, LORA_DIO0);

  if (!LoRa.begin(LORA_FREQ)) {
    Serial.println("[URB01] ERROR: LoRa init failed. Check wiring.");
    while (true) { delay(1000); }
  }
  LoRa.setSyncWord(0x34);   // MUST match existing forest node's default (it never calls setSyncWord, so library default 0x34 applies)
  Serial.println("[URB01] LoRa initialized OK at 868MHz.");

  // Prime baseline buffer with initial readings before entering main loop
  Serial.println("[URB01] Priming baseline (20 samples, ~4s)...");
  for (int i = 0; i < BASELINE_WINDOW; i++) {
    baselineBuffer[i] = analogRead(MQ135_AO_PIN);
    delay(200);
  }
  updateRollingBaseline();
  Serial.println("[URB01] Baseline primed. Entering main loop.");
}

void loop() {
  unsigned long now = millis();

  if (now - lastReadTime >= READ_INTERVAL_MS) {
    lastReadTime = now;
    readAndScore();
  }

  if (now - lastTxTime >= TX_INTERVAL_MS) {
    lastTxTime = now;
    transmitPacket();
  }
}

void readAndScore() {
  latestRaw = analogRead(MQ135_AO_PIN);

  // Update rolling baseline buffer
  baselineBuffer[baselineIndex] = latestRaw;
  baselineIndex = (baselineIndex + 1) % BASELINE_WINDOW;
  updateRollingBaseline();

  // Deviation from baseline as % above baseline
  float deviation = 0;
  if (rollingBaseline > 0) {
    deviation = ((float)latestRaw - rollingBaseline) / rollingBaseline * 100.0;
  }

  // Rule-based risk scoring from deviation.
  // NOTE: thresholds below are reasonable MVP defaults — recalibrate against
  // real ambient readings at your deployment site before trusting live alerts.
  int devInt = (int)deviation;
  if (devInt < 15) {
    latestRiskScore = constrain(map(devInt, 0, 15, 0, 25), 0, 25);
    latestSeverity = "NORMAL";
    latestConfidence = 85;
  } else if (devInt < 40) {
    latestRiskScore = constrain(map(devInt, 15, 40, 25, 50), 25, 50);
    latestSeverity = "WATCH";
    latestConfidence = 80;
  } else if (devInt < 80) {
    latestRiskScore = constrain(map(devInt, 40, 80, 50, 80), 50, 80);
    latestSeverity = "WARNING";
    latestConfidence = 85;
  } else {
    latestRiskScore = 90;
    latestSeverity = "CRITICAL";
    latestConfidence = 90;
  }

  Serial.printf("[URB01] Raw=%d Baseline=%.1f Dev=%.1f%% Risk=%d Sev=%s\n",
                latestRaw, rollingBaseline, deviation, latestRiskScore, latestSeverity.c_str());
}

void updateRollingBaseline() {
  long sum = 0;
  for (int i = 0; i < BASELINE_WINDOW; i++) sum += baselineBuffer[i];
  rollingBaseline = (float)sum / BASELINE_WINDOW;
}

void transmitPacket() {
  // Packet format: VCN1,<NODE_ID>,<HAZARD_TYPE>,<RISK_SCORE>,<SEVERITY>,<CONFIDENCE>,<RAW_VALUE>,<TIMESTAMP_MS>
  String packet = "VCN1," + String(NODE_ID) + "," + String(HAZARD_TYPE) + "," +
                   String(latestRiskScore) + "," + latestSeverity + "," +
                   String(latestConfidence) + "," + String(latestRaw) + "," +
                   String(millis());

  LoRa.beginPacket();
  LoRa.print(packet);
  LoRa.endPacket();

  Serial.println("[URB01] TX: " + packet);
}
