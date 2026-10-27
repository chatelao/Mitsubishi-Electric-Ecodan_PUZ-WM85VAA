import datetime
import os
import subprocess
import sys
import pytest

from src.tools.nighttime_capper import (
    parse_time_str,
    is_nighttime,
    check_telemetry_alarm,
    generate_capping_schedule_frame,
)
from src.tools.cn105_controller import validate_packet, decode_telemetry


def test_parse_time_str():
    t1 = parse_time_str("22:00")
    assert t1 == datetime.time(22, 0)

    t2 = parse_time_str("07:30")
    assert t2 == datetime.time(7, 30)

    with pytest.raises(ValueError):
        parse_time_str("invalid")

    with pytest.raises(ValueError):
        parse_time_str("25:00")


def test_is_nighttime():
    start = datetime.time(22, 0)
    end = datetime.time(7, 0)

    # Midnight wrapping window (22:00 - 07:00)
    assert is_nighttime(datetime.time(22, 0), start, end) is True
    assert is_nighttime(datetime.time(23, 59), start, end) is True
    assert is_nighttime(datetime.time(0, 0), start, end) is True
    assert is_nighttime(datetime.time(6, 59), start, end) is True

    assert is_nighttime(datetime.time(7, 0), start, end) is False
    assert is_nighttime(datetime.time(12, 0), start, end) is False
    assert is_nighttime(datetime.time(21, 59), start, end) is False

    # Non-wrapping window (01:00 - 05:00)
    start_day = datetime.time(1, 0)
    end_day = datetime.time(5, 0)
    assert is_nighttime(datetime.time(2, 30), start_day, end_day) is True
    assert is_nighttime(datetime.time(0, 30), start_day, end_day) is False
    assert is_nighttime(datetime.time(5, 0), start_day, end_day) is False


def test_generate_capping_schedule_frame():
    start = datetime.time(22, 0)
    end = datetime.time(7, 0)

    # Nighttime at 23:00 -> 75% cap
    frame_night, in_night = generate_capping_schedule_frame(
        datetime.time(23, 0), start, end, demand_cap=75
    )
    assert in_night is True
    assert validate_packet(frame_night) is True
    assert frame_night[5] == 0x01  # Enabled
    assert frame_night[6] == 0x4B  # 75%

    # Daytime at 14:00 -> 100% cap / disabled
    frame_day, in_day = generate_capping_schedule_frame(
        datetime.time(14, 0), start, end, demand_cap=75
    )
    assert in_day is False
    assert validate_packet(frame_day) is True
    assert frame_day[5] == 0x00  # Disabled
    assert frame_day[6] == 0x64  # 100%


def test_check_telemetry_alarm():
    telemetry_ok = {"compressor_freq_hz": 40, "alarm_code": 0}
    assert check_telemetry_alarm(telemetry_ok) is True

    telemetry_err = {"compressor_freq_hz": 0, "alarm_code": 0x1A}
    assert check_telemetry_alarm(telemetry_err) is False

    assert check_telemetry_alarm({}) is False


def test_cli_execution_nighttime(tmp_path):
    out_file = tmp_path / "night_frame.bin"
    cmd = [
        sys.executable,
        "src/tools/nighttime_capper.py",
        "-o",
        str(out_file),
        "--time",
        "23:30",
        "--start-time",
        "22:00",
        "--end-time",
        "07:00",
        "--demand-cap",
        "75",
        "-v",
    ]
    res = subprocess.run(cmd, capture_output=True, text=True)
    assert res.returncode == 0
    assert os.path.exists(out_file)

    with open(out_file, "rb") as f:
        data = f.read()
    assert validate_packet(data) is True
    assert data[5] == 0x01  # Enabled
    assert data[6] == 0x4B  # 75%


def test_cli_execution_daytime(tmp_path):
    out_file = tmp_path / "day_frame.bin"
    cmd = [
        sys.executable,
        "src/tools/nighttime_capper.py",
        "-o",
        str(out_file),
        "--time",
        "12:00",
        "--start-time",
        "22:00",
        "--end-time",
        "07:00",
        "--demand-cap",
        "75",
        "-v",
    ]
    res = subprocess.run(cmd, capture_output=True, text=True)
    assert res.returncode == 0
    assert os.path.exists(out_file)

    with open(out_file, "rb") as f:
        data = f.read()
    assert validate_packet(data) is True
    assert data[5] == 0x00  # Disabled / 100%
    assert data[6] == 0x64


def test_cli_check_only(tmp_path):
    cmd = [
        sys.executable,
        "src/tools/nighttime_capper.py",
        "-c",
        "--time",
        "23:00",
        "-v",
    ]
    res = subprocess.run(cmd, capture_output=True, text=True)
    assert res.returncode == 0
    assert "Nighttime Active: True" in res.stdout
