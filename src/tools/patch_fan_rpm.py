#!/usr/bin/env python3
"""
patch_fan_rpm.py - Target Fan RPM Lookup Table Patching Tool

This tool inspects and patches the target fan RPM lookup table within the
Renesas RX62T outdoor unit firmware binary (`0xFFFC0000`–`0xFFFFFFFF`).
Offset `0x14120` corresponds to flash address `0xFFFD4120`.

Supported CLI flags:
  -i, --input      Input firmware binary file path
  -o, --output     Output patched binary file path
  -c, --check-only Validate and inspect LUT without modifying binary
  -v, --verbose    Enable verbose log output
  --max-rpm        Maximum allowed fan RPM cap (default: 780)
  --endian         Byte order of uint16 LUT entries ('little' or 'big', default: 'little')
"""

import argparse
import sys
import os

CODE_FLASH_BASE = 0xFFFC0000
LUT_FLASH_ADDR = 0xFFFD4120
LUT_OFFSET = LUT_FLASH_ADDR - CODE_FLASH_BASE  # 0x14120
LUT_ENTRY_COUNT = 16  # 16-entry 16-bit array representing fan target RPM matrix


def parse_args(args=None):
    parser = argparse.ArgumentParser(
        description="Patch target fan RPM lookup table in Renesas RX62T firmware binary."
    )
    parser.add_argument(
        "-i", "--input", required=True, help="Path to input firmware binary"
    )
    parser.add_argument(
        "-o", "--output", help="Path to output patched firmware binary"
    )
    parser.add_argument(
        "-c",
        "--check-only",
        action="store_true",
        help="Check and display LUT entries without modifying binary",
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Enable verbose output logging",
    )
    parser.add_argument(
        "--max-rpm",
        type=int,
        default=780,
        help="Maximum target fan RPM ceiling (default: 780)",
    )
    parser.add_argument(
        "--endian",
        choices=["little", "big"],
        default="little",
        help="Byte order of uint16 LUT entries (default: little)",
    )
    return parser.parse_args(args)


def read_lut(data: bytes, offset: int, count: int, endian: str) -> list[int]:
    entries = []
    byte_order = "little" if endian == "little" else "big"
    for i in range(count):
        entry_offset = offset + i * 2
        val = int.from_bytes(data[entry_offset : entry_offset + 2], byteorder=byte_order)
        entries.append(val)
    return entries


def write_lut(data: bytearray, offset: int, entries: list[int], endian: str) -> None:
    byte_order = "little" if endian == "little" else "big"
    for i, val in enumerate(entries):
        entry_offset = offset + i * 2
        data[entry_offset : entry_offset + 2] = val.to_bytes(2, byteorder=byte_order)


def patch_fan_rpm(
    input_path: str,
    output_path: str = None,
    check_only: bool = False,
    verbose: bool = False,
    max_rpm: int = 780,
    endian: str = "little",
) -> bool:
    if not os.path.exists(input_path):
        print(f"Error: Input file '{input_path}' not found.", file=sys.stderr)
        return False

    with open(input_path, "rb") as f:
        data = f.read()

    if len(data) < LUT_OFFSET + LUT_ENTRY_COUNT * 2:
        print(
            f"Error: Input binary size ({len(data)} bytes) is too small for LUT offset 0x{LUT_OFFSET:X}.",
            file=sys.stderr,
        )
        return False

    entries = read_lut(data, LUT_OFFSET, LUT_ENTRY_COUNT, endian)

    if verbose:
        print(f"[*] Reading LUT at offset 0x{LUT_OFFSET:X} (Addr: 0x{LUT_FLASH_ADDR:X}):")
        for idx, rpm in enumerate(entries):
            print(f"    Entry [{idx:02d}]: {rpm} RPM")

    patched_entries = []
    changes_count = 0
    for rpm in entries:
        if rpm > max_rpm:
            patched_entries.append(max_rpm)
            changes_count += 1
        else:
            patched_entries.append(rpm)

    is_patched = changes_count == 0 and any(rpm == max_rpm for rpm in entries)

    if check_only:
        print(f"[*] LUT Check at 0x{LUT_FLASH_ADDR:X}:")
        print(f"    Original RPM values: {entries}")
        print(f"    Entries exceeding max RPM ({max_rpm}): {changes_count}")
        if changes_count == 0:
            print("    Status: Binary is already capped/patched or within max RPM limits.")
        else:
            print("    Status: Binary contains entries exceeding max RPM ceiling.")
        return True

    if changes_count == 0:
        print(f"[*] No entries exceed max RPM ceiling ({max_rpm} RPM). No patching required.")
        if output_path and output_path != input_path:
            with open(output_path, "wb") as f:
                f.write(data)
            if verbose:
                print(f"[*] Output copied to '{output_path}'.")
        return True

    out_data = bytearray(data)
    write_lut(out_data, LUT_OFFSET, patched_entries, endian)

    target_out = output_path if output_path else input_path
    with open(target_out, "wb") as f:
        f.write(out_data)

    print(
        f"[+] Successfully patched {changes_count} LUT entries to {max_rpm} RPM ceiling."
    )
    if verbose:
        print(f"    Patched LUT values: {patched_entries}")
        print(f"    Written to: '{target_out}'")

    return True


def main():
    args = parse_args()
    success = patch_fan_rpm(
        input_path=args.input,
        output_path=args.output,
        check_only=args.check_only,
        verbose=args.verbose,
        max_rpm=args.max_rpm,
        endian=args.endian,
    )
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
