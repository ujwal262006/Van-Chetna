# Van-Chetna — Hardware Integration Guide
**Exact wiring, pin mappings, and Ra-01H soldering points for all three nodes**

---

## 0. Global Safety Rules (apply to every node)

| Rule | Why |
|---|---|
| Ra-01H VCC → **3.3V only**, never 5V/VIN | Module is not 5V tolerant — will damage it |
| MQ-2, MQ-135 VCC → **5V (VIN pin)**, not 3.3V | These sensors need ~5V across the internal heater coil for correct sensitivity per datasheet — running at 3.3V gives weak, unreliable readings |
| MQ-2 AO, MQ-135 AO → **must pass through 10kΩ+22kΩ divider** before reaching ESP32 ADC pin | AO swings toward VCC (5V) under high gas concentration — undivided, this can damage the ADC pin |
| HC-SR04 VCC → **5V (VIN)** | Rated for 5V operation |
| HC-SR04 Echo → **must pass through 10kΩ+22kΩ divider** before ESP32 GPIO | Echo pulse is a 5V signal |
| HC-SR04 Trig → ESP32 GPIO direct, **no divider needed** | ESP32 3.3V HIGH is read correctly by HC-SR04 as valid trigger |
| DHT22 VCC → **3.3V** | Rated 3.3–6V; no mismatch, no divider needed, data line stays within 3.3V |

Voltage divider (same for all three): `Signal pin ──[10kΩ]── ESP32 pin ──[22kΩ]── GND`

---

## 1. Ra-01H (SX1276) — SPI Wiring, Common to All 3 Nodes

**Use this identical mapping for Urban and Riverine nodes (new builds).** For the Forest node, if your existing soldering already uses different pins, **keep it as-is** — do not rewire a working node. Just make sure whatever pins you used there are documented so Namya can keep the firmware pin-config consistent per node.

| Ra-01H Pad (check silkscreen label on module) | Function | ESP32 GPIO |
|---|---|---|
| VCC | Power | **3V3** |
| GND (any of the 3 ground pads) | Ground | GND |
| NSS | SPI Chip Select | GPIO5 |
| MOSI | SPI Data In | GPIO23 |
| MISO | SPI Data Out | GPIO19 |
| SCK | SPI Clock | GPIO18 |
| RESET | Module reset | GPIO14 |
| DIO0 | TX/RX-done interrupt | GPIO26 |
| DIO1–DIO5 | Not used | Leave unconnected |
| **ANT** | Antenna feed | Solder helix antenna wire lead directly here — no ESP32 connection |

### Soldering notes
- The module has small castellated pads along its edge — each labeled on the PCB silkscreen (VCC, GND, NSS, MOSI, MISO, SCK, RST, DIO0–5, ANT). Match jumper wires to labels directly, not by pin-counting, since layout can vary slightly by batch.
- **Tin the pad first** with a small amount of solder, then place the pre-tinned jumper wire tip and reflow — this avoids overheating the small SMD pads.
- Solder the **antenna's single wire lead to the ANT pad only**. Keep this wire as short and straight as practical, and route it away from the digital jumper wires (SPI lines) to minimize RF interference on both the antenna signal and the SPI bus.
- The 3 GND pads on the module are all internally common — you only need to wire one to the ESP32 GND, but soldering 2 for mechanical stability is fine too.
- Double-check VCC goes to **3V3, not VIN** before powering on — this is the #1 way to kill a Ra-01H.

---

## 2. Forest Node — Fire/Smoke Module Addition (MQ-2 + DHT22)

**Do not touch existing acoustic (INMP441) or LoRa wiring.** Only adding these two new sensors on free GPIOs.

| Sensor | Pin | ESP32 GPIO | Notes |
|---|---|---|---|
| MQ-2 | VCC | VIN (5V) | Heater needs 5V |
| MQ-2 | GND | GND | |
| MQ-2 | AO | GPIO34 (via 10k+22k divider) | GPIO34 is input-only/ADC-only — very unlikely to already be used by your mic or LoRa wiring |
| DHT22 | VCC | 3V3 | |
| DHT22 | GND | GND | |
| DHT22 | DATA (OUT) | GPIO4 | Breakout board has onboard pull-up — no extra resistor needed |

✅ **Verified against actual forest-node code** (`node_main.ino`): existing pins in use are I2S mic (SCK=27, WS=25, SD=32) and LoRa (NSS=5, RST=14, DIO0=26, SPI default 18/19/23). GPIO34 (MQ-2) and GPIO4 (DHT22) are both confirmed free — GPIO27 was the original suggestion but conflicts directly with the mic's I2S bit clock, so it's been moved to GPIO4.

### Fire/smoke module wiring diagram
```
        ESP32 (Forest Node)
    +-----------------------+
    | VIN(5V) ---------------+--> MQ-2 VCC
    | GND --------------------+--> MQ-2 GND
    | GPIO34 <---[10k]----+---- MQ-2 AO
    |           |            |
    |         [22k]           |
    |           |            |
    |         GND            |
    |                        |
    | 3V3 --------------------+--> DHT22 VCC
    | GND --------------------+--> DHT22 GND
    | GPIO4  <-----------------+---- DHT22 DATA
    +-----------------------+
```

---

## 3. Urban/Industrial Node — Full Build (ESP32 + Ra-01H + MQ-135)

| Component | Pin | ESP32 GPIO |
|---|---|---|
| Ra-01H | — | See Section 1 table |
| MQ-135 | VCC | VIN (5V) |
| MQ-135 | GND | GND |
| MQ-135 | AO | GPIO35 (via 10k+22k divider) |

```
        ESP32 (Urban Node)
    +-----------------------+
    | 3V3 --------------------+--> Ra-01H VCC
    | GND --------------------+--> Ra-01H GND
    | GPIO5  ------------------+--> Ra-01H NSS
    | GPIO23 ------------------+--> Ra-01H MOSI
    | GPIO19 <-----------------+---- Ra-01H MISO
    | GPIO18 ------------------+--> Ra-01H SCK
    | GPIO14 ------------------+--> Ra-01H RESET
    | GPIO26 <-----------------+---- Ra-01H DIO0
    |                        |      Ra-01H ANT --> Helix Antenna
    |                        |
    | VIN(5V) ---------------+--> MQ-135 VCC
    | GND --------------------+--> MQ-135 GND
    | GPIO35 <---[10k]----+---- MQ-135 AO
    |           |            |
    |         [22k]           |
    |           |            |
    |         GND            |
    +-----------------------+
```

---

## 4. Riverine Node — Full Build (ESP32 + Ra-01H + HC-SR04)

| Component | Pin | ESP32 GPIO |
|---|---|---|
| Ra-01H | — | See Section 1 table |
| HC-SR04 | VCC | VIN (5V) |
| HC-SR04 | GND | GND |
| HC-SR04 | Trig | GPIO25 (direct, no divider) |
| HC-SR04 | Echo | GPIO33 (via 10k+22k divider) |

```
        ESP32 (Riverine Node)
    +-----------------------+
    | 3V3 --------------------+--> Ra-01H VCC
    | GND --------------------+--> Ra-01H GND
    | GPIO5  ------------------+--> Ra-01H NSS
    | GPIO23 ------------------+--> Ra-01H MOSI
    | GPIO19 <-----------------+---- Ra-01H MISO
    | GPIO18 ------------------+--> Ra-01H SCK
    | GPIO14 ------------------+--> Ra-01H RESET
    | GPIO26 <-----------------+---- Ra-01H DIO0
    |                        |      Ra-01H ANT --> Helix Antenna
    |                        |
    | VIN(5V) ---------------+--> HC-SR04 VCC
    | GND --------------------+--> HC-SR04 GND
    | GPIO25 ------------------+--> HC-SR04 Trig
    | GPIO33 <---[10k]----+---- HC-SR04 Echo
    |           |            |
    |         [22k]           |
    |           |            |
    |         GND            |
    +-----------------------+
```

---

## 5. Bring-Up & Integration Sequence (recommended order)

Don't wire everything at once and power on — bring each node up incrementally so a fault is easy to isolate.

1. **Power each new ESP32 alone first** (no sensors, no LoRa) — confirm it boots, flashes, and connects over USB serial.
2. **Wire and test Ra-01H alone** on each new node — run a basic send/receive test sketch, confirm it talks to the existing forest-node receiver before adding sensors.
3. **Add one sensor at a time**, verify raw readings on serial monitor before adding the next:
   - Forest: MQ-2 first, confirm AO reads change with a lighter/incense test (ventilated area) → then DHT22.
   - Urban: MQ-135 alone, confirm baseline reading is stable.
   - Riverine: HC-SR04 alone, confirm distance readings are consistent at known distances.
4. **Only after each sensor reads correctly standalone**, integrate into the shared fusion/LoRa transmission firmware.
5. **MQ-2 and MQ-135 burn-in**: power both on continuously for 24–48 hours before trusting calibration — do this in parallel with other integration work so it doesn't block your timeline.

---

## 6. Final Pre-Power-On Checklist (per node)

- [ ] Ra-01H VCC confirmed on 3V3, not VIN
- [ ] MQ-2 / MQ-135 / HC-SR04 VCC confirmed on VIN (5V), not 3V3
- [ ] Every 5V-signal line (MQ-2 AO, MQ-135 AO, HC-SR04 Echo) passes through the 10k+22k divider before touching an ESP32 pin
- [ ] HC-SR04 Trig wired direct (no divider) — confirmed
- [ ] Antenna soldered to ANT pad only, no antenna wire touching other pads
- [ ] No pin conflicts between new sensors and existing forest-node mic/LoRa wiring
- [ ] All GND lines from every component tied to a common ESP32 GND
