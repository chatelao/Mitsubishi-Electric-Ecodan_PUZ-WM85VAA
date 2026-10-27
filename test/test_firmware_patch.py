import os
import struct
import pytest
from src.tools.patch_fan_rpm import patch_fan_rpm, LUT_OFFSET, LUT_ENTRY_COUNT
from src.tools.patch_checksum import (
    patch_checksum,
    calculate_crc16_ccitt,
    CHECKSUM_DATA_START,
    CHECKSUM_DATA_END,
    CHECKSUM_STORE_OFFSET,
    MIN_FIRMWARE_SIZE,
)

FIRMWARE_SIZE = 256 * 1024  # 256 KB Code Flash binary


@pytest.fixture
def dummy_firmware(tmp_path):
    firmware_path = tmp_path / "factory_firmware.bin"
    data = bytearray(b"\xFF" * FIRMWARE_SIZE)

    # Populate synthetic LUT entries at LUT_OFFSET (0x14120)
    # Default unpatched RPM entries (some exceeding 780 RPM up to 1150 RPM)
    factory_rpms = [
        300, 400, 500, 600, 700, 780, 850, 900,
        950, 1000, 1050, 1100, 1150, 1150, 1150, 1150
    ]
    for idx, rpm in enumerate(factory_rpms):
        struct.pack_into("<H", data, LUT_OFFSET + idx * 2, rpm)

    # Calculate initial CRC-16 over non-vector code flash region
    payload = data[CHECKSUM_DATA_START : CHECKSUM_DATA_END + 1]
    crc = calculate_crc16_ccitt(payload)
    struct.pack_into("<H", data, CHECKSUM_STORE_OFFSET, crc)

    with open(firmware_path, "wb") as f:
        f.write(data)

    return str(firmware_path)


def test_patch_fan_rpm_check_only(dummy_firmware, capsys):
    success = patch_fan_rpm(
        input_path=dummy_firmware, check_only=True, verbose=True, max_rpm=780
    )
    assert success is True
    captured = capsys.readouterr().out
    assert "Entries exceeding max RPM (780): 10" in captured


def test_patch_fan_rpm_modification(dummy_firmware, tmp_path):
    output_path = str(tmp_path / "patched_firmware.bin")
    success = patch_fan_rpm(
        input_path=dummy_firmware,
        output_path=output_path,
        max_rpm=780,
        verbose=True,
    )
    assert success is True
    assert os.path.exists(output_path)

    # Read back patched entries
    with open(output_path, "rb") as f:
        patched_data = f.read()

    for i in range(LUT_ENTRY_COUNT):
        val = struct.unpack_from("<H", patched_data, LUT_OFFSET + i * 2)[0]
        assert val <= 780

    # Ensure checking already patched binary indicates no changes needed
    success_recheck = patch_fan_rpm(
        input_path=output_path, check_only=True, max_rpm=780
    )
    assert success_recheck is True


def test_patch_checksum_verification(dummy_firmware):
    # Verify factory dummy firmware checksum
    valid = patch_checksum(input_path=dummy_firmware, check_only=True, verbose=True)
    assert valid is True


def test_patch_checksum_after_rpm_patch(dummy_firmware, tmp_path):
    output_rpm_patched = str(tmp_path / "firmware_rpm_patched.bin")
    patch_fan_rpm(
        input_path=dummy_firmware, output_path=output_rpm_patched, max_rpm=780
    )

    # Checksum should now be invalid before patch_checksum is called
    assert patch_checksum(input_path=output_rpm_patched, check_only=True) is False

    # Patch checksum
    final_output = str(tmp_path / "firmware_final.bin")
    success = patch_checksum(
        input_path=output_rpm_patched, output_path=final_output, verbose=True
    )
    assert success is True

    # Checksum should now be valid
    assert patch_checksum(input_path=final_output, check_only=True) is True
