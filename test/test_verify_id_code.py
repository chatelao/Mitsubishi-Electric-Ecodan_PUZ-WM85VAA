import os
import pytest
from src.tools.verify_id_code import (
    verify_id_code,
    parse_hex_key,
    ID_CODE_OFFSET,
    ID_CODE_LEN,
    UNLOCKED_ID_CODE,
)

FIRMWARE_SIZE = 256 * 1024  # 256 KB Code Flash binary


@pytest.fixture
def factory_firmware(tmp_path):
    firmware_path = tmp_path / "factory_rom.bin"
    data = bytearray(b"\xFF" * FIRMWARE_SIZE)
    with open(firmware_path, "wb") as f:
        f.write(data)
    return str(firmware_path)


@pytest.fixture
def locked_firmware(tmp_path):
    firmware_path = tmp_path / "locked_rom.bin"
    data = bytearray(b"\xFF" * FIRMWARE_SIZE)
    # Set locked ID code: "45434F44414E5F50555A5F574D383556"
    custom_key = bytes.fromhex("45434F44414E5F50555A5F574D383556")
    data[ID_CODE_OFFSET : ID_CODE_OFFSET + ID_CODE_LEN] = custom_key
    with open(firmware_path, "wb") as f:
        f.write(data)
    return str(firmware_path)


def test_unlocked_id_code_check(factory_firmware, capsys):
    success = verify_id_code(
        input_path=factory_firmware, check_only=True, verbose=True
    )
    assert success is True
    captured = capsys.readouterr().out
    assert "UNLOCKED" in captured


def test_locked_id_code_check(locked_firmware, capsys):
    success = verify_id_code(
        input_path=locked_firmware, check_only=True, verbose=True
    )
    assert success is False
    captured = capsys.readouterr().out
    assert "LOCKED / ARMED" in captured


def test_key_matching(locked_firmware, capsys):
    key_hex = "45434F44414E5F50555A5F574D383556"
    success = verify_id_code(
        input_path=locked_firmware, check_only=True, key=key_hex, verbose=True
    )
    assert success is True
    captured = capsys.readouterr().out
    assert "MATCH" in captured


def test_key_mismatch(locked_firmware):
    wrong_key_hex = "11223344556677889900AABBCCDDEEFF"
    success = verify_id_code(
        input_path=locked_firmware, check_only=True, key=wrong_key_hex
    )
    assert success is False


def test_update_id_code_key(factory_firmware, tmp_path):
    output_path = str(tmp_path / "custom_id_rom.bin")
    new_key_hex = "00112233445566778899AABBCCDDEEFF"
    success = verify_id_code(
        input_path=factory_firmware,
        output_path=output_path,
        key=new_key_hex,
        verbose=True,
    )
    assert success is True
    assert os.path.exists(output_path)

    # Verify that updated binary now matches new_key_hex
    verified = verify_id_code(
        input_path=output_path, check_only=True, key=new_key_hex
    )
    assert verified is True


def test_parse_hex_key_valid_and_invalid():
    valid_key = parse_hex_key("0x00112233445566778899AABBCCDDEEFF")
    assert len(valid_key) == 16
    assert valid_key == bytes.fromhex("00112233445566778899AABBCCDDEEFF")

    with pytest.raises(ValueError):
        parse_hex_key("TOO_SHORT")


def test_missing_and_short_file(tmp_path):
    assert verify_id_code(input_path=str(tmp_path / "non_existent.bin")) is False

    short_file = tmp_path / "short.bin"
    short_file.write_bytes(b"\xFF" * 100)
    assert verify_id_code(input_path=str(short_file)) is False
