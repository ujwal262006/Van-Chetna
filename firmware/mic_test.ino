// =====================================================================
// NODE A — INMP441 mic bring-up test (ESP32)
// =====================================================================
// Minimal I2S read test to confirm the mic is wired correctly before
// running the full node_main.ino pipeline. Prints raw sample values;
// tap/speak near the mic and watch the numbers move.
//
// INMP441 mic wiring (matches node_main.ino):
//   INMP441 ->  ESP32
//   VDD     ->  3V3
//   GND     ->  GND
//   SCK     ->  D27   (I2S bit clock)
//   WS      ->  D25   (I2S word select)
//   SD      ->  D32   (I2S serial data in)
//   L/R     ->  GND   (selects LEFT channel)
// =====================================================================

#include <driver/i2s.h>

#define I2S_SCK  27   // D27  bit clock
#define I2S_WS   25   // D25  word select
#define I2S_SD   32   // D32  serial data in
#define I2S_PORT I2S_NUM_0

void setup() {
  Serial.begin(115200);

  i2s_config_t i2s_config = {
    .mode = (i2s_mode_t)(I2S_MODE_MASTER | I2S_MODE_RX),
    .sample_rate = 16000,
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

void loop() {
  int32_t samples[256];
  size_t bytes_read;
  i2s_read(I2S_PORT, samples, sizeof(samples), &bytes_read, portMAX_DELAY);
  Serial.printf("sample: %ld\n", samples[0] >> 14);
  delay(50);
}
