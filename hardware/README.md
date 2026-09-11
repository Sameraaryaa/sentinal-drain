# Sentinel Drain — Hardware & Firmware Architecture

> **Navigation**: [🏠 Project Root](../README.md) | [☁️ Cloud Backend & AI](../backend/README.md) | [🖥️ Google Cloud Console](../frontend/README.md)

This directory contains the edge compute firmware, pinout definitions, and hardware specifications for the **Sentinel Drain ESP32-S3 Biosurveillance Node**.

---

## 1. Microcontroller & Sensor Pinout

| Pin / Interface | Peripheral / Sensor | Function & Signal Type |
|---|---|---|
| **ADC1_CH0 (GPIO 1)** | Industrial pH Electrode Probe | Analog input ($0–3.3\text{V}$), signal amplified via op-amp |
| **ADC1_CH1 (GPIO 2)** | Electrical Conductivity / TDS Sensor | Analog input, measures ionic dissolved solids & stormwater dilution |
| **ADC1_CH2 (GPIO 3)** | Oxidation-Reduction Potential (ORP) | Analog input, monitors microbial reducing state ($0–500\text{mV}$) |
| **ADC1_CH3 (GPIO 4)** | Optical Turbidity Sensor | Analog phototransistor measuring light attenuation (NTU) |
| **GPIO 5** | DS18B20 1-Wire Temperature Sensor | Digital temperature compensation ($ -10^\circ\text{C}$ to $+85^\circ\text{C}$) |
| **PWM (GPIO 6)** | Micro Peristaltic Pump A | Sample draw from community drain ($12\text{V}$ MOSFET driver) |
| **PWM (GPIO 7)** | Micro Peristaltic Pump B | Waste flush & rinse cycle |
| **GPIO 8** | Solenoid Valve Driver | Reagent chamber injection valve |
| **PWM (GPIO 9)** | Ceramic PTC Heater Block | PID closed-loop heating of LAMP reaction chamber to $63.0^\circ\text{C} \pm 0.5^\circ\text{C}$ |
| **I2C (SDA=10, SCL=11)** | TCS34725 / AS7262 Colorimeter | Reads optical absorbance ratio $A_{570}/A_{650}$ for LAMP color shift |
| **SPI (12, 13, 14, 15, 16, 17)**| SX1262 LoRa Transceiver | Long-range low-power backhaul to regional health gateway ($865–867\text{MHz}$) |
| **UART2 (TX=18, RX=19)** | SIM7080G Cellular NB-IoT Module | GSM / 2G fallback for low-LoRa-coverage catchments |
| **ADC2_CH0 (GPIO 20)** | Battery Voltage Divider | LiFePO4 battery charge monitor ($12.8\text{V}$ nominal) |
| **ADC2_CH1 (GPIO 21)** | Solar Panel Voltage Divider | Solar input charging monitor ($18.0\text{V}$ nominal) |

---

## 2. Firmware Architecture ([`esp32_firmware.ino`](file:///d:/sentinal%20drain/hardware/esp32_firmware.ino))

The ESP32-S3 firmware operates as an autonomous edge biosurveillance unit:

```
                  ┌────────────────────────────────────────┐
                  │          ESP32-S3 Main Loop            │
                  └──────────────────┬─────────────────────┘
                                     │
                 1. Sample Probes (pH, TDS, ORP, Turb, T)
                                     │
                                     ▼
                  ┌────────────────────────────────────────┐
                  │     Rolling Baseline Anomaly Engine    │
                  │ - Computes 24h rolling mean and stddev │
                  │ - Calculates per-channel Z-scores      │
                  │ - Evaluates composite anomaly score    │
                  └──────────────────┬─────────────────────┘
                                     │
                 2. Check Stormwater Dilution / Fouling
                                     │
                  ┌──────────────────┴─────────────────────┐
                  ▼                                        ▼
          [ Normal / Dilution ]                  [ Biological Anomaly ]
          - Log telemetry packet                 - Z-score >= 2.5σ
          - Store in LittleFS                    - Suppress if rain dilution
          - Transmit to gateway                  - Trigger Stage 2 LAMP Cycle
                                                           │
                                                           ▼
                                         ┌───────────────────────────────────┐
                                         │       Stage 2 LAMP Reaction       │
                                         │ - Peristaltic pump sample draw    │
                                         │ - Inject lyophilized primer mix   │
                                         │ - PID loop holds 63°C for 35 min  │
                                         │ - Read optical A570/A650 ratio    │
                                         │ - Classify POS / NEG / INCONCL    │
                                         └─────────────────┬─────────────────┘
                                                           │
                                            3. Package Multi-Stage Payload
                                                           │
                                                           ▼
                                         ┌───────────────────────────────────┐
                                         │    Store-and-Forward Subsystem    │
                                         │ - Store payload in LittleFS flash │
                                         │ - Attempt LoRa / GSM transmission │
                                         │ - Flush buffer upon reconnect     │
                                         └───────────────────────────────────┘
```

---

## 3. On-Device Edge Logic & Algorithms

### 3.1 Composite Anomaly Scoring
The rolling baseline engine stores the previous 288 samples (12–24 hours). Microbial sewage surges cause rapid reduction of Oxidation-Reduction Potential (ORP) and an elevation in dissolved ionic conductivity:
$$S = 0.20 \cdot Z_{\text{pH}} + 0.35 \cdot Z_{\text{Cond}} + 0.35 \cdot Z_{\text{ORP}} + 0.10 \cdot Z_{\text{Turb}}$$

### 3.2 Stormwater Runoff Dilution Guard (PRD FR-9)
In monsoon seasons, heavy rainfall washes through open community drains, depressing conductivity below $200\,\mu\text{S/cm}$ while elevating turbidity with silt. The firmware detects this pattern and flags the telemetry as a `DILUTION_EVENT`, suppressing false triggers to conserve reagents.

### 3.3 PID Temperature Loop (PRD FR-5)
Loop-mediated Isothermal Amplification (LAMP) requires constant incubation at $63.0^\circ\text{C} \pm 0.5^\circ\text{C}$:
$$u(t) = K_p e(t) + K_i \int_0^t e(\tau) d\tau + K_d \frac{de(t)}{dt}$$
Tuned with anti-windup clamping to prevent reagent denaturation.

---

## 4. How to Compile & Flash

1. Install [Arduino IDE](https://www.arduino.cc/en/software) or the [PlatformIO](https://platformio.org/) VS Code extension.
2. Add ESP32 board support: `https://raw.githubusercontent.com/espressif/arduino-esp32/gh-pages/package_esp32_index.json`.
3. Select board: **ESP32S3 Dev Module** (Flash: 16MB, PSRAM: 8MB OPI).
4. Install libraries:
   - `LittleFS` (Included in ESP32 core)
   - `RadioLib` (SX1262 LoRa driver)
   - `Adafruit TCS34725` (Optical colorimeter driver)
5. Flash `esp32_firmware.ino` over USB-C at 115200 baud.
