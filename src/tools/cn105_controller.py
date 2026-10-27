#!/usr/bin/env python3
"""
cn105_controller.py - FTC6 Indoor CN105 Serial Protocol & Capping Tool

This tool generates, validates, and decodes CN105 serial packets for the
FTC6 (Flow Temperature Controller 6) interface. It supports generating
demand capping / night mode packets as well as parsing telemetry response frames.

Supported CLI flags:
  -i, --input          Input binary file or hex string containing CN105 frame(s)
  -o, --output         Output binary file path to write generated or modified packet
  -c, --check-only     Validate packet checksums and structure without writing output
  -v, --verbose        Enable verbose log output
  --demand-cap         Demand cap percentage (50, 75, 100)
  --enable-demand      Enable demand limit / night mode (default: 1)
  --decode-telemetry   Decode input packet as telemetry response
"""

import argparse
import sys
import os

SYNC1_REQ = 0x52  # 'R'
SYNC1_ALT = 0xFC
SYNC2_REQ = 0x42  # Request
SYNC2_RESP = 0x61  # Response

CMD_SET = 0x02
CMD_GET = 0x03
CMD_TELEMETRY = 0x07

FN_NIGHT_DEMAND_CAP = 0x0B


def calculate_checksum(data: bytes) -> int:
    """Calculate CN105 byte summation checksum."""
    total = sum(data) % 256
    return (0x100 - total) & 0xFF


def parse_args(args=None):
    parser = argparse.ArgumentParser(
        description="FTC6 CN105 serial interface packet generator and decoder."
    )
    parser.add_argument(
        "-i",
        "--input",
        help="Input binary file path or hex string containing CN105 frame",
    )
    parser.add_argument(
        "-o",
        "--output",
        help="Output binary file path to save generated or processed frame",
    )
    parser.add_argument(
        "-c",
        "--check-only",
        action="store_true",
        help="Validate input frame checksum and structure without modifying or creating files",
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Enable verbose output logging",
    )
    parser.add_argument(
        "--demand-cap",
        type=int,
        choices=[50, 75, 100],
        help="Set demand cap percentage level (50%%, 75%%, 100%%)",
    )
    parser.add_argument(
        "--enable-demand",
        type=int,
        choices=[0, 1],
        default=1,
        help="Enable (1) or disable (0) demand limit mode (default: 1)",
    )
    parser.add_argument(
        "--decode-telemetry",
        action="store_true",
        help="Decode input frame as telemetry response",
    )
    return parser.parse_args(args)


def build_demand_cap_packet(cap_pct: int = 75, enable: bool = True) -> bytes:
    """
    Construct a CN105 Demand Capping frame (Command 0x02, Function 0x0B).
    cap_pct: 50 -> 0x32, 75 -> 0x4B, 100 -> 0x64.
    """
    pct_map = {50: 0x32, 75: 0x4B, 100: 0x64}
    cap_byte = pct_map.get(cap_pct, 0x4B)
    enable_byte = 0x01 if enable else 0x00

    payload = bytes([CMD_SET, FN_NIGHT_DEMAND_CAP, enable_byte, cap_byte, 0x00])
    header = bytes([SYNC1_REQ, SYNC2_REQ, len(payload)])
    frame_body = header + payload
    cs = calculate_checksum(frame_body)
    return frame_body + bytes([cs])


def validate_packet(frame: bytes, verbose: bool = False) -> bool:
    """Validate a CN105 packet frame structure and checksum."""
    if len(frame) < 5:
        if verbose:
            print(f"Error: Frame length ({len(frame)} bytes) is under minimum 5 bytes.", file=sys.stderr)
        return False

    sync1, sync2, length = frame[0], frame[1], frame[2]
    if sync1 not in (SYNC1_REQ, SYNC1_ALT):
        if verbose:
            print(f"Error: Invalid Sync1 byte 0x{sync1:02X}.", file=sys.stderr)
        return False

    expected_len = length + 4  # Header(3) + Payload(length) + Checksum(1)
    if len(frame) < expected_len:
        if verbose:
            print(
                f"Error: Frame length ({len(frame)}) is shorter than expected frame size ({expected_len}).",
                file=sys.stderr,
            )
        return False

    body = frame[:expected_len - 1]
    expected_cs = calculate_checksum(body)
    actual_cs = frame[expected_len - 1]

    if actual_cs != expected_cs:
        if verbose:
            print(
                f"Error: Checksum mismatch. Stored: 0x{actual_cs:02X}, Calculated: 0x{expected_cs:02X}.",
                file=sys.stderr,
            )
        return False

    if verbose:
        print(f"[*] Valid CN105 Packet Frame ({expected_len} bytes):")
        print(f"    Sync: 0x{sync1:02X} 0x{sync2:02X}")
        print(f"    Payload Length: {length} bytes")
        print(f"    Command: 0x{frame[3]:02X}")
        print(f"    Checksum: 0x{actual_cs:02X} (VALID)")

    return True


def decode_telemetry(frame: bytes, verbose: bool = False) -> dict:
    """
    Decode telemetry registers from a response frame.
    Register mappings:
      0x10: Compressor Frequency (Hz)
      0x12: Evaporator Temp (°C + 40)
      0x15: Suction Superheat (Kelvin x 10)
      0x1A: Outdoor Fan Speed Status (Step 0..8)
    """
    if not validate_packet(frame, verbose=False):
        if verbose:
            print("Error: Cannot decode telemetry from invalid packet frame.", file=sys.stderr)
        return {}

    length = frame[2]
    cmd = frame[3]
    payload = frame[4 : 4 + length - 1]

    telemetry = {}
    if cmd in (CMD_TELEMETRY, CMD_SET, CMD_GET):
        idx = 0
        while idx < len(payload) - 1:
            reg = payload[idx]
            val = payload[idx + 1]
            if reg == 0x10:
                telemetry["compressor_freq_hz"] = val
            elif reg == 0x12:
                telemetry["evap_temp_c"] = val - 40
            elif reg == 0x15:
                telemetry["superheat_k"] = val / 10.0
            elif reg == 0x1A:
                telemetry["fan_speed_step"] = val
            idx += 2

    if verbose:
        print("[*] Decoded Telemetry Readout:")
        for k, v in telemetry.items():
            print(f"    {k}: {v}")

    return telemetry


def load_frame_from_input(input_arg: str) -> bytes | None:
    """Load frame bytes from a binary file or hex string."""
    if os.path.exists(input_arg):
        with open(input_arg, "rb") as f:
            return f.read()
    else:
        clean_hex = input_arg.replace(" ", "").replace("0x", "")
        try:
            return bytes.fromhex(clean_hex)
        except ValueError:
            return None


def main():
    args = parse_args()

    input_frame = None
    if args.input:
        input_frame = load_frame_from_input(args.input)
        if input_frame is None:
            print(f"Error: Unable to load input from file or hex string '{args.input}'.", file=sys.stderr)
            sys.exit(1)

    if args.check_only:
        if not input_frame:
            print("Error: --check-only requires --input argument.", file=sys.stderr)
            sys.exit(1)
        is_valid = validate_packet(input_frame, verbose=True)
        if args.decode_telemetry and is_valid:
            decode_telemetry(input_frame, verbose=True)
        sys.exit(0 if is_valid else 1)

    if args.demand_cap is not None:
        enable_bool = bool(args.enable_demand)
        frame = build_demand_cap_packet(cap_pct=args.demand_cap, enable=enable_bool)
        if args.verbose:
            print(f"[+] Constructed Demand Cap Frame ({len(frame)} bytes): {frame.hex().upper()}")
            validate_packet(frame, verbose=True)
    elif input_frame:
        frame = input_frame
        if args.decode_telemetry:
            decode_telemetry(frame, verbose=True)
    else:
        frame = build_demand_cap_packet(cap_pct=75, enable=True)
        if args.verbose:
            print(f"[+] Default 75% Demand Cap Frame ({len(frame)} bytes): {frame.hex().upper()}")

    if args.output:
        with open(args.output, "wb") as f:
            f.write(frame)
        if args.verbose:
            print(f"[*] Output written to '{args.output}'.")

    sys.exit(0)


if __name__ == "__main__":
    main()
