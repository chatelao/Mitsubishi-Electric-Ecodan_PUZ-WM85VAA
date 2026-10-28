# Mitsubishi Electric Ecodan PUZ-WM85VAA Fan Acoustic Optimization Project

This repository contains technical specifications, hardware interceptor designs, firmware analysis tools, and roadmap documentation for reducing operational fan noise on the **Mitsubishi Electric Ecodan PUZ-WM85VAA** air-to-water heat pump outdoor unit (twin-fan chassis) and its **FTC6** (Flow Temperature Controller 6) main controller.

---

## Objective

Lower operational outdoor fan noise (<35 dB(A) acoustic pressure at 3 meters during nighttime high-demand heating) while preserving essential heat pump thermodynamic safeguards (suction superheat collapse prevention, defrost airflow minimums, and inverter IPM thermal protection).

---

## Strategy: Inverted Staged Hybrid Approach

1. **Stage 1 (Primary Execution)**:
   - **Dual-Channel Hardware Signal Interceptor**: RP2350-based inline hardware module installed on fan motor connectors `CNF1` and `CNF2` to attenuate speed commands ($V_{\text{sp}}$, 0–6.5V) while synthesizing feedback pulses ($FG$) to prevent `P8`/`P9` fault trips.
   - **FTC6 Indoor CN105 Load Capping**: Command injection over the indoor 2400/9600 bps 8E1 serial port to cap compressor thermal demand during nighttime hours.
2. **Stage 2 (Secondary / Advanced)**:
   - **Firmware Reverse Engineering & Patching**: Decompile Renesas RX62T 32-bit MCU code flash in Ghidra v11.x, patch fan speed target lookup tables (`0xFFFD4120`), recalculate CRC-16-CCITT checksums via `/src/tools/patch_checksum.py`, and reflash ROM if the 128-bit ID-Code (`0xFFFFFFA0`) security gate is verified as unlocked.

---

## Project Structure & Documentation

- **`CONCEPT.md`**: Architectural use cases, trade-offs, and high-level alternatives comparison.
- **`DESIGN.md`**: Microcontroller specs, memory maps, coupled electro-thermal laws, circuit schematics, and signal interface specifications.
- **`TOP_ARCHITECTURE.puml`**: Top-level PlantUML architecture diagram illustrating hardware and software component interconnects.
- **`ROADMAP.md`**: Project execution phases, detailed tasks, and progress tracking.
- **`/specification/`**: System connector pinouts (`CNF1`/`CNF2`, `CN105`), Renesas RX62T MCU architecture, and DIP switch settings.
  - `cnf_pinout.md`: `CNF1`/`CNF2` 6-pin BLDC motor interface connector pinout.
  - `cn105_protocol.md`: FTC6 indoor `CN105` serial command protocol.
  - `rx62t_mcu.md`: Renesas RX62T memory map, registers, and vector table layout.
  - `dip_switches.md`: Outdoor unit DIP switches (`SW7`/`SW1`) and factory service parameters.

---

## Verification & Tooling

To format and check documentation in accordance with repository standards:

```bash
# Check Markdown formatting
npx prettier --check "**/*.md"

# Automatically format Markdown files
npx prettier --write "**/*.md"
```

### Continuous Integration (CI/CD)

An automated GitHub Actions pipeline (`.github/workflows/ci.yml`) validates the state of the repository after every commit and pull request:

- **Documentation Syntax & Formatting**: Enforces Markdown formatting with Prettier.
- **Source Code Syntax & Compilation**: Validates Python scripts (`py_compile`) and C embedded firmware compilation (`gcc`).
- **Automated Test Suite**: Executes unit and integration test benches (`PYTHONPATH=. pytest`).
- **Toolchain End-to-End Pipeline**: Runs end-to-end simulation, factory ROM synthesis, fan table patching, CRC recalculation, CN105 packet generation, and nighttime capper scheduling.
