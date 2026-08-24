// =====================================================================
// NODE A — Acoustic sensor node (ESP32 + RA-01H + INMP441 mic)
// =====================================================================
// Full production node. Captures 5 s audio windows from the INMP441 mic,
// streams raw PCM to the companion (09_node_companion.py) over USB serial,
// and LoRa-transmits any classification result the companion sends back.
//
// RA-01H (SX127x) wiring — identical to Node B:
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
//
// INMP441 mic wiring — uses pins separate from the LoRa side:
//   INMP441 ->  ESP32
//   VDD     ->  3V3   (same rail as LoRa 3.3V)
//   GND     ->  GND   (same rail as LoRa GND)
//   SCK     ->  D27   (I2S bit clock)
//   WS      ->  D25   (I2S word select / LR clock)
//   SD      ->  D32   (I2S serial data in)
//   L/R     ->  GND   (selects LEFT channel)
// =====================================================================

#include <driver/i2s.h>
#include <SPI.h>
#include <LoRa.h>

// --- INMP441 mic (I2S) pins ---
#define I2S_SCK   27   // D27  bit clock
#define I2S_WS    25   // D25  word select
#define I2S_SD    32   // D32  serial data in
#define I2S_PORT  I2S_NUM_0

// --- LoRa (RA-01H / SX127x) control pins ---
// SCK/MISO/MOSI use the ESP32 default VSPI pins (18/19/23) automatically.
#define LORA_NSS   5   // D5
#define LORA_RST   14  // D14
#define LORA_DIO0  26  // D26

#define LORA_FREQ  866E6  // 866 MHz — India ISM band

#define SAMPLE_RATE     16000
#define WINDOW_SECONDS  5
#define WINDOW_SAMPLES  (SAMPLE_RATE * WINDOW_SECONDS)  // 80000 samples

int16_t* audioBuffer;  // ~160KB, needs to fit in ESP32 RAM — confirm once hardware is in hand

void setupI2S() {
  i2s_config_t i2s_config = {
    .mode = (i2s_mode_t)(I2S_MODE_MASTER | I2S_MODE_RX),
    .sample_rate = SAMPLE_RATE,
    .bits_per_sample = I2S_BITS_PER_SAMPLE_32BIT,
    .channel_format = I2S_CHANNEL_FMT_ONLY_LEFT,
    .communication_format = I2S_COMM_FORMAT_STAND_I2S,
    .intr_alloc_flags = 0,
    .dma_buf_count = 4,
    .dma_buf_len = 1024
  };

  i2s_pin_config_t pin_config = {
    .bck_io_num = I2S_SCK,
    .ws_io_num = I2S_WS,
    .data_out_num = I2S_PIN_NO_CHANGE,
    .data_in_num = I2S_SD
  };

  i2s_driver_install(I2S_PORT, &i2s_config, 0, NULL);
  i2s_set_pin(I2S_PORT, &pin_config);
}

void setup() {
  Serial.begin(921600);  // MUST match the companion script's baud rate exactly

  audioBuffer = (int16_t*)malloc(WINDOW_SAMPLES * sizeof(int16_t));
  if (audioBuffer == NULL) {
    Serial.println("Failed to allocate audio buffer! Out of memory.");
    while (1);
  }

  setupI2S();

  LoRa.setPins(LORA_NSS, LORA_RST, LORA_DIO0);
  if (!LoRa.begin(LORA_FREQ)) {
    Serial.println("LoRa init failed. Check wiring.");
    while (1);
  }
}

void captureWindow() {
  int32_t rawSample;
  size_t bytesRead;
  for (int i = 0; i < WINDOW_SAMPLES; i++) {
    i2s_read(I2S_PORT, &rawSample, sizeof(rawSample), &bytesRead, portMAX_DELAY);
    audioBuffer[i] = (int16_t)(rawSample >> 14);  // scale 32-bit I2S sample to 16-bit
  }
}

void sendAudioWindow() {
  Serial.write((const uint8_t*)"AUD1", 4);          // 4-byte header
  uint32_t count = WINDOW_SAMPLES;
  Serial.write((uint8_t*)&count, 4);                // sample count, little-endian
  Serial.write((uint8_t*)audioBuffer, WINDOW_SAMPLES * sizeof(int16_t)); // raw PCM
  Serial.flush();
}

void checkForClassificationResult() {
  if (Serial.available()) {
    String json = Serial.readStringUntil('\n');
    json.trim();
    if (json.length() > 0) {
      LoRa.beginPacket();
      LoRa.print(json);
      LoRa.endPacket();
    }
  }
}

void loop() {
  captureWindow();
  sendAudioWindow();

  unsigned long start = millis();
  while (millis() - start < 2000) {  // listen for companion's reply while next window fills
    checkForClassificationResult();
  }
}
