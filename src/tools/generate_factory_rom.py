#!/usr/bin/env python3
"""
generate_factory_rom.py - Synthetic Factory Firmware Generator Tool for Renesas RX62T

This tool generates a 256 KB Code Flash binary image (`0xFFFC0000`–`0xFFFFFFFF`)
representing the factory firmware for the Mitsubishi Electric Ecodan PUZ-WM85VAA
outdoor unit MCU.

The generated binary contains:
  - 16-entry uint16 fan target RPM lookup table at offset 0x14120 (0xFFFD4120)
  - Unlocked 128-bit ID-code security field at offset 0x3FFA0 (0xFFFFFFA0)
  - Valid CRC-16-CCITT checksum at offset 0x3FF7E (0xFFFFFF7E)
  - Reset vector pointing to Code Flash start address (0xFFFC0000)

Supported CLI flags:
  -o, --output     Output binary file path (default: build/puz_wm85vaa_factory.bin)
  -c, --check-only Validate existing binary without writing
  -v, --verbose    Enable verbose log output
  --force          Overwrite output file if it already exists
  --endian         Byte order for LUT and checksum ('little' or 'big', default: 'little')
"""

import argparse
import sys
import os
import struct

CODE_FLASH_BASE = 0xFFFC0000
CODE_FLASH_SIZE = 256 * 1024  # 262,144 bytes

LUT_FLASH_ADDR = 0xFFFD4120
LUT_OFFSET = LUT_FLASH_ADDR - CODE_FLASH_BASE  # 0x14120
LUT_ENTRY_COUNT = 16

DEFAULT_FACTORY_RPMS = [
    300,
    400,
    500,
    600,
    700,
    780,
    850,
    900,
    950,
    1000,
    1050,
    1100,
    1150,
    1150,
    1150,
    1150,
]

ID_CODE_OFFSET = 0x3FFA0  # 0xFFFFFFA0 - 0xFFFC0000 (16 bytes)
CHECKSUM_DATA_START = 0x00000
CHECKSUM_DATA_END = 0x3FF7D  # Inclusive byte offset for checksum calculation
CHECKSUM_STORE_OFFSET = 0x3FF7E  # 2 bytes
RESET_VECTOR_OFFSET = 0x3FFFC  # 0xFFFFFFFC - 0xFFFC0000 (4 bytes)


def parse_args(args=None):
    parser = argparse.ArgumentParser(
        description="Generate synthetic factory firmware binary for Renesas RX62T MCU."
    )
    parser.add_argument(
        "-o",
        "--output",
        default="build/puz_wm85vaa_factory.bin",
        help="Path to output firmware binary (default: build/puz_wm85vaa_factory.bin)",
    )
    parser.add_argument(
        "-c",
        "--check-only",
        action="store_true",
        help="Check existing binary validity without modifying/creating files",
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Enable verbose output logging",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Force overwrite of existing output binary",
    )
    parser.add_argument(
        "--endian",
        choices=["little", "big"],
        default="little",
        help="Byte order for LUT and checksum word storage (default: little)",
    )
    return parser.parse_args(args)


def calculate_crc16_ccitt(
    data: bytes, init: int = 0xFFFF, poly: int = 0x1021
) -> int:
    crc = init
    for byte in data:
        crc ^= byte << 8
        for _ in range(8):
            if crc & 0x8000:
                crc = ((crc << 1) ^ poly) & 0xFFFF
            else:
                crc = (crc << 1) & 0xFFFF
    return crc


def build_factory_rom(endian: str = "little") -> bytearray:
    data = bytearray(b"\xFF" * CODE_FLASH_SIZE)
    fmt_h = "<H" if endian == "little" else ">H"
    fmt_i = "<I" if endian == "little" else ">I"

    # Populate 16-entry fan RPM lookup table
    for idx, rpm in enumerate(DEFAULT_FACTORY_RPMS):
        struct.pack_into(fmt_h, data, LUT_OFFSET + idx * 2, rpm)

    # Set 128-bit ID code security bytes (0xFF...FF indicates unlocked MCU)
    for i in range(16):
        data[ID_CODE_OFFSET + i] = 0xFF

    # Set Reset Vector (0xFFFFFFFC) to point to Code Flash Base (0xFFFC0000)
    struct.pack_into(fmt_i, data, RESET_VECTOR_OFFSET, CODE_FLASH_BASE)

    # Calculate and store CRC-16-CCITT checksum over non-vector ROM region
    payload = data[CHECKSUM_DATA_START : CHECKSUM_DATA_END + 1]
    crc = calculate_crc16_ccitt(payload)
    struct.pack_into(fmt_h, data, CHECKSUM_STORE_OFFSET, crc)

    return data


def generate_factory_rom(
    output_path: str = "build/puz_wm85vaa_factory.bin",
    check_only: bool = False,
    verbose: bool = False,
    force: bool = False,
    endian: str = "little",
) -> bool:
    fmt_h = "<H" if endian == "little" else ">H"

    if check_only:
        if not os.path.exists(output_path):
            print(f"Error: Binary '{output_path}' does not exist for check.", file=sys.stderr)
            return False
        with open(output_path, "rb") as f:
            data = f.read()

        if len(data) != CODE_FLASH_SIZE:
            print(
                f"Error: Binary size ({len(data)} bytes) does not match expected size ({CODE_FLASH_SIZE} bytes).",
                file=sys.stderr,
            )
            return False

        payload = data[CHECKSUM_DATA_START : CHECKSUM_DATA_END + 1]
        calc_crc = calculate_crc16_ccitt(payload)
        stored_crc = struct.unpack_from(fmt_h, data, CHECKSUM_STORE_OFFSET)[0]

        is_valid = calc_crc == stored_crc
        if verbose:
            print(f"[*] Checking binary '{output_path}':")
            print(f"    Size: {len(data)} bytes")
            print(f"    Stored CRC: 0x{stored_crc:04X}, Calculated CRC: 0x{calc_crc:04X}")
            print(f"    Checksum Valid: {is_valid}")

        return is_valid

    if os.path.exists(output_path) and not force:
        print(
            f"[*] Output binary '{output_path}' already exists. Use --force to overwrite.",
            file=sys.stdout,
        )
        return True

    out_dir = os.path.dirname(output_path)
    if out_dir:
        os.makedirs(out_dir, exist_ok=True)

    data = build_factory_rom(endian=endian)

    with open(output_path, "wb") as f:
        f.write(data)

    payload = data[CHECKSUM_DATA_START : CHECKSUM_DATA_END + 1]
    crc = calculate_crc16_ccitt(payload)

    print(f"[+] Successfully generated synthetic factory binary: '{output_path}'")
    if verbose:
        print(f"    Flash Region: 0x{CODE_FLASH_BASE:08X} - 0x{CODE_FLASH_BASE + CODE_FLASH_SIZE - 1:08X}")
        print(f"    LUT Offset: 0x{LUT_OFFSET:05X} (Addr: 0x{LUT_FLASH_ADDR:08X})")
        print(f"    Factory RPM entries: {DEFAULT_FACTORY_RPMS}")
        print(f"    Calculated CRC-16: 0x{crc:04X}")

    return True


def main():
    args = parse_args()
    success = generate_factory_rom(
        output_path=args.output,
        check_only=args.check_only,
        verbose=args.verbose,
        force=args.force,
        endian=args.endian,
    )
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
