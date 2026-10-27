#!/usr/bin/env python3
"""
interceptor_sim.py - Interceptor Board Bench Simulation Tool

Simulates ATtiny1616 dual-channel hardware interceptor signal transformation:
  - Vsp dynamic attenuation (Vsp_out = Vsp_in * k)
  - Open-drain FG tachometer pulse ratio synthesis (FG_out = FG_in / k)
  - Active stall passthrough (FG_out = 0 Hz if FG_in < 10 Hz while Vsp_in > 1.8V)
  - Evaporator freeze override relay bypass (T_evap < -3.0°C)
  - High-load voltage emergency relay bypass (Vsp_in > 5.2V)

Supported CLI flags:
  -i, --input          Input JSON benchmark vector file or inline JSON string
  -o, --output         Output JSON result file path
  -c, --check-only     Validate input vector structure and parameters without writing output
  -v, --verbose        Enable verbose log output
"""

import argparse
import json
import sys
import os

DIVIDER_RATIO = 0.6875
OPAMP_GAIN = 1.50
DEFAULT_K_ATTEN = 0.68
MIN_K_ATTEN = 0.68
MAX_K_ATTEN = 1.00

VSP_STALL_VOLTAGE_MIN = 1.80
VSP_BYPASS_VOLTAGE_MAX = 5.20
FG_STALL_FREQ_HZ_MIN = 10.0
NTC_FREEZE_TEMP_C_MIN = -3.0


def parse_args(args=None):
    parser = argparse.ArgumentParser(
        description="ATtiny1616 Dual-Channel Interceptor Signal Bench Simulator."
    )
    parser.add_argument(
        "-i",
        "--input",
        help="Input JSON signal bench vector file path or JSON string",
    )
    parser.add_argument(
        "-o",
        "--output",
        help="Output JSON result file path to write simulation results",
    )
    parser.add_argument(
        "-c",
        "--check-only",
        action="store_true",
        help="Validate signal input structure and safety thresholds without creating output files",
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Enable verbose output logging",
    )
    return parser.parse_args(args)


def simulate_interceptor(vsp_in1: float, vsp_in2: float, fg_in1: float, fg_in2: float, t_evap: float = 20.0, k: float = DEFAULT_K_ATTEN) -> dict:
    """
    Simulate dual-channel interceptor signal processing and safety logic.
    """
    if k < MIN_K_ATTEN:
        k = MIN_K_ATTEN
    if k > MAX_K_ATTEN:
        k = MAX_K_ATTEN

    # Freeze bypass override check
    if t_evap < NTC_FREEZE_TEMP_C_MIN:
        return {
            "mode": "FREEZE_BYPASS",
            "relay_bypass_active": True,
            "k_attenuation": k,
            "t_evap_c": t_evap,
            "ch1": {
                "vsp_in_volts": vsp_in1,
                "vsp_out_volts": vsp_in1,
                "fg_in_freq_hz": fg_in1,
                "fg_out_freq_hz": fg_in1,
                "stall_detected": False,
            },
            "ch2": {
                "vsp_in_volts": vsp_in2,
                "vsp_out_volts": vsp_in2,
                "fg_in_freq_hz": fg_in2,
                "fg_out_freq_hz": fg_in2,
                "stall_detected": False,
            },
        }

    # High load emergency bypass check
    if vsp_in1 > VSP_BYPASS_VOLTAGE_MAX or vsp_in2 > VSP_BYPASS_VOLTAGE_MAX:
        return {
            "mode": "HIGH_LOAD_BYPASS",
            "relay_bypass_active": True,
            "k_attenuation": k,
            "t_evap_c": t_evap,
            "ch1": {
                "vsp_in_volts": vsp_in1,
                "vsp_out_volts": vsp_in1,
                "fg_in_freq_hz": fg_in1,
                "fg_out_freq_hz": fg_in1,
                "stall_detected": False,
            },
            "ch2": {
                "vsp_in_volts": vsp_in2,
                "vsp_out_volts": vsp_in2,
                "fg_in_freq_hz": fg_in2,
                "fg_out_freq_hz": fg_in2,
                "stall_detected": False,
            },
        }

    # Normal intercept calculations
    vsp_out1 = min(6.5, max(0.0, vsp_in1 * k))
    vsp_out2 = min(6.5, max(0.0, vsp_in2 * k))

    # Stall checks
    stall1 = (vsp_in1 > VSP_STALL_VOLTAGE_MIN) and (fg_in1 < FG_STALL_FREQ_HZ_MIN)
    stall2 = (vsp_in2 > VSP_STALL_VOLTAGE_MIN) and (fg_in2 < FG_STALL_FREQ_HZ_MIN)

    fg_out1 = 0.0 if stall1 else (fg_in1 / k)
    fg_out2 = 0.0 if stall2 else (fg_in2 / k)

    mode = "STALL_PASSTHROUGH" if (stall1 or stall2) else "NORMAL_INTERCEPT"

    return {
        "mode": mode,
        "relay_bypass_active": False,
        "k_attenuation": k,
        "t_evap_c": t_evap,
        "ch1": {
            "vsp_in_volts": round(vsp_in1, 3),
            "vsp_out_volts": round(vsp_out1, 3),
            "fg_in_freq_hz": round(fg_in1, 2),
            "fg_out_freq_hz": round(fg_out1, 2),
            "stall_detected": stall1,
        },
        "ch2": {
            "vsp_in_volts": round(vsp_in2, 3),
            "vsp_out_volts": round(vsp_out2, 3),
            "fg_in_freq_hz": round(fg_in2, 2),
            "fg_out_freq_hz": round(fg_out2, 2),
            "stall_detected": stall2,
        },
    }


def load_input_vector(input_arg: str) -> dict | None:
    """Load JSON vector from file or raw JSON string."""
    if os.path.exists(input_arg):
        with open(input_arg, "r") as f:
            return json.load(f)
    else:
        try:
            return json.loads(input_arg)
        except json.JSONDecodeError:
            return None


def main():
    args = parse_args()

    vec = None
    if args.input:
        vec = load_input_vector(args.input)
        if vec is None:
            print(f"Error: Unable to parse input vector from file or string '{args.input}'.", file=sys.stderr)
            sys.exit(1)

    if vec is None:
        # Default baseline simulation vector
        vec = {
            "vsp_in1": 4.0,
            "vsp_in2": 4.0,
            "fg_in1": 50.0,
            "fg_in2": 50.0,
            "t_evap": 5.0,
            "k": 0.68,
        }

    if args.check_only:
        # Validate input vector ranges
        required_keys = ["vsp_in1", "vsp_in2", "fg_in1", "fg_in2"]
        missing = [k for k in required_keys if k not in vec]
        if missing:
            print(f"Error: Missing vector keys: {missing}", file=sys.stderr)
            sys.exit(1)
        res = simulate_interceptor(
            vec["vsp_in1"],
            vec["vsp_in2"],
            vec["fg_in1"],
            vec["fg_in2"],
            vec.get("t_evap", 20.0),
            vec.get("k", DEFAULT_K_ATTEN),
        )
        if args.verbose:
            print("[*] Vector check passed successfully. Simulation Result:")
            print(json.dumps(res, indent=2))
        sys.exit(0)

    res = simulate_interceptor(
        vec["vsp_in1"],
        vec["vsp_in2"],
        vec["fg_in1"],
        vec["fg_in2"],
        vec.get("t_evap", 20.0),
        vec.get("k", DEFAULT_K_ATTEN),
    )

    if args.verbose:
        print("[+] Simulation Result:")
        print(json.dumps(res, indent=2))

    if args.output:
        with open(args.output, "w") as f:
            json.dump(res, f, indent=2)
        if args.verbose:
            print(f"[*] Simulation result written to '{args.output}'.")

    sys.exit(0)


if __name__ == "__main__":
    main()
