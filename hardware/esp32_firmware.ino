/*
 * Sentinel Drain: Edge Firmware for ESP32-S3
 * Hyperlocal Wastewater Biosurveillance Network for PHC-Level Outbreak Early-Warning
 * 
 * Hardware Requirements:
 * - MCU: ESP32-S3 (Dual-core 240MHz, 8MB PSRAM, 16MB Flash)
 * - Stage 1 Probes:
 *     - Industrial pH Probe (Analog Pin A0 / GPIO 1)
 *     - Electrical Conductivity / TDS Sensor (Analog Pin A1 / GPIO 2)
 *     - Oxidation-Reduction Potential (ORP) Probe (Analog Pin A2 / GPIO 3)
 *     - Optical Turbidity Sensor (Analog Pin A3 / GPIO 4)
 *     - DS18B20 1-Wire Digital Temp Sensor (GPIO 5)
 * - Stage 2 Fluidics & Thermal Control:
 *     - Micro Peristaltic Pump A (Sample Draw) (PWM Pin GPIO 6)
 *     - Micro Peristaltic Pump B (Waste Flush) (PWM Pin GPIO 7)
 *     - Solenoid Valve (Reagent Chamber) (GPIO 8)
 *     - PTC Ceramic Heater Block (Assay chamber 63°C) (PWM Pin GPIO 9)
 *     - TCS34725 / AS7262 Optical Colorimetric Sensor (I2C SDA=GPIO 10, SCL=GPIO 11)
 * - Communications:
 *     - SX1262 LoRa Transceiver (SPI: MOSI=13, MISO=14, SCK=12, CS=15, RST=16, DIO1=17)
 *     - SIM7080G GSM/NB-IoT Module (Serial2: TX=18, RX=19)
 * - Power & Diagnostics:
 *     - Battery Voltage Divider (Analog Pin A4 / GPIO 20)
 *     - Solar Panel Voltage Divider (Analog Pin A5 / GPIO 21)
 */

#include <Arduino.h>
#include <SPI.h>
#include <Wire.h>
#include <Preferences.h>
#include <FS.h>
#include <LittleFS.h>

// --- Configuration Constants ---
#define NODE_ID "NODE-GP-01"
#define CATCHMENT_ID "CATCHMENT-RAMPUR-01"
#define FIRMWARE_VERSION "v1.1.0"

#define SAMPLING_INTERVAL_MS 300000   // 5 minutes Stage 1 sampling
#define BASELINE_WINDOW_SIZE 288      // 24 hours of 5-minute samples for rolling window
#define Z_SCORE_ANOMALY_THRESHOLD 2.5 // Standard deviations for anomaly trigger
#define DILUTION_CONDUCTIVITY_MIN 150 // uS/cm: surface water dilution indicator
#define DILUTION_TURBIDITY_MAX 800    // NTU: mud/rain runoff indicator

#define LAMP_TARGET_TEMP 63.0f        // Target isothermal temperature for LAMP (~63 deg C)
#define LAMP_HOLD_TIME_MS 2400000     // 40 minutes reaction time

// --- Global State Structures ---
struct Stage1Sample {
    uint32_t timestamp;
    float ph;
    float conductivity_us_cm;
    float orp_mv;
    float turbidity_ntu;
    float temperature_c;
    float anomaly_score;
    bool is_dilution_event;
};

struct Stage2Assay {
    uint32_t start_time;
    uint32_t duration_sec;
    float mean_temp_c;
    float optical_absorbance_650nm;
    float optical_absorbance_570nm;
    float absorbance_ratio;
    uint8_t result; // 0=Negative, 1=Positive, 2=Inconclusive
    float confidence;
};

struct NodeHealth {
    float battery_voltage;
    float solar_voltage;
    uint8_t battery_percent;
    uint8_t remaining_reagents;
    bool probe_fouling_suspected;
};

// --- Rolling Baseline Engine ---
class RollingBaselineEngine {
private:
    float ph_history[BASELINE_WINDOW_SIZE];
    float cond_history[BASELINE_WINDOW_SIZE];
    float orp_history[BASELINE_WINDOW_SIZE];
    uint16_t sample_count = 0;
    uint16_t head_index = 0;

public:
    void addSample(float ph, float cond, float orp) {
        ph_history[head_index] = ph;
        cond_history[head_index] = cond;
        orp_history[head_index] = orp;
        head_index = (head_index + 1) % BASELINE_WINDOW_SIZE;
        if (sample_count < BASELINE_WINDOW_SIZE) sample_count++;
    }

    void calculateStats(float history[], uint16_t count, float &mean, float &stddev) {
        if (count == 0) { mean = 0; stddev = 1.0f; return; }
        float sum = 0;
        for (uint16_t i = 0; i < count; i++) sum += history[i];
        mean = sum / count;

        float sq_diff_sum = 0;
        for (uint16_t i = 0; i < count; i++) {
            sq_diff_sum += (history[i] - mean) * (history[i] - mean);
        }
        stddev = sqrt(sq_diff_sum / count);
        if (stddev < 0.001f) stddev = 0.001f; // Prevent division by zero
    }

    float computeCombinedAnomalyScore(float ph, float cond, float orp, bool &dilution_flag) {
        if (sample_count < 12) return 0.0f; // Warm-up period

        float ph_mean, ph_std;
        float cond_mean, cond_std;
        float orp_mean, orp_std;

        calculateStats(ph_history, sample_count, ph_mean, ph_std);
        calculateStats(cond_history, sample_count, cond_mean, cond_std);
        calculateStats(orp_history, sample_count, orp_mean, orp_std);

        float z_ph = abs(ph - ph_mean) / ph_std;
        float z_cond = abs(cond - cond_mean) / cond_std;
        float z_orp = abs(orp - orp_mean) / orp_std;

        // Pathogen / sewage surge often causes sharp ORP drop and conductivity/pH shifts
        float combined_z = (0.25f * z_ph) + (0.35f * z_cond) + (0.40f * z_orp);

        // Dilution detection (monsoon rain runoff causes sudden drop in conductivity below baseline)
        if (cond < DILUTION_CONDUCTIVITY_MIN && (cond_mean - cond) > (2.0f * cond_std)) {
            dilution_flag = true;
        } else {
            dilution_flag = false;
        }

        return combined_z;
    }
};

// --- PID Temperature Controller for LAMP Chamber ---
class LampPidController {
private:
    float Kp = 6.0f;
    float Ki = 0.4f;
    float Kd = 2.5f;
    float integral = 0.0f;
    float prev_error = 0.0f;
    uint32_t last_calc_time = 0;

public:
    uint8_t update(float current_temp, float target_temp) {
        uint32_t now = millis();
        float dt = (now - last_calc_time) / 1000.0f;
        if (dt <= 0.0f || dt > 2.0f) dt = 0.1f;
        last_calc_time = now;

        float error = target_temp - current_temp;
        integral += error * dt;
        // Anti-windup
        if (integral > 100.0f) integral = 100.0f;
        if (integral < -100.0f) integral = -100.0f;

        float derivative = (error - prev_error) / dt;
        prev_error = error;

        float output = (Kp * error) + (Ki * integral) + (Kd * derivative);
        if (output < 0) output = 0;
        if (output > 255) output = 255;
        return (uint8_t)output;
    }
};

// --- Store and Forward Queue ---
class FlashStorageQueue {
public:
    bool begin() {
        return LittleFS.begin(true);
    }

    void queuePacket(const String &jsonPayload) {
        File f = LittleFS.open("/uplink_queue.log", FILE_APPEND);
        if (f) {
            f.println(jsonPayload);
            f.close();
        }
    }

    void flushToGateway() {
        if (!LittleFS.exists("/uplink_queue.log")) return;
        File f = LittleFS.open("/uplink_queue.log", FILE_READ);
        if (!f) return;

        while (f.available()) {
            String line = f.readStringUntil('\n');
            line.trim();
            if (line.length() > 0) {
                // Emulate uplink transmission over LoRa or GSM
                Serial.printf("[UPLINK-TRANSMIT] %s\n", line.c_str());
            }
        }
        f.close();
        LittleFS.remove("/uplink_queue.log");
    }
};

// Instances
RollingBaselineEngine baselineEngine;
LampPidController pidController;
FlashStorageQueue storageQueue;
NodeHealth currentHealth = { 12.8f, 18.2f, 96, 24, false };

void setup() {
    Serial.begin(115200);
    delay(1000);
    Serial.println("=================================================");
    Serial.println(" SENTINEL DRAIN - ESP32-S3 BIOSURVEILLANCE NODE ");
    Serial.printf(" Node: %s | Catchment: %s | FW: %s\n", NODE_ID, CATCHMENT_ID, FIRMWARE_VERSION);
    Serial.println("=================================================");

    storageQueue.begin();
    Serial.println("[SYSTEM] Flash queue initialized.");
    Serial.println("[SYSTEM] Baseline engine online. Beginning Stage-1 continuous sampling loop.");
}

void loop() {
    // 1. Read Analog Stage-1 Sensors (simulated ADC conversion)
    float raw_ph = 7.15f + (float)(random(-15, 15)) / 100.0f;
    float raw_cond = 820.0f + (float)(random(-40, 40));
    float raw_orp = 185.0f + (float)(random(-10, 10));
    float raw_turbidity = 42.0f + (float)(random(-5, 5));
    float raw_temp = 28.5f + (float)(random(-5, 5)) / 10.0f;

    // 2. Anomaly evaluation
    bool dilution_flag = false;
    float anomaly_score = baselineEngine.computeCombinedAnomalyScore(raw_ph, raw_cond, raw_orp, dilution_flag);
    baselineEngine.addSample(raw_ph, raw_cond, raw_orp);

    Stage1Sample sample = {
        (uint32_t)(millis() / 1000),
        raw_ph,
        raw_cond,
        raw_orp,
        raw_turbidity,
        raw_temp,
        anomaly_score,
        dilution_flag
    };

    // 3. Check for Anomaly Trigger
    bool trigger_stage2 = (anomaly_score >= Z_SCORE_ANOMALY_THRESHOLD && !dilution_flag);

    Serial.printf("[STAGE-1] pH:%.2f | Cond:%.1f uS/cm | ORP:%.1f mV | Turb:%.1f NTU | Score:%.2f | Dilution:%s | Trigger:%s\n",
        sample.ph, sample.conductivity_us_cm, sample.orp_mv, sample.turbidity_ntu,
        sample.anomaly_score, dilution_flag ? "YES" : "NO", trigger_stage2 ? "TRUE" : "FALSE");

    // Package packet into JSON
    String packet = "{";
    packet += "\"node_id\":\"" + String(NODE_ID) + "\",";
    packet += "\"catchment_id\":\"" + String(CATCHMENT_ID) + "\",";
    packet += "\"timestamp\":" + String(sample.timestamp) + ",";
    packet += "\"ph\":" + String(sample.ph, 2) + ",";
    packet += "\"conductivity\":" + String(sample.conductivity_us_cm, 1) + ",";
    packet += "\"orp\":" + String(sample.orp_mv, 1) + ",";
    packet += "\"turbidity\":" + String(sample.turbidity_ntu, 1) + ",";
    packet += "\"temp\":" + String(sample.temperature_c, 1) + ",";
    packet += "\"anomaly_score\":" + String(sample.anomaly_score, 2) + ",";
    packet += "\"dilution_flag\":" + String(dilution_flag ? "true" : "false");
    packet += "}";

    storageQueue.queuePacket(packet);
    storageQueue.flushToGateway();

    delay(10000); // Demo interval (in production: SAMPLING_INTERVAL_MS)
}
