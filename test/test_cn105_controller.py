import os
import subprocess
import sys
import pytest
from src.tools.cn105_controller import (
    build_demand_cap_packet,
    calculate_checksum,
    validate_packet,
    decode_telemetry,
)


def test_calculate_checksum():
    # Example body: 52 42 05 02 0B 01 4B 00
    body = bytes([0x52, 0x42, 0x05, 0x02, 0x0B, 0x01, 0x4B, 0x00])
    # sum = 0x52+0x42+0x05+0x02+0x0B+0x01+0x4B+0x00 = 0xF2 (242)
    # cs = (0x100 - 0xF2) & 0xFF = 0x0E (14)
    cs = calculate_checksum(body)
    assert cs == 0x0E
    assert (sum(body) + cs) % 256 == 0


def test_build_demand_cap_packet():
    frame_50 = build_demand_cap_packet(cap_pct=50, enable=True)
    assert len(frame_50) == 9
    assert frame_50[0] == 0x52
    assert frame_50[1] == 0x42
    assert frame_50[2] == 0x05  # Payload length
    assert frame_50[3] == 0x02  # Cmd
    assert frame_50[4] == 0x0B  # Fn
    assert frame_50[5] == 0x01  # Enable
    assert frame_50[6] == 0x32  # 50% = 0x32
    assert validate_packet(frame_50) is True

    frame_75 = build_demand_cap_packet(cap_pct=75, enable=True)
    assert frame_75[6] == 0x4B  # 75% = 0x4B
    assert validate_packet(frame_75) is True

    frame_100 = build_demand_cap_packet(cap_pct=100, enable=False)
    assert frame_100[5] == 0x00  # Disable
    assert frame_100[6] == 0x64  # 100% = 0x64
    assert validate_packet(frame_100) is True


def test_validate_packet_invalid():
    # Corrupted checksum
    frame = bytearray(build_demand_cap_packet(75))
    frame[-1] ^= 0xFF
    assert validate_packet(bytes(frame)) is False

    # Short frame
    assert validate_packet(bytes([0x52, 0x42])) is False


def test_decode_telemetry():
    # Construct a synthetic telemetry response packet:
    # Sync1(52), Sync2(61), Len(09), Cmd(07), Regs: [10(freq)=45, 12(evap)=48(+8C), 15(sh)=35(3.5K), 1A(fan)=4]
    payload = bytes([0x07, 0x10, 45, 0x12, 48, 0x15, 35, 0x1A, 4])
    header = bytes([0x52, 0x61, len(payload)])
    body = header + payload
    cs = calculate_checksum(body)
    frame = body + bytes([cs])

    assert validate_packet(frame) is True
    telemetry = decode_telemetry(frame)
    assert telemetry["compressor_freq_hz"] == 45
    assert telemetry["evap_temp_c"] == 8  # 48 - 40 = 8
    assert telemetry["superheat_k"] == 3.5  # 35 / 10 = 3.5
    assert telemetry["fan_speed_step"] == 4


def test_cli_execution(tmp_path):
    out_file = tmp_path / "packet.bin"
    cmd = [
        sys.executable,
        "src/tools/cn105_controller.py",
        "-o",
        str(out_file),
        "--demand-cap",
        "75",
        "-v",
    ]
    res = subprocess.run(cmd, capture_output=True, text=True)
    assert res.returncode == 0
    assert os.path.exists(out_file)

    # Validate output with -c/--check-only
    check_cmd = [
        sys.executable,
        "src/tools/cn105_controller.py",
        "-i",
        str(out_file),
        "-c",
        "-v",
    ]
    check_res = subprocess.run(check_cmd, capture_output=True, text=True)
    assert check_res.returncode == 0
    assert "VALID" in check_res.stdout
