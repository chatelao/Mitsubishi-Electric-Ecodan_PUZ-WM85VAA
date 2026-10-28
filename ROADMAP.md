# Project Roadmap (ROADMAP.md)

This roadmap outlines the implementation phases, objectives, and task schedule for modifying the **Mitsubishi Electric Ecodan PUZ-WM85VAA** outdoor unit fan speed parameters, software control logic, and hardware interfaces in conjunction with the **FTC6** controller, adhering to the Inverted Staged Hybrid Approach specified in `CONCEPT.md` and `DESIGN.md`.

---

## Goals

- 🚧 **Primary Goal**: Reduce operational fan noise of the Mitsubishi Electric Ecodan PUZ-WM85VAA heat pump outdoor unit by lowering target fan RPM during high-demand and nighttime operation (<35 dB(A) sound pressure at 3 meters) while preserving critical safety logic (suction superheat collapse prevention, defrost airflow minimums, and IPM thermal protection).
- ⏳ **Stage 1 (Primary): Hardware Interceptor & CN105 Capping**: Develop and deploy a dual-channel inline microcontroller signal interceptor board (RP2350-based $V_{\text{sp}}$ attenuation & synthetic $FG$ pulse generation) on connectors `CNF1`/`CNF2` combined with indoor `CN105` serial thermal load capping.
- ⏳ **Stage 2 (Advanced): Firmware Reverse Engineering & Patching**: Inspect Renesas RX62T 128-bit ID-code protection (`0xFFFFFFA0`), extract code flash (`0xFFFC0000`–`0xFFFFFFFF`), decompile in Ghidra v11.x, patch fan target lookup tables (`0xFFFD4120`), recalculate CRC-16-CCITT checksums via script, and reflash the MCU.

---

## Progress Overview

| Phase                                                                                  | Description                                                                                                            | Status |
| :------------------------------------------------------------------------------------- | :--------------------------------------------------------------------------------------------------------------------- | :----- |
| **Phase 1: Specification & System Interfaces**                                         | Document pinouts, Renesas RX62T specs, memory maps, DIP switches, and CN105 serial protocol                            | ✅     |
| **Phase 2: Stage 1 Subsystem — Dual-Channel Hardware Interceptor**                     | Design RP2350 dual-channel circuit, schematic, signal conditioning front-end, and open-drain $FG$ synthesis            | ✅     |
| **Phase 3: Stage 1 Subsystem — FTC6 Indoor CN105 Thermal Load Capping**                | Implement 2400/9600 bps 8E1 serial command injection to cap compressor thermal load during nighttime hours             | ✅     |
| **Phase 4: Stage 2 Subsystem — Firmware Reverse Engineering & Decompilation**          | Extract Renesas RX62T code flash, decompile RX core logic, map fan target LUT at `0xFFFD4120`, and safety loops        | ⏳     |
| **Phase 5: Stage 2 Subsystem — Firmware Patching, Checksum Recalculation & Emulation** | Patch fan target LUTs (1150 to 780 RPM cap), recalculate CRC-16 checksum via `/src/tools/patch_checksum.py`, run tests | ✅     |
| **Phase 6: Field Integration, Field Verification & Acoustic Validation**               | Install interceptor/patched firmware on PUZ-WM85VAA unit, perform noise level (<35 dB(A)) and thermal validation       | ⏳     |

---

## Phases & Detailed Tasks

### Phase 1: Specification & System Interfaces ✅

- [x] **Task 1.1: Document System Architecture and Dual Connector Specifications** ✅
  - [x] Document `CNF1` (Upper Fan) and `CNF2` (Lower Fan) 6-pin connector specifications (340V DC `Vcc_HV`, 15V `Vcc_Logic`, 0–6.5V $V_{\text{sp}}$, 0–5V $FG$) in `/specification/cnf_pinout.md`
  - [x] Document indoor `CN105` serial interface pinouts, baud rates (2400/9600 8E1), and packet structures in `/specification/cn105_protocol.md`
- [x] **Task 1.2: Define MCU Hardware Architecture & Memory Maps** ✅
  - [x] Specify Renesas RX62T (`R5F562TxxDFP`) registers, 12 MHz oscillator / 96 MHz ICLK, and 100-pin LQFP pinout in `/specification/rx62t_mcu.md`
  - [x] Define Code Flash (`0xFFFC0000`), Data Flash (`0x00100000`), SRAM (`0x00000000`), Fixed Vectors (`0xFFFFFF80`), and 128-bit ID-Code Security location (`0xFFFFFFA0`)
- [x] **Task 1.3: Document Factory DIP Switch & Service Parameters** ✅
  - [x] Map `SW7` Silent Mode bit settings (Bit 1: -3 dB(A), Bit 2: Capacity Override) and `SW1` demand control options in `/specification/dip_switches.md`

---

### Phase 2: Stage 1 Subsystem — Dual-Channel Hardware Interceptor ✅

- [x] **Task 2.1: Circuit Schematic & PCB Design** ✅
  - [x] Design RP2350 dual-channel schematic in PlantUML / KiCad under `/src/hardware/`
  - [x] Design $0.50\times$ resistor divider ($R_1=10\text{ k}\Omega, R_2=10\text{ k}\Omega$) with 3.3V Zener clamp scaling $6.5\text{V}$ $V_{\text{sp}}$ to $3.25\text{V}$ for 3.3V ADC
  - [x] Design dual MCP6002 OpAmp gain stage ($G=2.00$) powered from 15V `Vcc_Logic` rail restoring $0\text{–}6.5\text{V}$ PWM/DAC dynamic range
  - [x] Design open-drain MOSFET driver for $FG$ pulse output synthesis and NC DPDT fail-safe relay circuit
- [x] **Task 2.2: Interceptor Firmware Implementation** ✅
  - [x] Implement RP2350 embedded code under `/src/interceptor/` for dynamic $V_{\text{sp}}$ attenuation ($k = 0.68 - 1.0$)
  - [x] Implement closed-loop tachometer pulse measurement (`FG_in`) and pulse ratio synthesis (`FG_out = FG_in / k`)
  - [x] Implement active stall passthrough (`FG_out = LOW` if $f_{\text{actual}} < 10\text{ Hz}$ while $V_{\text{sp}} > 1.8\text{V}$)
  - [x] Implement Watchdog Timer (WDT) and NTC thermistor freeze override ($T_{\text{evap}} < -3^\circ\text{C}$) driving NC relay bypass
- [x] **Task 2.3: Interceptor Bench Verification** ✅
  - [x] Simulate and test interceptor board on signal test bench under `/test/test_interceptor.py` with CLI flags `-i/--input`, `-o/--output`, `-v/--verbose`

---

### Phase 3: Stage 1 Subsystem — FTC6 Indoor CN105 Thermal Load Capping ✅

- [x] **Task 3.1: Serial Interface Harness & Command Protocol Specification** ✅
  - [x] Construct JST-PA 5-pin serial interface cable for FTC6 `CN105` port
  - [x] Implement Python serial interface driver `/src/tools/cn105_controller.py` supporting `-i/--input`, `-o/--output`, `-c/--check-only`, `-v/--verbose`
- [x] **Task 3.2: Automated Nighttime Capacity Capping Script** ✅
  - [x] Develop scheduling module `/src/tools/nighttime_capper.py` to send dynamic compressor capacity cap packets during designated nighttime window (22:00–07:00)
  - [x] Validate serial telemetry readout and verify absence of FTC6 communication alarm codes

---

### Phase 4: Stage 2 Subsystem — Firmware Reverse Engineering & Decompilation ⏳

- [ ] **Task 4.1: Silicon Inspection & ID-Code Protection Gate** ⏳
  - [ ] **Task 4.1.1: Physical Pinout & Voltage Check Protocol**: Perform non-destructive visual package inspection and measure voltage levels on `EMLE`, `MD0`, `MD1`, and JTAG/SCI programming header pins on outdoor unit PCB
  - [ ] **Task 4.1.2: ID-Code Security Probing Protocol**: Perform hardware probe readout check of 128-bit ID-code location (`0xFFFFFFA0`) via E1/E20 or SCI boot loader to verify protection status (`0xFF...FF` vs. locked)
- [ ] **Task 4.2: Extract and Decompile Outdoor Unit Firmware** ⏳
  - [ ] **Task 4.2.1: Flash Readout Execution**: Connect hardware programmer (e.g. Renesas E1/E20 or SCI boot tool) and dump Code Flash ROM (`0xFFFC0000`–`0xFFFFFFFF`) into binary file `/build/puz_wm85vaa_factory.bin`
  - [x] **Task 4.2.2: Linker Script Specification**: Prepare custom Renesas RX linker script `/src/firmware/rx62t_rom.ld` mapping SRAM, SFRs, Data Flash, and Code Flash ✅
  - [x] **Task 4.2.3: Synthetic Factory Binary Generator**: Develop `/src/tools/generate_factory_rom.py` supporting CLI flags (`-o/--output`, `-c/--check-only`, `-v/--verbose`) to produce factory ROM binary for emulation testing ✅
  - [x] **Task 4.2.4: Decompiler Environment Initialization**: Initialize Ghidra v11.x project using Renesas RX processor module and load memory layout script `/src/firmware/ghidra_init_rx62t.py` ✅
- [ ] **Task 4.3: Map Fan Target RPM Tables & Closed-Loop Safety Guards** ⏳
  - [ ] **Task 4.3.1: Fan Target RPM Table Identification**: Map target RPM lookup table array at `0xFFFD4120` in Ghidra and verify 16-entry `uint16_t` matrix structure
  - [ ] **Task 4.3.2: Suction Superheat Safeguard Disassembly**: Disassemble suction superheat collapse protection subroutine ($\Delta T_{\text{SH}} < 3.5\text{ K} \implies$ ramp RPM to 1150)
  - [ ] **Task 4.3.3: Defrost Frost Gradient Safeguard Disassembly**: Disassemble defrost frost gradient evaluation routine ($T_{\text{evap}} < -4.0^\circ\text{C}$ and $\frac{dT_{\text{evap}}}{dt} < -0.3\text{ K/min} \implies \text{RPM} \ge 850$)
  - [ ] **Task 4.3.4: IPM Thermal Safeguard Disassembly**: Disassemble inverter IPM thermal override routine ($T_{\text{IPM}} > 80^\circ\text{C} \implies \text{RPM} = 1100$)

---

### Phase 5: Stage 2 Subsystem — Firmware Patching, Checksum Recalculation & Emulation ✅

- [x] **Task 5.1: Develop Patching Tooling & Apply Fan Curve Modifications** ✅
  - [x] Develop `/src/tools/patch_fan_rpm.py` supporting CLI flags (`-i/--input`, `-o/--output`, `-c/--check-only`, `-v/--verbose`)
  - [x] Patch target RPM table at `0xFFFD4120` to cap high-demand heating fan RPM from 1150 RPM to 780 RPM
- [x] **Task 5.2: CRC-16 Checksum Recalculation & ROM Validation** ✅
  - [x] Develop `/src/tools/patch_checksum.py` supporting CLI flags (`-i/--input`, `-o/--output`, `-c/--check-only`, `-v/--verbose`)
  - [x] Recalculate CRC-16-CCITT checksum over `0xFFFC0000`–`0xFFFFFF7F` and patch non-vector ROM checksum word
- [x] **Task 5.3: Automated Testing & Binary Emulation** ✅
  - [x] Run test suite under `/test/test_firmware_patch.py` verifying patch integrity and CRC validity

---

### Phase 6: Field Integration, Field Verification & Acoustic Validation ⏳

- [ ] **Task 6.1: Hardware Deployment & Reflashing** ⏳
  - [ ] **Task 6.1.1: Physical Mounting & Signal Harnessing**: Mount Stage 1 Dual-Channel Hardware Interceptor PCB on outdoor unit housing and connect inline harnesses to `CNF1` and `CNF2` connectors
  - [ ] **Task 6.1.2: Unpowered Relay Bypass Continuity Check**: Verify NC DPDT fail-safe relay unpowered bypass continuity across $V_{\text{sp}}$ and $FG$ signal lines
  - [ ] **Task 6.1.3: MCU Reflashing Procedure**: Reflash patched firmware onto Renesas RX62T MCU via programming header (if Stage 2 path is validated)
  - [ ] **Task 6.1.4: Power-On Self-Test (POST) Verification**: Perform initial power-on self-test and verify diagnostic LEDs and status flags
- [ ] **Task 6.2: Operational, Acoustic & Safety Verification** ⏳
  - [ ] **Task 6.2.1: Outdoor Acoustic Sound Pressure Measurement**: Measure outdoor sound pressure level (SPL) at 3 meters during peak heating demand using calibrated Class 1 sound level meter
  - [ ] **Task 6.2.2: Acoustic Ceiling Target Compliance**: Confirm sound pressure level remains below $35\text{ dB(A)}$ target at 3 meters under nighttime high-demand conditions
  - [ ] **Task 6.2.3: Active Defrost Cycle Field Trial**: Perform low-ambient frost chamber trial to trigger active defrost cycles and verify unconstrained airflow execution
  - [ ] **Task 6.2.4: FTC6 Fault Telemetry Audit**: Verify zero diagnostic error codes (`P8` fan tachometer fault, `P9` fan motor abnormality, or refrigerant circuit alarms)
  - [x] **Task 6.2.5: Field Test & Acoustic Validation Specification**: Compile field verification log and acoustic performance validation report in `/specification/field_test_report.md` ✅
