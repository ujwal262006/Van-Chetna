/*
 * Van-Chetna — Riverine Hazard Node
 * Water Level / Flash-Flood Risk Monitoring (HC-SR04) + LoRa Transmission
 * Node ID: RIV01
 *
 * Hardware: ESP32 DevKit V1 (WROOM-32) + Ai-Thinker Ra-01H (SX1276, 868MHz) + HC-SR04
 * Pin mapping: see Van-Chetna_Hardware_Integration_Guide.md, Section 4
 *
 * Required library: "LoRa" by Sandeep Mistry (install via Arduino Library Manager)
 */

#include <SPI.h>
#include <LoRa.h>

// ---------- Node Identity ----------
const char* NODE_ID = "RIV01";
const char* HAZARD_TYPE = "WATER_LEVEL";

// ---------- LoRa Pins (Ra-01H) ----------
#define LORA_SCK   18
#define LORA_MISO  19
#define LORA_MOSI  23
#define LORA_NSS   5
#define LORA_RESET 14
#define LORA_DIO0  26
#define LORA_FREQ  866E6  // MUST match existing forest node (lora_sender.ino/node_main.ino) — India ISM band

// ---------- HC-SR04 Pins ----------
#define TRIG_PIN 25
#define ECHO_PIN 33   // via 10k+22k divider

// IMPORTANT: measure the actual sensor mounting height above the normal/dry
// riverbed or reference water surface on-site, in cm, and update this value
// before deployment. This directly determines water-level accuracy.
const float SENSOR_MOUNT_HEIGHT_CM = 200.0;

// ---------- Timing ----------
const unsigned long READ_INTERVAL_MS = 5000;
const unsigned long TX_INTERVAL_MS   = 10000;
unsigned long lastReadTime = 0;
unsigned long lastTxTime = 0;

// ---------- History buffer for rate-of-rise calculation ----------
const int HISTORY_SIZE = 6;   // 6 samples x 5s = 30s rolling window
float levelHistory[HISTORY_SIZE];
int historyIndex = 0;
bool historyFilled = false;

// ---------- Latest computed values ----------
float  latestDistanceCm = 0;
float  latestWaterLevelCm = 0;
float  latestRiseRateCmPerMin = 0;
int    latestRiskScore = 0;
int    latestConfidence = 0;
String latestSeverity = "NORMAL";

void setup() {
  Serial.begin(115200);
  delay(500);
  Serial.println("[RIV01] Van-Chetna Riverine Node booting...");

  pinMode(TRIG_PIN, OUTPUT);
  pinMode(ECHO_PIN, INPUT);
  digitalWrite(TRIG_PIN, LOW);

  SPI.begin(LORA_SCK, LORA_MISO, LORA_MOSI, LORA_NSS);
  LoRa.setPins(LORA_NSS, LORA_RESET, LORA_DIO0);

  if (!LoRa.begin(LORA_FREQ)) {
    Serial.println("[RIV01] ERROR: LoRa init failed. Check wiring.");
    while (true) { delay(1000); }
  }
  LoRa.setSyncWord(0x34);   // MUST match existing forest node's default (it never calls setSyncWord, so library default 0x34 applies)
  Serial.println("[RIV01] LoRa initialized OK at 868MHz.");
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

float readDistanceCm() {
  digitalWrite(TRIG_PIN, LOW);
  delayMicroseconds(2);
  digitalWrite(TRIG_PIN, HIGH);
  delayMicroseconds(10);
  digitalWrite(TRIG_PIN, LOW);

  long duration = pulseIn(ECHO_PIN, HIGH, 30000);  // 30ms timeout ~5m max range
  if (duration == 0) return -1;  // no echo / out of range

  return duration * 0.0343 / 2.0;  // speed of sound (cm/us) / 2 for round trip
}

void readAndScore() {
  latestDistanceCm = readDistanceCm();

  if (latestDistanceCm < 0) {
    Serial.println("[RIV01] WARNING: No echo received, sensor read failed this cycle.");
    latestConfidence = 30;
    return;
  }

  latestWaterLevelCm = SENSOR_MOUNT_HEIGHT_CM - latestDistanceCm;
  if (latestWaterLevelCm < 0) latestWaterLevelCm = 0;

  // Update rolling history for rate-of-rise
  int oldestIdxBeforeOverwrite = historyIndex;
  levelHistory[historyIndex] = latestWaterLevelCm;
  historyIndex = (historyIndex + 1) % HISTORY_SIZE;
  if (historyIndex == 0) historyFilled = true;

  if (historyFilled) {
    float oldest = levelHistory[historyIndex];  // next slot to be overwritten = oldest sample
    float windowMinutes = (READ_INTERVAL_MS * HISTORY_SIZE) / 60000.0;
    latestRiseRateCmPerMin = (latestWaterLevelCm - oldest) / windowMinutes;
  } else {
    latestRiseRateCmPerMin = 0;
  }

  // Rule-based flash-flood risk: combine absolute level + rate of rise.
  // NOTE: thresholds below are MVP placeholders — calibrate against your
  // actual deployment site's normal and flood-stage water levels before
  // relying on this for real alerts.
  int levelScore = constrain(map((int)latestWaterLevelCm, 0, 150, 0, 60), 0, 60);
  int riseScore  = constrain(map((int)latestRiseRateCmPerMin, 0, 20, 0, 40), 0, 40);
  latestRiskScore = constrain(levelScore + riseScore, 0, 100);

  if (latestRiskScore < 25)      latestSeverity = "NORMAL";
  else if (latestRiskScore < 50) latestSeverity = "WATCH";
  else if (latestRiskScore < 80) latestSeverity = "WARNING";
  else                           latestSeverity = "CRITICAL";

  latestConfidence = 90;

  Serial.printf("[RIV01] Dist=%.1fcm Level=%.1fcm Rise=%.1fcm/min Risk=%d Sev=%s\n",
                latestDistanceCm, latestWaterLevelCm, latestRiseRateCmPerMin,
                latestRiskScore, latestSeverity.c_str());
}

void transmitPacket() {
  // Packet format: VCN1,<NODE_ID>,<HAZARD_TYPE>,<RISK_SCORE>,<SEVERITY>,<CONFIDENCE>,<LEVEL_CM>,<RISE_RATE>,<TIMESTAMP_MS>
  String packet = "VCN1," + String(NODE_ID) + "," + String(HAZARD_TYPE) + "," +
                   String(latestRiskScore) + "," + latestSeverity + "," +
                   String(latestConfidence) + "," + String(latestWaterLevelCm, 1) + "," +
                   String(latestRiseRateCmPerMin, 1) + "," + String(millis());

  LoRa.beginPacket();
  LoRa.print(packet);
  LoRa.endPacket();

  Serial.println("[RIV01] TX: " + packet);
}
