"""
test_ghidra_init.py - Unit Test Suite for Ghidra RX62T Decompiler Initializer
"""

import json
import os
import subprocess
import sys
import tempfile
import pytest

from src.firmware.ghidra_init_rx62t import (
    get_memory_layout,
    verify_memory_layout,
    validate_input_binary,
    MEMORY_BLOCKS,
    SYMBOLS,
)


def test_memory_layout_structure():
    layout = get_memory_layout()
    assert layout["processor"] == "Renesas RX62T (R5F562TxxDFP)"
    assert len(layout["memory_blocks"]) == 5
    assert len(layout["symbols"]) == 6


def test_verify_memory_layout():
    assert verify_memory_layout() is True


def test_memory_blocks_and_symbol_addresses():
    # Verify SRAM bounds
    sram = next(b for b in MEMORY_BLOCKS if b["name"] == "SRAM")
    assert sram["start"] == 0x00000000
    assert sram["size"] == 16384

    # Verify Code Flash bounds
    code_flash = next(b for b in MEMORY_BLOCKS if b["name"] == "CODE_FLASH")
    assert code_flash["start"] == 0xFFFC0000

    # Verify Fixed Vectors bounds
    fixed_vectors = next(b for b in MEMORY_BLOCKS if b["name"] == "FIXED_VECTORS")
    assert fixed_vectors["start"] == 0xFFFFFF80
    assert fixed_vectors["size"] == 128

    # Verify LUT symbol
    assert SYMBOLS["FAN_TARGET_RPM_LUT"]["address"] == 0xFFFD4120
    # Verify ID code security symbol
    assert SYMBOLS["ID_CODE_SECURITY_FIELD"]["address"] == 0xFFFFFFA0
    # Verify Reset Vector symbol
    assert SYMBOLS["RESET_VECTOR"]["address"] == 0xFFFFFFFC


def test_validate_input_binary():
    # Existing factory binary in build/ if present or create temporary 256 KB binary
    with tempfile.NamedTemporaryFile(suffix=".bin", delete=False) as tmp:
        tmp.write(b"\xFF" * (256 * 1024))
        tmp_path = tmp.name

    try:
        assert validate_input_binary(tmp_path) is True
    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)

    # Invalid binary size
    with tempfile.NamedTemporaryFile(suffix=".bin", delete=False) as tmp:
        tmp.write(b"\xFF" * 1024)
        tmp_path_invalid = tmp.name

    try:
        assert validate_input_binary(tmp_path_invalid) is False
    finally:
        if os.path.exists(tmp_path_invalid):
            os.remove(tmp_path_invalid)

    # Non-existent file
    assert validate_input_binary("non_existent_file.bin") is False


def test_cli_check_only():
    cmd = [
        sys.executable,
        "src/firmware/ghidra_init_rx62t.py",
        "-c",
        "-v",
    ]
    res = subprocess.run(cmd, capture_output=True, text=True)
    assert res.returncode == 0
    assert "Memory layout configuration valid" in res.stdout


def test_cli_export_json():
    with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as tmp:
        out_path = tmp.name

    try:
        cmd = [
            sys.executable,
            "src/firmware/ghidra_init_rx62t.py",
            "-o",
            out_path,
            "-v",
        ]
        res = subprocess.run(cmd, capture_output=True, text=True)
        assert res.returncode == 0
        assert os.path.exists(out_path)

        with open(out_path, "r") as f:
            data = json.load(f)
        assert data["processor"] == "Renesas RX62T (R5F562TxxDFP)"
    finally:
        if os.path.exists(out_path):
            os.remove(out_path)
