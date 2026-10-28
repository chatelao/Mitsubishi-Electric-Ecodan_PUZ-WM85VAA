#!/usr/bin/env python3
"""
ghidra_init_rx62t.py - Ghidra Decompiler Environment Initialization for Renesas RX62T MCU

This script initializes the Ghidra v11.x decompiler environment for the
Renesas RX62T microcontroller (R5F562TxxDFP) used in the Mitsubishi Electric
Ecodan PUZ-WM85VAA outdoor heat pump unit.

It defines:
  - Memory Blocks: SRAM, SFRs, Data Flash, Code Flash, and Fixed Vectors.
  - Key Memory Symbols: Reset Vector, ID-Code Security Field, CRC Checksum Word,
    and Target Fan RPM Lookup Table (LUT).

Can be executed directly within Ghidra PyGhidra/Jython environment, or as a
standalone Python utility to inspect, validate, or export Ghidra layout configurations.

Supported CLI flags:
  -i, --input      Input binary file path to validate against memory bounds
  -o, --output     Output JSON/PyGhidra memory layout file path
  -c, --check-only Validate memory layout definitions without writing output files
  -v, --verbose    Enable verbose log output
"""

# Ghidra Script Metadata Header
# @name RX62T_Environment_Initialization
# @category RX62T
# @keybinding
# @menupath Tools.RX62T Environment Initialization
# @toolbar

import argparse
import json
import os
import sys

# Memory Region Boundaries (Renesas RX62T 256 KB Flash Variant)
MEMORY_BLOCKS = [
    {
        "name": "SRAM",
        "start": 0x00000000,
        "size": 16 * 1024,  # 16 KB
        "read": True,
        "write": True,
        "execute": True,
        "comment": "Internal SRAM (Variable storage, fan speed target, stack)",
    },
    {
        "name": "SFR",
        "start": 0x00080000,
        "size": 128 * 1024,  # 128 KB
        "read": True,
        "write": True,
        "execute": False,
        "comment": "Peripheral Special Function Registers (ICU, MTU3, S12AD, SCI)",
    },
    {
        "name": "DATA_FLASH",
        "start": 0x00100000,
        "size": 32 * 1024,  # 32 KB
        "read": True,
        "write": True,
        "execute": False,
        "comment": "Data Flash E2 Data Storage (Calibration, fault history)",
    },
    {
        "name": "CODE_FLASH",
        "start": 0xFFFC0000,
        "size": 255 * 1024 + 896,  # 255.875 KB (0xFFFC0000 - 0xFFFFFF7F)
        "read": True,
        "write": False,
        "execute": True,
        "comment": "Code Flash ROM (Main program logic, relocatable INTB table, LUTs)",
    },
    {
        "name": "FIXED_VECTORS",
        "start": 0xFFFFFF80,
        "size": 128,  # 128 Bytes
        "read": True,
        "write": False,
        "execute": False,
        "comment": "Fixed Vector Table (ID-Code security field, OFS1, Reset Vector)",
    },
]

# Key Hardware Symbols & Memory Addresses
SYMBOLS = {
    "CODE_FLASH_START": {
        "address": 0xFFFC0000,
        "comment": "Start address of Code Flash ROM region",
    },
    "FAN_TARGET_RPM_LUT": {
        "address": 0xFFFD4120,
        "comment": "16-entry uint16 fan target RPM lookup table matrix",
    },
    "ROM_CRC16_CHECKSUM": {
        "address": 0xFFFFFF7E,
        "comment": "Non-vector ROM CRC-16-CCITT checksum storage word",
    },
    "ID_CODE_SECURITY_FIELD": {
        "address": 0xFFFFFFA0,
        "comment": "128-bit ID-Code security protection field (16 bytes)",
    },
    "OFS1_REGISTER": {
        "address": 0xFFFFFFF8,
        "comment": "Option Function Select Register 1",
    },
    "RESET_VECTOR": {
        "address": 0xFFFFFFFC,
        "comment": "Power-On Reset Vector Entry Point (_PowerON_Reset)",
    },
}


def parse_args(args=None):
    parser = argparse.ArgumentParser(
        description="Ghidra Decompiler Environment Initialization Script for Renesas RX62T MCU."
    )
    parser.add_argument(
        "-i",
        "--input",
        help="Path to input firmware binary file to validate memory mapping bounds",
    )
    parser.add_argument(
        "-o",
        "--output",
        help="Path to output JSON memory layout script file",
    )
    parser.add_argument(
        "-c",
        "--check-only",
        action="store_true",
        help="Validate memory block definitions without modifying/creating files",
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Enable verbose log output",
    )
    return parser.parse_args(args)


def get_memory_layout() -> dict:
    """Return complete RX62T Ghidra memory map layout definition."""
    return {
        "processor": "Renesas RX62T (R5F562TxxDFP)",
        "architecture": "RX 32-bit Harvard Architecture",
        "memory_blocks": MEMORY_BLOCKS,
        "symbols": SYMBOLS,
    }


def verify_memory_layout() -> bool:
    """Validate memory block continuity, non-overlapping addresses, and symbol bounds."""
    # Check block overlaps and bounds
    blocks = sorted(MEMORY_BLOCKS, key=lambda b: b["start"])
    for i in range(len(blocks)):
        b = blocks[i]
        start = b["start"]
        end = start + b["size"] - 1

        if start < 0 or end > 0xFFFFFFFF:
            print(
                f"Error: Block '{b['name']}' out of 32-bit address space bounds (0x{start:08X} - 0x{end:08X}).",
                file=sys.stderr,
            )
            return False

        if i < len(blocks) - 1:
            next_b = blocks[i + 1]
            if end >= next_b["start"]:
                print(
                    f"Error: Memory block overlap detected between '{b['name']}' and '{next_b['name']}'.",
                    file=sys.stderr,
                )
                return False

    # Check symbols reside in valid defined memory blocks
    for sym_name, sym_info in SYMBOLS.items():
        addr = sym_info["address"]
        in_block = any(
            b["start"] <= addr < (b["start"] + b["size"]) for b in MEMORY_BLOCKS
        )
        if not in_block:
            print(
                f"Error: Symbol '{sym_name}' at address 0x{addr:08X} does not reside within any memory block.",
                file=sys.stderr,
            )
            return False

    return True


def run_in_ghidra():
    """Execution hook when running inside Ghidra environment (Jython/PyGhidra)."""
    try:
        # Check if running under Ghidra
        if "currentProgram" in globals() or "currentProgram" in locals():
            prog = globals().get("currentProgram")
            mem = prog.getMemory()
            sym_table = prog.getSymbolTable()

            print("[*] Running RX62T Ghidra Initializer inside Ghidra...")
            for b in MEMORY_BLOCKS:
                addr = prog.getAddressFactory().getDefaultAddressSpace().getAddress(b["start"])
                try:
                    mem.createUninitializedBlock(b["name"], addr, b["size"], False)
                    print(f"    Created block '{b['name']}' at 0x{b['start']:08X}")
                except Exception as ex:
                    print(f"    Block '{b['name']}' already exists or notice: {ex}")

            for sym_name, sym_info in SYMBOLS.items():
                addr = prog.getAddressFactory().getDefaultAddressSpace().getAddress(sym_info["address"])
                try:
                    sym_table.createLabel(addr, sym_name, None, ghidra.program.model.symbol.SourceType.USER_DEFINED) # type: ignore
                    print(f"    Created symbol '{sym_name}' at 0x{sym_info['address']:08X}")
                except Exception as ex:
                    print(f"    Symbol '{sym_name}' notice: {ex}")

            print("[+] Ghidra RX62T memory layout initialization complete.")
            return True
    except Exception as e:
        print(f"Notice: Ghidra execution environment check: {e}")
    return False


def validate_input_binary(input_path: str, verbose: bool = False) -> bool:
    """Validate that input binary file matches expected Code Flash / ROM memory bounds."""
    if not os.path.exists(input_path):
        print(f"Error: Input binary '{input_path}' not found.", file=sys.stderr)
        return False

    file_size = os.path.getsize(input_path)
    code_flash_block = next(b for b in MEMORY_BLOCKS if b["name"] == "CODE_FLASH")
    fixed_vector_block = next(b for b in MEMORY_BLOCKS if b["name"] == "FIXED_VECTORS")
    expected_rom_size = code_flash_block["size"] + fixed_vector_block["size"]  # 256 KB

    if file_size != expected_rom_size:
        print(
            f"Error: Binary size ({file_size} bytes) does not match total ROM size ({expected_rom_size} bytes).",
            file=sys.stderr,
        )
        return False

    if verbose:
        print(f"[*] Validated binary '{input_path}': Size {file_size} bytes matches RX62T Code Flash ROM bounds.")

    return True


def main():
    args = parse_args()

    # If running inside Ghidra, execute Ghidra API sequence
    if run_in_ghidra():
        sys.exit(0)

    # Validate memory layout definition
    if not verify_memory_layout():
        sys.exit(1)

    if args.input:
        if not validate_input_binary(args.input, verbose=args.verbose):
            sys.exit(1)

    layout = get_memory_layout()

    if args.check_only:
        print("[*] RX62T Ghidra Memory Layout Definition Check:")
        print(f"    Processor: {layout['processor']}")
        print(f"    Defined Memory Blocks: {len(layout['memory_blocks'])}")
        print(f"    Defined Symbols: {len(layout['symbols'])}")
        if args.verbose:
            for b in layout["memory_blocks"]:
                print(
                    f"      - {b['name']}: 0x{b['start']:08X} - 0x{b['start'] + b['size'] - 1:08X} ({b['size']} bytes)"
                )
            for sym, info in layout["symbols"].items():
                print(f"      - {sym}: 0x{info['address']:08X} ({info['comment']})")
        print("    Status: Memory layout configuration valid.")
        sys.exit(0)

    if args.verbose:
        print("[+] RX62T Ghidra Memory Layout Config:")
        print(json.dumps(layout, indent=2))

    if args.output:
        out_dir = os.path.dirname(args.output)
        if out_dir:
            os.makedirs(out_dir, exist_ok=True)
        with open(args.output, "w") as f:
            json.dump(layout, f, indent=2)
        print(f"[+] Written Ghidra memory layout to '{args.output}'.")

    sys.exit(0)


if __name__ == "__main__":
    main()
