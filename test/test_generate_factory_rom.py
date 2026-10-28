import os
import struct
import pytest
from src.tools.generate_factory_rom import (
    generate_factory_rom,
    CODE_FLASH_SIZE,
    LUT_OFFSET,
    LUT_ENTRY_COUNT,
    DEFAULT_FACTORY_RPMS,
)
from src.tools.patch_fan_rpm import patch_fan_rpm
from src.tools.patch_checksum import patch_checksum


def test_generate_factory_rom_creation(tmp_path):
    output_path = str(tmp_path / "factory_rom.bin")
    success = generate_factory_rom(
        output_path=output_path, force=True, verbose=True
    )
    assert success is True
    assert os.path.exists(output_path)
    assert os.path.getsize(output_path) == CODE_FLASH_SIZE


def test_generate_factory_rom_check_only(tmp_path):
    output_path = str(tmp_path / "factory_rom.bin")
    generate_factory_rom(output_path=output_path, force=True)

    # Check validity via check_only
    is_valid = generate_factory_rom(
        output_path=output_path, check_only=True, verbose=True
    )
    assert is_valid is True


def test_factory_rom_lut_entries(tmp_path):
    output_path = str(tmp_path / "factory_rom.bin")
    generate_factory_rom(output_path=output_path, force=True)

    with open(output_path, "rb") as f:
        data = f.read()

    for i in range(LUT_ENTRY_COUNT):
        val = struct.unpack_from("<H", data, LUT_OFFSET + i * 2)[0]
        assert val == DEFAULT_FACTORY_RPMS[i]


def test_factory_rom_interoperability_with_patching(tmp_path):
    factory_bin = str(tmp_path / "factory_rom.bin")
    generate_factory_rom(output_path=factory_bin, force=True)

    # Verify initial CRC via patch_checksum tool
    assert patch_checksum(input_path=factory_bin, check_only=True) is True

    # Patch fan RPM curve
    patched_rpm_bin = str(tmp_path / "patched_rpm.bin")
    success_rpm = patch_fan_rpm(
        input_path=factory_bin,
        output_path=patched_rpm_bin,
        max_rpm=780,
        verbose=True,
    )
    assert success_rpm is True

    # Verify LUT entries are capped
    with open(patched_rpm_bin, "rb") as f:
        patched_data = f.read()

    for i in range(LUT_ENTRY_COUNT):
        val = struct.unpack_from("<H", patched_data, LUT_OFFSET + i * 2)[0]
        assert val <= 780

    # Recalculate and update CRC
    final_bin = str(tmp_path / "final_patched.bin")
    success_crc = patch_checksum(
        input_path=patched_rpm_bin, output_path=final_bin, verbose=True
    )
    assert success_crc is True
    assert patch_checksum(input_path=final_bin, check_only=True) is True
