#!/usr/bin/env python3
"""
nighttime_capper.py - Automated Nighttime Compressor Capacity Capping Script

This tool evaluates scheduling rules for FTC6 CN105 capacity capping during
designated nighttime windows (default 22:00–07:00). It dynamically generates
CN105 command frames to enforce capacity limits during nighttime hours and restore
standard operation during daytime hours. It also validates telemetry frames and checks for
FTC6 alarm status.

Supported CLI flags:
  -i, --input          Input binary file or hex string containing CN105 frame or telemetry
  -o, --output         Output binary file path to save generated or processed frame
  -c, --check-only     Validate input frame and window status without modifying or creating files
  -v, --verbose        Enable verbose log output
  --time               Current time override in HH:MM format (e.g. 23:30)
  --start-time         Nighttime window start time in HH:MM format (default: 22:00)
  --end-time           Nighttime window end time in HH:MM format (default: 07:00)
  --demand-cap         Nighttime demand cap percentage level (50, 75, 100) (default: 75)
"""

import argparse
import datetime
import sys
import os

from src.tools.cn105_controller import (
    build_demand_cap_packet,
    validate_packet,
    decode_telemetry,
    load_frame_from_input,
)


def parse_time_str(time_str: str) -> datetime.time:
    """Parse HH:MM string into datetime.time object."""
    try:
        parts = time_str.strip().split(":")
        if len(parts) != 2:
            raise ValueError
        hour, minute = int(parts[0]), int(parts[1])
        return datetime.time(hour, minute)
    except Exception:
        raise ValueError(f"Invalid time format '{time_str}'. Expected HH:MM.")


def is_nighttime(
    current_time: datetime.time,
    start_time: datetime.time,
    end_time: datetime.time,
) -> bool:
    """
    Check if current_time falls within [start_time, end_time).
    Handles midnight wrap-around (e.g., 22:00 to 07:00).
    """
    if start_time == end_time:
        # 24-hour window if equal
        return True
    if start_time < end_time:
        # Non-midnight-wrapping window (e.g., 01:00 to 05:00)
        return start_time <= current_time < end_time
    else:
        # Midnight-wrapping window (e.g., 22:00 to 07:00)
        return current_time >= start_time or current_time < end_time


def check_telemetry_alarm(telemetry: dict, verbose: bool = False) -> bool:
    """
    Check telemetry data for alarm or error indicators.
    Returns True if no alarms detected, False if alarm/error present.
    """
    if not telemetry:
        if verbose:
            print("Warning: Telemetry readout is empty or unparseable.", file=sys.stderr)
        return False

    # Check for fault/alarm code indicators if present in telemetry dict
    alarm_code = telemetry.get("alarm_code", 0)
    if alarm_code != 0:
        if verbose:
            print(f"Error: FTC6 Alarm Code detected: 0x{alarm_code:02X}", file=sys.stderr)
        return False

    if verbose:
        print("[*] FTC6 Telemetry verification successful: Zero alarm codes reported.")
    return True


def parse_args(args=None):
    parser = argparse.ArgumentParser(
        description="Automated Nighttime FTC6 Capacity Capping Script."
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
        help="Validate time window and telemetry without writing output",
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Enable verbose output logging",
    )
    parser.add_argument(
        "--time",
        help="Current time override in HH:MM format (default: current system time)",
    )
    parser.add_argument(
        "--start-time",
        default="22:00",
        help="Nighttime start time in HH:MM format (default: 22:00)",
    )
    parser.add_argument(
        "--end-time",
        default="07:00",
        help="Nighttime end time in HH:MM format (default: 07:00)",
    )
    parser.add_argument(
        "--demand-cap",
        type=int,
        choices=[50, 75, 100],
        default=75,
        help="Nighttime demand cap percentage level (default: 75)",
    )
    return parser.parse_args(args)


def generate_capping_schedule_frame(
    current_time: datetime.time,
    start_time: datetime.time,
    end_time: datetime.time,
    demand_cap: int = 75,
    verbose: bool = False,
) -> tuple[bytes, bool]:
    """
    Generates a CN105 demand capping frame based on time window.
    Returns (frame_bytes, is_nighttime_active).
    """
    in_night = is_nighttime(current_time, start_time, end_time)
    if in_night:
        if verbose:
            print(
                f"[*] Current time ({current_time.strftime('%H:%M')}) is in nighttime window "
                f"({start_time.strftime('%H:%M')}–{end_time.strftime('%H:%M')}). Enforcing {demand_cap}% demand cap."
            )
        frame = build_demand_cap_packet(cap_pct=demand_cap, enable=True)
    else:
        if verbose:
            print(
                f"[*] Current time ({current_time.strftime('%H:%M')}) is outside nighttime window "
                f"({start_time.strftime('%H:%M')}–{end_time.strftime('%H:%M')}). Restoring 100% capacity."
            )
        frame = build_demand_cap_packet(cap_pct=100, enable=False)

    return frame, in_night


def main():
    args = parse_args()

    try:
        start_t = parse_time_str(args.start_time)
        end_t = parse_time_str(args.end_time)
    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

    if args.time:
        try:
            curr_t = parse_time_str(args.time)
        except ValueError as e:
            print(f"Error: {e}", file=sys.stderr)
            sys.exit(1)
    else:
        curr_t = datetime.datetime.now().time()

    input_frame = None
    if args.input:
        input_frame = load_frame_from_input(args.input)
        if input_frame is None:
            print(f"Error: Unable to load input from '{args.input}'.", file=sys.stderr)
            sys.exit(1)

    if args.check_only:
        in_night = is_nighttime(curr_t, start_t, end_t)
        if args.verbose:
            print(f"[*] Window Evaluation for {curr_t.strftime('%H:%M')}:")
            print(f"    Nighttime Window: {start_t.strftime('%H:%M')} - {end_t.strftime('%H:%M')}")
            print(f"    Nighttime Active: {in_night}")
            if in_night:
                print(f"    Target Capping: {args.demand_cap}% Dynamic Cap")
            else:
                print(f"    Target Capping: Disabled / 100%")

        valid = True
        if input_frame:
            valid = validate_packet(input_frame, verbose=args.verbose)
            if valid:
                telemetry = decode_telemetry(input_frame, verbose=args.verbose)
                if telemetry:
                    valid = check_telemetry_alarm(telemetry, verbose=args.verbose)

        sys.exit(0 if valid else 1)

    frame, in_night = generate_capping_schedule_frame(
        curr_t, start_t, end_t, demand_cap=args.demand_cap, verbose=args.verbose
    )

    if args.output:
        with open(args.output, "wb") as f:
            f.write(frame)
        if args.verbose:
            print(f"[*] Output frame ({len(frame)} bytes) written to '{args.output}'.")

    sys.exit(0)


if __name__ == "__main__":
    main()
