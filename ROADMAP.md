# Project Roadmap: Mitsubishi Ecodan Fan Speed Control & Noise Reduction

This roadmap outlines the planned and completed phases for lowering outdoor fan speeds and reducing noise levels on the **Mitsubishi Electric Ecodan PUZ-WM85VAA** heat pump and **FTC6** controller.

## Goals

- 🎯 **Primary Goal**: Lower the outdoor unit BLDC fan speed during low-load / nighttime conditions while maintaining defrost safety and system thermal limits.
- 🎯 **Software Configuration**: Identify and document DIP switch, CN105, and Modbus serial parameters affecting fan speed logic.
- 🎯 **Firmware Decompilation**: Reverse engineer MCU firmware for PUZ-WM85VAA / FTC6, extracting fan control routines and target RPM lookup tables.
- 🎯 **Surgical Patching**: Modify target RPM lookup tables in firmware with updated checksums/CRCs.
- 🎯 **Hardware Interceptor (Fallback)**: Design electronic PWM/RPM signal interceptor circuit if firmware flashing is locked.
- 🎯 **Verification & CI/CD**: Automated testing for build artifacts, decompilation scripts, and documentation syntax.

---

## Progress Overview

| Phase | Description | Status |
| :--- | :--- | :---: |
| **Phase 1** | Conceptualization & Goal Definition | ✅ |
| **Phase 2** | Technical Design & Architecture Specifications | 🚧 |
| **Phase 3** | Specifications & Interface Definitions | ⏳ |
| **Phase 4** | Hardware Analysis & Protocol Reverse Engineering | ⏳ |
| **Phase 5** | Firmware Extraction & Decompilation | ⏳ |
| **Phase 6** | Software Parameter Tuning & Firmware Patching | ⏳ |
| **Phase 7** | Fallback Electronics / Interceptor Development | ⏳ |
| **Phase 8** | Integration Testing, Verification & CI/CD | ⏳ |

---

## Phases & Tasks

### Phase 1: Conceptualization & Goal Definition ✅

Focuses on establishing high-level goals, operational concepts, use cases, and evaluating technical approaches.

- [x] **Task 1.1: Define Top-Level Goal and Repository Structure** ([17ba80c](https://github.com/chatelao/ecodan-fan-control/commit/17ba80cef21567702ad05a0bf67a2ddcae854b46) - 2026-10-27)
  - [x] Document goal in `GEMINI.md`.
  - [x] Establish repository structure (`/src/`, `/test/`, `/build/`, `/specification/`).
- [x] **Task 1.2: Develop Operational Concept (`CONCEPT.md`)** ([17ba80c](https://github.com/chatelao/ecodan-fan-control/commit/17ba80cef21567702ad05a0bf67a2ddcae854b46) - 2026-10-27)
  - [x] Define use cases: UC-1 Nighttime low-noise, UC-2 Low-load acoustic tuning, UC-3 Custom low-noise profile.
  - [x] Evaluate alternatives: Software configuration vs. Hardware modification vs. Firmware reverse engineering.
  - [x] Select staged hybrid strategy (Software + Firmware RE primary, Hardware interceptor secondary).

---

### Phase 2: Technical Design & Architecture Specifications 🚧

Focuses on detailed architectural modeling and technical design documentation (`DESIGN.md` and `TOP_ARCHITECTURE.puml`).

- [x] **Task 2.1: Create High-Level Architecture Overview (`TOP_ARCHITECTURE.puml`)**
  - [x] Draft PlantUML diagram showing PUZ-WM85VAA outdoor unit, FTC6 main controller, inverter driver, BLDC fan motor, and signal paths.
- [ ] **Task 2.2: Develop Technical Design Document (`DESIGN.md`)**
  - [ ] Document detailed technical choices derived from `CONCEPT.md`.
  - [ ] Detail MCU target architecture, memory maps, connector pinouts, and toolchain selection.
  - [ ] Compare implementation alternatives and document discarded options in summary section.

---

### Phase 3: Specifications & Interface Definitions ⏳

Parallelizable specification work defining pinouts, protocol register maps, and CLI script parameters prior to implementation.

- [ ] **Task 3.1: External Specification Conversion**
  - [ ] Convert service manual datasheets and schematics into Markdown under `/specification/`.
  - [ ] Document PUZ-WM85VAA and FTC6 connector pinouts (CN105, CNF1/CNF2, SW7 DIP switch maps).
- [ ] **Task 3.2: Protocol Register Specifications**
  - [ ] Map CN105 serial communication protocol commands relevant to fan speed control.
  - [ ] Map Modbus / M-Net register addresses for noise mode / fan operation limits.
- [ ] **Task 3.3: Tooling Interface Specification**
  - [ ] Define CLI interface requirements (supporting `-i`/`--input`, `-o`/`--output`) for binary analysis, checksum calculation, and patching utilities.

---

### Phase 4: Hardware Analysis & Protocol Reverse Engineering ⏳

Hands-on hardware exploration, pinout verification, and protocol probing.

- [ ] **Task 4.1: Hardware Board Inspection & MCU Identification**
  - [ ] Identify main controller MCU part numbers, chip markings, crystal frequencies, and debugging ports (JTAG/SWD/UART).
  - [ ] Map Flash / EEPROM memory structure and vector tables.
- [ ] **Task 4.2: Motor Signal Interface Probing**
  - [ ] Measure BLDC fan motor PWM drive and Hall-effect feedback signals across various standard operating modes.
  - [ ] Record exact RPM vs PWM duty cycle curves and fault trigger conditions (e.g., P8/P9 error codes).
- [ ] **Task 4.3: Communication Protocol Sniffing**
  - [ ] Capture CN105 serial traffic during silent mode state changes.
  - [ ] Verify command injection possibilities for dynamic fan speed control.

---

### Phase 5: Firmware Extraction & Decompilation ⏳

Extraction and reverse engineering of MCU binary code.

- [ ] **Task 5.1: Firmware Extraction & Memory Dumping**
  - [ ] Read binary firmware from MCU via programmer/debugger interfaces.
  - [ ] Validate dump integrity and identify code/data segments.
- [ ] **Task 5.2: Firmware Reverse Engineering & Disassembly**
  - [ ] Set up Ghidra / radare2 project with appropriate MCU architecture definition.
  - [ ] Locate fan speed calculation routines and target RPM lookup tables.
  - [ ] Document defrost cycle minimum airflow and thermal protection override limits.
  - [ ] Analyze checksum / CRC calculation routines and signature validation logic.

---

### Phase 6: Software Parameter Tuning & Firmware Patching ⏳

Implementation of software configuration changes and binary firmware modifications.

- [ ] **Task 6.1: Software Parameter Tuning**
  - [ ] Verify maximum noise reduction achievable via software parameters and DIP switch configurations.
- [ ] **Task 6.2: Checksum Utility Tooling**
  - [ ] Implement command-line tool (`/src/tools/checksum.py`) supporting `-i`/`--input` and `-o`/`--output` to recalculate firmware checksums.
- [ ] **Task 6.3: Firmware Target Table Patching**
  - [ ] Create patch scripts to alter target RPM lookup tables while keeping safety bounds intact.
  - [ ] Re-flash patched firmware to target MCU and verify basic boot and operation.

---

### Phase 7: Fallback Electronics / Interceptor Development ⏳

Secondary hardware fallback path if firmware flashing is infeasible.

- [ ] **Task 7.1: Interceptor Circuit Design**
  - [ ] Design active microcontroller-based PWM interceptor board (KiCad schematics in `/src/hardware/`).
  - [ ] Synthesize valid Hall-effect feedback signals to prevent P8/P9 motor fault codes.
- [ ] **Task 7.2: Interceptor Firmware Development**
  - [ ] Develop firmware for interceptor MCU to dynamically scale fan drive signals.

---

### Phase 8: Integration Testing, Verification & CI/CD ⏳

Automated verification, test bench validation, and continuous integration pipeline setup.

- [ ] **Task 8.1: Test Bench Setup & Emulation**
  - [ ] Develop test scripts in `/test/` to validate checksum utility against firmware binary samples.
  - [ ] Simulate fan speed calculation routines against edge cases (defrost mode, ambient heat extremes).
- [ ] **Task 8.2: Continuous Integration Pipeline**
  - [ ] Configure CI/CD pipeline (GitHub Actions) to execute automated tests on decompilation scripts, checksum recalculations, documentation syntax, and code formatting on every commit.
  - [ ] Set up documentation publishing via ReadTheDocs / GitHub Pages.
