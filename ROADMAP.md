# Project Roadmap (ROADMAP.md)

This roadmap outlines the implementation phases, objectives, and task schedule for modifying the **Mitsubishi Electric Ecodan PUZ-WM85VAA** outdoor unit fan speed parameters, software control logic, and hardware interfaces in conjunction with the **FTC6** controller.

---

## Goals

- ⏳ **Primary Goal**: Reduce operational fan noise of the Mitsubishi Electric Ecodan PUZ-WM85VAA heat pump outdoor unit by lowering target fan RPM during high-demand and nighttime operation while preserving critical safety logic (defrost airflow minimums and IPM thermal protection).
- ⏳ **Firmware Reverse Engineering & Patching**: Decompile, analyze, and surgical patch the PUZ-WM85VAA outdoor unit MCU firmware target RPM tables and CRC checksum recalculation logic.
- ⏳ **Software & Parameter Configuration**: Analyze native DIP switch (SW7/SW1) settings and CN105 serial protocol interfaces for parameter-based fan speed constraints.
- ⏳ **Fallback Hardware Interceptor**: Develop an inline microcontroller signal interceptor board (ATtiny1616-based $V_{\text{sp}}$ attenuation & synthetic FG pulse generation) to circumvent MCU write-protection if required.

---

## Progress Overview

| Phase | Description | Status |
| :--- | :--- | :--- |
| **Phase 1: Specification & Hardware Interfaces** | Document pinouts, MCU specs, memory maps, DIP switches, and serial interfaces | 🚧 |
| **Phase 2: Toolchain & Binary Analysis Setup** | Setup Ghidra/radare2 environment, binary patching scripts (`patch_checksum.py`), and CI workflow | ⏳ |
| **Phase 3: Firmware Decompilation & Target Logic Analysis** | Extract MCU binary, decompile RX62T/M16C code, locate target RPM tables (`0xFFFD4120`), and map safety checks | ⏳ |
| **Phase 4: Firmware Patching, Checksum Recalculation & Emulation** | Patch RPM target curves (1150 RPM cap to 780 RPM), recalculate CRC16 checksums, and verify via tests | ⏳ |
| **Phase 5: Fallback Hardware Interceptor Subsystem** | Design ATtiny1616 schematic/PCB for inline $V_{\text{sp}}$ modulation and synthetic FG pulse generation (preventing `P8`/`P9` fault codes) | ⏳ |
| **Phase 6: Integration, Field Testing & Acoustic Validation** | Deploy firmware/hardware patches on PUZ-WM85VAA unit, perform noise level (<35 dB(A)) and thermal/defrost validation | ⏳ |

---

## Phases & Detailed Tasks

### Phase 1: Specification & Hardware Interfaces 🚧

- [ ] **Task 1.1: Document System Architecture and Connector Specifications** ⏳
  - [ ] Document CNF1/CNF2 fan motor connector pinouts ($V_{\text{cc\_HV}}$, $V_{\text{cc\_logic}}$, $V_{\text{sp}}$, $FG$) in `/specification/`
  - [ ] Document CN105 serial interface pinouts, baud rates (2400/9600 8N1), and packet structures
- [ ] **Task 1.2: Define MCU Hardware Architecture & Memory Maps** ⏳
  - [ ] Specify Renesas RX62T / M16C CPU registers, clock scaling (12 MHz xtal, 96 MHz ICLK), and pin package specs
  - [ ] Define ROM (`0xFFFC0000`), Data Flash (`0x00100000`), SRAM (`0x00000000`), and Vector Table layout in `/specification/`
- [ ] **Task 1.3: Document Factory DIP Switch & Service Parameters** ⏳
  - [ ] Map SW7 Silent Mode bit settings (Bit 1: -3 dB(A), Bit 2: -5 dB(A)) and SW1 demand control options

---

### Phase 2: Toolchain & Binary Analysis Setup ⏳

- [ ] **Task 2.1: Establish Reverse Engineering Analysis Environment** ⏳
  - [ ] Configure Ghidra v10.x with Renesas RX62T architecture module and memory map layout
  - [ ] Initialize decompilation source structure under `/src/firmware/` and build output directory under `/build/`
- [ ] **Task 2.2: Develop Checksum & CRC Verification Tooling** ⏳
  - [ ] Implement `/src/tools/patch_checksum.py` supporting `-i/--input`, `-o/--output`, `-c/--check-only` flags for CCITT-16 CRC recalculation
  - [ ] Add unit tests under `/test/` for CRC recalculation and patch verification

---

### Phase 3: Firmware Decompilation & Target Logic Analysis ⏳

- [ ] **Task 3.1: Extract and Disassemble Outdoor Unit Firmware** ⏳
  - [ ] Dump Flash ROM (`0xFFFC0000` - `0xFFFFFFFF`) via hardware programming header
  - [ ] Disassemble entry point `_start` (`0xFFFFFFFC`) and main control loop
- [ ] **Task 3.2: Map Fan RPM Target Calculation Routines** ⏳
  - [ ] Locate RPM target lookup table at Flash ROM address `0xFFFD4120`
  - [ ] Reverse engineer $\text{RPM}_{\text{target}} = f(f_{\text{comp}}, T_{\text{ambient}}, T_{\text{evap}})$ algorithm and mode offset parameters
- [ ] **Task 3.3: Analyze Safety Logic & Diagnostic Fault Codes** ⏳
  - [ ] Trace defrost cycle safety routines ($T_{\text{evap}} < -5^\circ\text{C} \implies \text{RPM}_{\text{target}} \ge 850$)
  - [ ] Trace IPM thermal protection ($T_{\text{IPM}} > 85^\circ\text{C} \implies \text{RPM}_{\text{target}} \ge 1100$)
  - [ ] Document `P8` and `P9` fan motor FG feedback fault detection thresholds

---

### Phase 4: Firmware Patching, Checksum Recalculation & Emulation ⏳

- [ ] **Task 4.1: Implement Fan Target Curve Firmware Patch** ⏳
  - [ ] Create patch script `/src/tools/patch_fan_rpm.py` with `-i/--input` and `-o/--output` flags
  - [ ] Cap high-load target RPM from 1150 RPM to 780 RPM while preserving defrost/IPM override branches
- [ ] **Task 4.2: Validate Binary Integrity & Checksum Recalculation** ⏳
  - [ ] Recalculate CCITT-16 CRC at address `0xFFFFFFBE` and generate patched binary in `/build/`
- [ ] **Task 4.3: Emulate and Unit Test Patched Logic** ⏳
  - [ ] Run test suite under `/test/` verifying patched binary against synthetic inputs (ambient temp, compressor frequency)

---

### Phase 5: Fallback Hardware Interceptor Subsystem ⏳

- [ ] **Task 5.1: Circuit Schematic & PCB Design** ⏳
  - [ ] Create ATtiny1616 schematic in PlantUML / KiCad under `/src/hardware/` for $V_{\text{sp}}$ ADC sampling and PWM/DAC output attenuation
  - [ ] Design FG feedback pulse generation circuit ($f_{\text{synth}} = f_{\text{actual}} / k$)
- [ ] **Task 5.2: Interceptor Firmware Implementation** ⏳
  - [ ] Implement ATtiny1616 embedded logic under `/src/interceptor/` for dynamic $V_{\text{sp}}$ attenuation ($k = 0.65 - 0.80$)
  - [ ] Implement synthetic FG pulse counter/generator to prevent main PCB `P8`/`P9` diagnostic trip
- [ ] **Task 5.3: Hardware Interceptor Verification** ⏳
  - [ ] Simulate and test interceptor board on signal test bench under `/test/`

---

### Phase 6: Integration, Field Testing & Acoustic Validation ⏳

- [ ] **Task 6.1: Flashing & Hardware Installation** ⏳
  - [ ] Program patched MCU firmware onto PUZ-WM85VAA outdoor unit board (or install hardware interceptor)
- [ ] **Task 6.2: Operational & Acoustic Field Verification** ⏳
  - [ ] Verify nighttime noise levels meet target (<35 dB(A) at 3 meters)
  - [ ] Validate defrost cycle activation and IPM temperature boundaries under real heat load conditions
