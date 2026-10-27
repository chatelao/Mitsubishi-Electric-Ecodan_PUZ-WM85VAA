import json
import subprocess
import tempfile
import sys
import pytest
from src.tools.interceptor_sim import simulate_interceptor


def test_normal_intercept_attenuation():
    res = simulate_interceptor(vsp_in1=4.0, vsp_in2=4.0, fg_in1=50.0, fg_in2=50.0, t_evap=5.0, k=0.68)
    assert res["mode"] == "NORMAL_INTERCEPT"
    assert res["relay_bypass_active"] is False
    assert pytest.approx(res["ch1"]["vsp_out_volts"], 0.01) == 2.72
    assert pytest.approx(res["ch1"]["fg_out_freq_hz"], 0.01) == 73.53
    assert res["ch1"]["stall_detected"] is False


def test_active_stall_passthrough():
    res = simulate_interceptor(vsp_in1=2.5, vsp_in2=2.5, fg_in1=5.0, fg_in2=5.0, t_evap=10.0, k=0.68)
    assert res["mode"] == "STALL_PASSTHROUGH"
    assert res["relay_bypass_active"] is False
    assert res["ch1"]["fg_out_freq_hz"] == 0.0
    assert res["ch1"]["stall_detected"] is True


def test_freeze_override_bypass():
    res = simulate_interceptor(vsp_in1=4.0, vsp_in2=4.0, fg_in1=50.0, fg_in2=50.0, t_evap=-5.0, k=0.68)
    assert res["mode"] == "FREEZE_BYPASS"
    assert res["relay_bypass_active"] is True
    assert res["ch1"]["vsp_out_volts"] == 4.0
    assert res["ch1"]["fg_out_freq_hz"] == 50.0


def test_high_load_emergency_bypass():
    res = simulate_interceptor(vsp_in1=5.5, vsp_in2=4.0, fg_in1=80.0, fg_in2=60.0, t_evap=2.0, k=0.68)
    assert res["mode"] == "HIGH_LOAD_BYPASS"
    assert res["relay_bypass_active"] is True
    assert res["ch1"]["vsp_out_volts"] == 5.5
    assert res["ch1"]["fg_out_freq_hz"] == 80.0


def test_cli_flags_and_io():
    input_vector = {
        "vsp_in1": 3.5,
        "vsp_in2": 3.5,
        "fg_in1": 40.0,
        "fg_in2": 40.0,
        "t_evap": 12.0,
        "k": 0.68,
    }

    with tempfile.NamedTemporaryFile("w+", suffix=".json", delete=False) as infile, \
         tempfile.NamedTemporaryFile("r+", suffix=".json", delete=False) as outfile:
        json.dump(input_vector, infile)
        infile.flush()

        cmd = [
            sys.executable,
            "src/tools/interceptor_sim.py",
            "-i", infile.name,
            "-o", outfile.name,
            "-v",
        ]
        proc = subprocess.run(cmd, capture_output=True, text=True)
        assert proc.returncode == 0
        assert "Simulation Result" in proc.stdout

        outfile.seek(0)
        output_data = json.load(outfile)
        assert output_data["mode"] == "NORMAL_INTERCEPT"
        assert pytest.approx(output_data["ch1"]["vsp_out_volts"], 0.01) == 2.38


def test_cli_check_only_flag():
    input_vector = {
        "vsp_in1": 3.0,
        "vsp_in2": 3.0,
        "fg_in1": 30.0,
        "fg_in2": 30.0,
        "t_evap": 8.0,
        "k": 0.70,
    }
    vec_str = json.dumps(input_vector)
    cmd = [
        sys.executable,
        "src/tools/interceptor_sim.py",
        "-i", vec_str,
        "-c",
        "-v",
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True)
    assert proc.returncode == 0
    assert "Vector check passed successfully" in proc.stdout
