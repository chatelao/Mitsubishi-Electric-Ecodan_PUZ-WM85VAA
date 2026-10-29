#!/usr/bin/env python3
"""
verify_id_code.py - Renesas RX62T ID-Code Security Field Probing Tool

This tool inspects, verifies, and manages the 128-bit ID-Code security protection
field located at flash address `0xFFFFFFA0` (offset `0x3FFA0` in 256 KB Code Flash).

MCU Security Protection States:
  - Unlocked: All 16 bytes are 0xFF (0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFF).
    SCI boot mode readout and JTAG debugger connection permitted.
  - Locked / Armed: Any byte is not 0xFF. SCI boot mode connections without matching
    key result in flash erasure or serial communication lockout.

Supported CLI flags:
  -i, --input      Input firmware binary or dump file path
  -o, --output     Output binary file path (if writing new ID code key)
  -c, --check-only Verify ID-code protection state without modifying binary
  -v, --verbose    Enable verbose log output
  --key            16-byte hex string (32 hex chars) key to validate or set
"""

import argparse
import os
import sys

CODE_FLASH_BASE = 0xFFFC0000
ID_CODE_FLASH_ADDR = 0xFFFFFFA0
ID_CODE_OFFSET = ID_CODE_FLASH_ADDR - CODE_FLASH_BASE  # 0x3FFA0
ID_CODE_LEN = 16  # 128 bits
UNLOCKED_ID_CODE = b"\xFF" * ID_CODE_LEN
MIN_FIRMWARE_SIZE = ID_CODE_OFFSET + ID_CODE_LEN  # 262,064 bytes (0x3FFB0)


def parse_args(args=None):
    parser = argparse.ArgumentParser(
        description="Inspect and verify 128-bit ID-Code security protection field for Renesas RX62T."
    )
    parser.add_argument(
        "-i", "--input", required=True, help="Path to input firmware binary or ROM dump"
    )
    parser.add_argument(
        "-o", "--output", help="Path to output binary with updated ID-code protection field"
    )
    parser.add_argument(
        "-c",
        "--check-only",
        action="store_true",
        help="Validate ID-code protection state without modifying binary",
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Enable verbose output logging",
    )
    parser.add_argument(
        "--key",
        type=str,
        help="32-character hex key string (16 bytes) to validate against or set",
    )
    return parser.parse_args(args)


def parse_hex_key(key_str: str) -> bytes:
    """Parse a 32-character hex string into 16 bytes."""
    clean_key = key_str.replace(" ", "").replace("0x", "").replace(":", "")
    if len(clean_key) != 32:
        raise ValueError(
            f"Key hex string must be 32 characters long (16 bytes), got {len(clean_key)} characters."
        )
    return bytes.fromhex(clean_key)


def verify_id_code(
    input_path: str,
    output_path: str = None,
    check_only: bool = False,
    verbose: bool = False,
    key: str = None,
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

    current_id_code = data[ID_CODE_OFFSET : ID_CODE_OFFSET + ID_CODE_LEN]
    is_unlocked = current_id_code == UNLOCKED_ID_CODE

    expected_key_bytes = None
    if key:
        try:
            expected_key_bytes = parse_hex_key(key)
        except ValueError as ve:
            print(f"Error: Invalid --key argument: {ve}", file=sys.stderr)
            return False

    if verbose:
        print(f"[*] Input Binary: '{input_path}' ({len(data)} bytes)")
        print(
            f"[*] ID-Code Location: 0x{ID_CODE_OFFSET:05X} (ROM Address: 0x{ID_CODE_FLASH_ADDR:08X})"
        )
        print(f"[*] Read ID-Code Hex: {current_id_code.hex().upper()}")
        print(f"[*] Protection Status: {'UNLOCKED (All 0xFF)' if is_unlocked else 'LOCKED / ARMED'}")

    if check_only:
        print(f"[*] Renesas RX62T ID-Code Protection Gate Check:")
        print(f"    Raw ID-Code: {current_id_code.hex().upper()}")
        if is_unlocked:
            print("    Status: UNLOCKED - SCI boot mode and JTAG debugging permitted.")
        else:
            print(
                "    Status: LOCKED / ARMED - Key required for SCI connection. Readout check mandatory."
            )

        if expected_key_bytes:
            matches_key = current_id_code == expected_key_bytes
            print(
                f"    Key Match ({expected_key_bytes.hex().upper()}): {'MATCH' if matches_key else 'MISMATCH'}"
            )
            return matches_key

        return is_unlocked

    # If --key is provided and output_path (or in-place modification) is intended
    if expected_key_bytes:
        if current_id_code == expected_key_bytes:
            print(f"[*] ID-Code already matches key ({expected_key_bytes.hex().upper()}). No change required.")
            if output_path and output_path != input_path:
                with open(output_path, "wb") as f:
                    f.write(data)
                if verbose:
                    print(f"[*] Output copied to '{output_path}'.")
            return True

        out_data = bytearray(data)
        out_data[ID_CODE_OFFSET : ID_CODE_OFFSET + ID_CODE_LEN] = expected_key_bytes

        target_out = output_path if output_path else input_path
        with open(target_out, "wb") as f:
            f.write(out_data)

        print(
            f"[+] Successfully updated ID-code field to {expected_key_bytes.hex().upper()}."
        )
        if verbose:
            print(f"    Written to: '{target_out}'")
        return True

    # If no key provided and check_only is False
    if is_unlocked:
        print("[*] MCU ID-code field is UNLOCKED.")
        if output_path and output_path != input_path:
            with open(output_path, "wb") as f:
                f.write(data)
            if verbose:
                print(f"[*] Output copied to '{output_path}'.")
        return True
    else:
        print(
            f"[!] WARNING: MCU ID-code is LOCKED ({current_id_code.hex().upper()}). Provide --key to match or update.",
            file=sys.stderr,
        )
        return False


def main():
    args = parse_args()
    success = verify_id_code(
        input_path=args.input,
        output_path=args.output,
        check_only=args.check_only,
        verbose=args.verbose,
        key=args.key,
    )
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
