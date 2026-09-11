"""
Unit Tests for Sentinel Drain Firmware & Edge Node Emulator
Verifies PRD requirements:
- FR-1: Continuous sensing
- FR-2: On-device rolling baseline anomaly scoring
- FR-3: Trigger logic for LAMP assay
- FR-5, FR-6: Isothermal LAMP kinetics and optical readout
- FR-7: Store-and-forward queue
- FR-8: Probe fouling detection
- FR-9: Stormwater dilution detection
"""

import pytest
from backend.app.firmware_emulator.edge_node import EdgeDrainNode

def test_rolling_baseline_and_anomaly_trigger():
    node = EdgeDrainNode("TEST-ND-01", "CAT-TEST", "PHC-TEST", 26.75, 83.37)

    # 1. Normal sample should have low anomaly score
    normal_sample = node.evaluate_sample(ph=7.20, cond=840.0, orp=185.0, turb=42.0, temp=28.5)
    assert normal_sample["anomaly_score"] < 2.0
    assert not normal_sample["trigger_assay_recommended"]
    assert not normal_sample["is_dilution_event"]

    # 2. Strong biological sewage anomaly: sudden reducing ORP drop + conductivity surge
    outbreak_sample = node.evaluate_sample(ph=6.45, cond=1350.0, orp=45.0, turb=95.0, temp=28.8)
    assert outbreak_sample["anomaly_score"] >= 2.2
    assert outbreak_sample["trigger_assay_recommended"]

def test_stormwater_dilution_detection():
    node = EdgeDrainNode("TEST-ND-02", "CAT-TEST", "PHC-TEST", 26.75, 83.37)

    # Monsoon rain runoff: severe conductivity drop (<200 uS/cm) + high turbidity (>500 NTU)
    diluted_sample = node.evaluate_sample(
        ph=6.90, cond=160.0, orp=175.0, turb=600.0, temp=27.5, rainfall_mm_hr=35.0
    )
    assert diluted_sample["is_dilution_event"] is True
    # PRD FR-9: Must suppress false alarm rather than trigger bioassay
    assert diluted_sample["trigger_assay_recommended"] is False

def test_probe_fouling_detection():
    node = EdgeDrainNode("TEST-ND-03", "CAT-TEST", "PHC-TEST", 26.75, 83.37)

    # Physical fouling: out of physical limits (pH < 3.0)
    fouled_sample = node.evaluate_sample(ph=2.40, cond=800.0, orp=400.0, turb=40.0, temp=28.0)
    assert fouled_sample["probe_fouling"] is True
    assert node.probe_fouling_detected is True
    assert fouled_sample["trigger_assay_recommended"] is False

def test_isothermal_lamp_bioassay_kinetics():
    node = EdgeDrainNode("TEST-ND-04", "CAT-TEST", "PHC-TEST", 26.75, 83.37)
    initial_reagents = node.reagents_remaining

    # Force positive assay
    pos_res = node.run_isothermal_lamp_assay(
        target_pathogen="Vibrio cholerae O1",
        force_result="POSITIVE"
    )
    assert pos_res["result"] == "POSITIVE"
    assert pos_res["optical_absorbance_ratio"] > 1.8
    assert pos_res["confidence"] > 0.90
    assert 62.0 <= pos_res["assay_temperature_c"] <= 64.0
    assert node.reagents_remaining == initial_reagents - 1

    # Force negative assay
    neg_res = node.run_isothermal_lamp_assay(
        target_pathogen="Vibrio cholerae O1",
        force_result="NEGATIVE"
    )
    assert neg_res["result"] == "NEGATIVE"
    assert neg_res["optical_absorbance_ratio"] < 1.0

def test_store_and_forward_offline_queue():
    node = EdgeDrainNode("TEST-ND-05", "CAT-TEST", "PHC-TEST", 26.75, 83.37)
    node.is_online = False

    node.evaluate_sample(7.2, 840.0, 180.0, 40.0, 28.0)
    node.evaluate_sample(7.1, 850.0, 175.0, 42.0, 28.2)
    assert len(node.offline_queue) == 2

    # Reconnect and flush
    node.is_online = True
    flushed = node.flush_offline_queue()
    assert len(flushed) == 2
    assert len(node.offline_queue) == 0
