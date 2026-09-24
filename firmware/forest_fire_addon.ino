/*
 * Van-Chetna — Forest Node: Fire/Smoke Module ADD-ON
 *
 * *** THIS IS NOT A STANDALONE SKETCH — DO NOT FLASH THIS FILE DIRECTLY ***
 *
 * Merge the sections below into your EXISTING forest-node sketch (the one
 * already running acoustic AI streaming + LoRa transmission). This file has
 * no setup()/loop() of its own on purpose — it defines functions you call
 * from your existing setup() and loop(). It does not touch your INMP441 mic
 * wiring, I2S config, or audio serial streaming in any way.
 *
 * Required library: "DHT sensor library" by Adafruit (Library Manager) —
 * also installs "Adafruit Unified Sensor" as a dependency automatically.
 *
 * ============================ MERGE INSTRUCTIONS ============================
 * 1. Copy the #include and all variable/constant declarations below to the
 *    top of your existing forest-node .ino file.
 * 2. Inside your EXISTING setup(), add one line: fireModuleSetup();
 * 3. Inside your EXISTING loop(), add one line: fireModuleLoop();
 * 4. Wherever your existing code transmits acoustic LoRa packets, also call
 *    transmitFirePacket() — either right after the acoustic transmission, or
 *    on its own timer as already set up below. Both use the same LoRa object,
 *    so no double LoRa.begin() needed — reuse your existing LoRa.begin() call.
 * 5. Pin assignments below were checked against node_main.ino's actual pin
 *    usage (I2S: 27/25/32, LoRa: 5/14/18/19/23/26) — GPIO34 (MQ-2) and GPIO4
 *    (DHT22) are both confirmed free. If you rewire anything later, re-check
 *    against your current node_main.ino before reusing either pin.
 * ==============================================================================
 */

#include <DHT.h>

// ---------- Fire/Smoke Pins ----------
#define MQ2_AO_PIN   34    // ADC1, input-only, via 10k+22k divider — confirmed free
#define DHT22_PIN    4     // Changed from GPIO27 — that pin is your I2S mic's bit clock (SCK) in node_main.ino
#define DHTTYPE      DHT22

DHT dht(DHT22_PIN, DHTTYPE);

// ---------- Fire Module Timing ----------
const unsigned long FIRE_READ_INTERVAL_MS = 5000;
unsigned long lastFireReadTime = 0;

// ---------- Rolling baseline for smoke (drift compensation) ----------
const int SMOKE_BASELINE_WINDOW = 20;
int smokeBaselineBuffer[SMOKE_BASELINE_WINDOW];
int smokeBaselineIndex = 0;
float smokeRollingBaseline = 0;

// ---------- Latest fire module values — read these from your fusion logic ----------
int    latestSmokeRaw = 0;
float  latestTempC = 0;
float  latestHumidity = 0;
int    latestFireRiskScore = 0;
int    latestFireConfidence = 0;
String latestFireSeverity = "NORMAL";

// ===== Call this once from inside your existing setup() =====
void fireModuleSetup() {
  pinMode(MQ2_AO_PIN, INPUT);
  dht.begin();

  Serial.println("[FOR01-FIRE] Priming smoke baseline...");
  for (int i = 0; i < SMOKE_BASELINE_WINDOW; i++) {
    smokeBaselineBuffer[i] = analogRead(MQ2_AO_PIN);
    delay(100);
  }
  updateSmokeBaseline();
  Serial.println("[FOR01-FIRE] Fire/smoke module ready.");
}

// ===== Call this every loop() iteration — it self-throttles via millis() =====
void fireModuleLoop() {
  unsigned long now = millis();
  if (now - lastFireReadTime >= FIRE_READ_INTERVAL_MS) {
    lastFireReadTime = now;
    readAndScoreFire();
    transmitFirePacket();   // remove this line if you'd rather gate TX from your existing timer
  }
}

void updateSmokeBaseline() {
  long sum = 0;
  for (int i = 0; i < SMOKE_BASELINE_WINDOW; i++) sum += smokeBaselineBuffer[i];
  smokeRollingBaseline = (float)sum / SMOKE_BASELINE_WINDOW;
}

void readAndScoreFire() {
  latestSmokeRaw = analogRead(MQ2_AO_PIN);
  smokeBaselineBuffer[smokeBaselineIndex] = latestSmokeRaw;
  smokeBaselineIndex = (smokeBaselineIndex + 1) % SMOKE_BASELINE_WINDOW;
  updateSmokeBaseline();

  float h = dht.readHumidity();
  float t = dht.readTemperature();
  if (isnan(h) || isnan(t)) {
    Serial.println("[FOR01-FIRE] WARNING: DHT22 read failed, skipping this cycle.");
    return;
  }
  latestTempC = t;
  latestHumidity = h;

  float smokeDeviation = 0;
  if (smokeRollingBaseline > 0) {
    smokeDeviation = ((float)latestSmokeRaw - smokeRollingBaseline) / smokeRollingBaseline * 100.0;
  }

  // Rule-based fire risk: smoke spike + rising temp + falling humidity together
  // give higher confidence of an unattended fire vs. any single signal alone.
  // NOTE: temp/humidity reference ranges below are placeholders for typical
  // forest ambient conditions — recalibrate against your deployment site's
  // actual baseline climate before relying on this for real alerts.
  int smokeScore  = constrain(map((int)smokeDeviation, 0, 100, 0, 60), 0, 60);
  int tempScore   = constrain(map((int)t, 25, 45, 0, 25), 0, 25);
  int humidScore  = constrain(map((int)(100 - h), 30, 70, 0, 15), 0, 15);

  latestFireRiskScore = constrain(smokeScore + tempScore + humidScore, 0, 100);

  if (latestFireRiskScore < 25)      latestFireSeverity = "NORMAL";
  else if (latestFireRiskScore < 50) latestFireSeverity = "WATCH";
  else if (latestFireRiskScore < 80) latestFireSeverity = "WARNING";
  else                                latestFireSeverity = "CRITICAL";

  // Confidence rises when multiple independent signals agree
  int signalsElevated = (smokeScore > 20 ? 1 : 0) + (tempScore > 10 ? 1 : 0) + (humidScore > 5 ? 1 : 0);
  latestFireConfidence = 60 + (signalsElevated * 10);

  Serial.printf("[FOR01-FIRE] Smoke=%d(dev%.1f%%) Temp=%.1fC Hum=%.1f%% Risk=%d Sev=%s Conf=%d\n",
                latestSmokeRaw, smokeDeviation, t, h, latestFireRiskScore,
                latestFireSeverity.c_str(), latestFireConfidence);
}

// ===== Reuses your EXISTING LoRa object — do not call LoRa.begin() again =====
void transmitFirePacket() {
  // Packet format: VCN1,FOR01,FIRE,<RISK>,<SEVERITY>,<CONFIDENCE>,<SMOKE_RAW>,<TEMP_C>,<HUMIDITY>,<TIMESTAMP_MS>
  String packet = "VCN1,FOR01,FIRE," + String(latestFireRiskScore) + "," + latestFireSeverity + "," +
                   String(latestFireConfidence) + "," + String(latestSmokeRaw) + "," +
                   String(latestTempC, 1) + "," + String(latestHumidity, 1) + "," + String(millis());

  LoRa.beginPacket();
  LoRa.print(packet);
  LoRa.endPacket();

  Serial.println("[FOR01-FIRE] TX: " + packet);
}
