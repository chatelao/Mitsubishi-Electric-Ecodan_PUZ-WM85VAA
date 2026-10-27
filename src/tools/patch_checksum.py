#!/usr/bin/env python3
"""
patch_checksum.py - Renesas RX62T Firmware CRC-16 Checksum Patching Tool

This tool calculates and updates the CRC-16-CCITT checksum over the non-vector
code flash ROM (`0xFFFC0000`–`0xFFFFFF7D`, offset `0x00000`–`0x3FF7D`) and writes
the 16-bit result at offset `0x3FF7E` (ROM address `0xFFFFFF7E`).

Supported CLI flags:
  -i, --input      Input firmware binary file path
  -o, --output     Output patched binary file path
  -c, --check-only Verify checksum without modifying binary
  -v, --verbose    Enable verbose log output
  --endian         Byte order of checksum entry ('little' or 'big', default: 'little')
"""

import argparse
import sys
import os

CHECKSUM_DATA_START = 0x00000
CHECKSUM_DATA_END = 0x3FF7D  # Inclusive byte offset for checksum calculation
CHECKSUM_STORE_OFFSET = 0x3FF7E  # 2 bytes at end of non-vector ROM
MIN_FIRMWARE_SIZE = CHECKSUM_STORE_OFFSET + 2  # 262,016 bytes (0x3FF80)


def parse_args(args=None):
    parser = argparse.ArgumentParser(
        description="Calculate and patch CRC-16-CCITT checksum for Renesas RX62T firmware binary."
    )
    parser.add_argument(
        "-i", "--input", required=True, help="Path to input firmware binary"
    )
    parser.add_argument(
        "-o", "--output", help="Path to output firmware binary with patched checksum"
    )
    parser.add_argument(
        "-c",
        "--check-only",
        action="store_true",
        help="Validate existing ROM checksum without modifying binary",
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Enable verbose output logging",
    )
    parser.add_argument(
        "--endian",
        choices=["little", "big"],
        default="little",
        help="Byte order for checksum word storage (default: little)",
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


def patch_checksum(
    input_path: str,
    output_path: str = None,
    check_only: bool = False,
    verbose: bool = False,
    endian: str = "little",
) -> bool:
    if not os.path.exists(input_path):
        print(f"Error: Input file '{input_path}' not found.", file=sys.stderr)
        return False

    with open(input_path, "rb") as f:
        data = f.read()

    if len(data) < MIN_FIRMWARE_SIZE:
        print(
            f"Error: Input binary size ({len(data)} bytes) is smaller than required minimum ({MIN_FIRMWARE_SIZE} bytes).",
            file=sys.stderr,
        )
        return False

    rom_payload = data[CHECKSUM_DATA_START : CHECKSUM_DATA_END + 1]
    calculated_crc = calculate_crc16_ccitt(rom_payload)

    byte_order = "little" if endian == "little" else "big"
    stored_crc_bytes = data[CHECKSUM_STORE_OFFSET : CHECKSUM_STORE_OFFSET + 2]
    stored_crc = int.from_bytes(stored_crc_bytes, byteorder=byte_order)

    if verbose:
        print(f"[*] Firmware Size: {len(data)} bytes")
        print(
            f"[*] Checksum Data Region: 0x{CHECKSUM_DATA_START:05X} - 0x{CHECKSUM_DATA_END:05X} ({len(rom_payload)} bytes)"
        )
        print(f"[*] Stored CRC-16 (Offset 0x{CHECKSUM_STORE_OFFSET:05X}): 0x{stored_crc:04X}")
        print(f"[*] Calculated CRC-16-CCITT: 0x{calculated_crc:04X}")

    is_valid = stored_crc == calculated_crc

    if check_only:
        print(f"[*] CRC-16 Checksum Verification:")
        print(f"    Stored CRC:     0x{stored_crc:04X}")
        print(f"    Calculated CRC: 0x{calculated_crc:04X}")
        if is_valid:
            print("    Status: CHECKSUM VALID")
        else:
            print("    Status: CHECKSUM INVALID (Mismatch)")
        return is_valid

    if is_valid:
        print(f"[*] Checksum is already valid (0x{calculated_crc:04X}). No patching required.")
        if output_path and output_path != input_path:
            with open(output_path, "wb") as f:
                f.write(data)
            if verbose:
                print(f"[*] Output copied to '{output_path}'.")
        return True

    out_data = bytearray(data)
    out_data[CHECKSUM_STORE_OFFSET : CHECKSUM_STORE_OFFSET + 2] = calculated_crc.to_bytes(
        2, byteorder=byte_order
    )

    target_out = output_path if output_path else input_path
    with open(target_out, "wb") as f:
        f.write(out_data)

    print(
        f"[+] Successfully updated CRC-16 checksum from 0x{stored_crc:04X} to 0x{calculated_crc:04X}."
    )
    if verbose:
        print(f"    Written to: '{target_out}'")

    return True


def main():
    args = parse_args()
    success = patch_checksum(
        input_path=args.input,
        output_path=args.output,
        check_only=args.check_only,
        verbose=args.verbose,
        endian=args.endian,
    )
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
