# Detailed Technical Design (DESIGN.md)

## 1. System Architecture & Overview

This document specifies the hardened technical design for modifying the dual outdoor fan speed control logic of the **Mitsubishi Electric Ecodan PUZ-WM85VAA** air-to-water heat pump outdoor unit (twin-fan chassis) coupled with the **FTC6** (Flow Temperature Controller 6) indoor main controller.

The architecture follows an **Inverted Staged Hybrid Approach** to maximize hardware survival and operational safety:

- **Stage 1 (Primary Execution)**: Non-invasive Dual-Channel Hardware Signal Interceptor with closed-loop thermodynamic fail-safe bypass on connectors `CNF1` and `CNF2`, combined with indoor `CN105` thermal load capping.
- **Stage 2 (Secondary / Advanced)**: Non-destructive MCU readout verification, static binary analysis, and closed-loop thermodynamic lookup table (LUT) patching on the outdoor inverter PCB (executed only if the Renesas 128-bit ID-Code protection is unlocked).

```text
+-----------------------------------------------------------------------------+
|                           FTC6 Indoor Main Board                            |
|  - CN105 Port (JST-PA 5-pin, 2400 bps, 8E1, 5V TTL) -> Telemetry & Cap      |
+--------------------------------------+--------------------------------------+
                                       |
                          S1-S2-S3 Interconnect Bus
               (S1-S2: 230V AC Power | S2-S3: 12-24V DC Opto-Loop)
                                       |
                                       v
+-----------------------------------------------------------------------------+
|                PUZ-WM85VAA Outdoor Unit Inverter Controller                 |
|                                                                             |
|  +-------------------------------+        +------------------------------+  |
|  | Renesas RX62T MCU             |        | Dual BLDC Fan Motor Drivers  |  |
|  | (R5F562T / 100-pin LQFP)      |        | (Connectors CNF1 & CNF2)     |  |
|  |                               | Vsp1/2 |                              |  |
|  | - Superheat & Defrost FSM     +------->+ - Pin 1: Vcc_HV (340V DC)    |  |
|  | - Relocatable Vector (INTB)   |        | - Pin 3: GND (0V Reference)  |  |
|  | - 128-Bit ID-Code Lock Check  | FG1/2  | - Pin 4: Vcc_Logic (15V DC)  |  |
|  | - Hardware CRC Unit           +<-------+ - Pin 5: Vsp (0-6.5V Analog) |  |
|  |                               |        | - Pin 6: FG (0-5V Tach Pulse)|  |
|  +-------------------------------+        +------------------------------+  |
+-----------------------------------------------------------------------------+
```

Refer to `TOP_ARCHITECTURE.puml` for the complete system block structure.

---

## 2. Microcontroller Architecture & Firmware Memory Maps

### 2.1 Hardware Verification Gate & Target Specifications

Before connecting any debugging probe, visual silicon inspection on the outdoor inverter PCB is mandatory to confirm the exact MCU derivative and prevent accidental flash erasure triggered by readout protection lockouts.

- **MCU Architecture**: Renesas RX62T Family (32-bit RX CPU core with single-precision hardware FPU, `R5F562TxxDFP`).
- **Clock Frequency**: Main Crystal Oscillator `X1` @ 12.000 MHz (PLL 8x multiplication for 96 MHz ICLK, 48 MHz PCLK).
- **Package**: 100-pin LQFP (14x14 mm, 0.5 mm pitch).
- **Security Gate**: Inspect the **128-bit ID-Code Protection** field at `0xFFFFFFA0`–`0xFFFFFFAF`. If armed (`!= 0xFF...FF`), blind SCI boot-mode connections will lock out or trigger automatic block erasure.

### 2.2 Memory Map Definition (Renesas RX62T — 256 KB Flash Variant)

| Memory Region          | Start Address | End Address  | Size       | Access Type  | Description                                                          |
| :--------------------- | :------------ | :----------- | :--------- | :----------- | :------------------------------------------------------------------- |
| **Internal SRAM**      | `0x00000000`  | `0x00003FFF` | 16 KB      | R/W          | Operational variables, dynamic `RPM_target`, superheat state machine |
| **Peripheral SFRs**    | `0x00080000`  | `0x0009FFFF` | 128 KB     | R/W          | ICU, MTU3 Timers, 12-bit ADC, SCI0/SCI1, Hardware CRC Unit           |
| **Data Flash (E2)**    | `0x00100000`  | `0x00107FFF` | 32 KB      | R/W (EEPROM) | Non-volatile factory calibration parameters, fault history logs      |
| **Code Flash ROM**     | `0xFFFC0000`  | `0xFFFFFF7F` | 255.875 KB | Read / Exec  | Main control firmware, relocatable vector table (`INTB`), fan LUTs   |
| **Fixed Vector Table** | `0xFFFFFF80`  | `0xFFFFFFFF` | 128 B      | Read-Only    | CPU Exceptions, 128-bit ID-Code (`0xFFFFFFA0`), Reset (`0xFFFFFFFC`) |

### 2.3 Interrupt Vector Table Layout

The Renesas RX architecture strictly separates CPU exceptions from peripheral interrupts:

1. **Fixed Vector Table (`0xFFFFFF80` – `0xFFFFFFFF`)**:
   - `0xFFFFFFA0` – `0xFFFFFFAF`: 128-bit ID-Code Protection & Option Function Select (`OFS`).
   - `0xFFFFFFD0`: Privileged Instruction Exception.
   - `0xFFFFFFE4`: Floating-Point (FPU) Exception.
   - `0xFFFFFFF8`: Non-Maskable Interrupt (NMI).
   - `0xFFFFFFFC`: Reset Vector (Entry Point `_PowerON_Reset`).
2. **Relocatable Vector Table (Base Address pointed to by CPU Register `INTB`, typically `0xFFFC0000`)**:
   - `INTB + (Vector_No * 4)`: Handles all peripheral interrupts.
   - `MTU3 TGI0A / TGI1A`: Input capture interrupts for `CNF1` and `CNF2` FG tachometer pulse measurement.
   - `MTU3 TGI2A / DAC`: `Vsp` control signal generation for Upper and Lower fan drivers.
   - `SCI0 / SCI1 RXI & TXI`: Serial communication interrupts for the opto-isolated `S2-S3` indoor/outdoor bus.

---

## 3. Firmware Reverse Engineering & Thermodynamic Patching

### 3.1 Analysis Toolchain Integration

- **Decompiler / Disassembler**: Ghidra v11.x with native Renesas RX processor module and custom SVD register definitions (`RX62T.svd`).
- **Binary Utilities**: Custom Python scripts located in `/src/tools/` supporting CLI flags (`-i`/`--input`, `-o`/`--output`, `-c`/`--check-only`, `-v`/`--verbose`).
- **Decompilation Directory**: Reconstructed C pseudocode, linker scripts (`rx62t_rom.ld`), and binary patches reside in `/src/firmware/`.

### 3.2 Coupled Electro-Thermal Fan Speed Calculation & Patch Target

In an 8.5 kW R32 heat pump, reducing fan airflow $\dot{m}_{\text{air}}$ without bounding the refrigeration cycle load causes the evaporating temperature $T_{\text{evap}}$ to plummet, inducing rapid coil frosting and liquid slugging risk. Therefore, the patched target speed $N_{\text{target}}$ (applied synchronously to both fans) is governed by a coupled electro-thermal law:

$$
N_{\text{target}} = \max \left( N_{\text{safety\_floor}}, \min \left( \text{LUT}[f_{\text{comp}}][T_{\text{ambient}}] + \Delta_{\text{mode}}, N_{\text{acoustic\_cap}}(\Delta T_{\text{SH}}, \dot{T}_{\text{evap}}) \right) \right)
$$

#### Mandatory Thermodynamic & Hardware Safety Overrides

1. **Suction Superheat Collapse Guard**: If suction superheat $\Delta T_{\text{SH}} = T_{\text{suction}} - T_{\text{evap}} < 3.5 \text{ K}$, $N_{\text{acoustic\_cap}}$ linearly ramps back to the factory ceiling (1150 RPM) OR the compressor frequency $f_{\text{comp}}$ is actively derated to maintain complete refrigerant vaporization.
2. **Defrost & Frost Gradient Protection**: If $T_{\text{evap}} < -4.0^\circ\text{C}$ and the cooling gradient $\frac{dT_{\text{evap}}}{dt} < -0.3 \text{ K/min}$ (indicating accelerating frost isolation), acoustic capping is suspended ($N_{\text{safety\_floor}} \ge 850 \text{ RPM}$). During active defrost and post-defrost drip recovery, factory LUTs run unmodified.
3. **Inverter IPM & Discharge Thermal Protection**: If Inverter Intelligent Power Module temperature $T_{\text{IPM}} > 80^\circ\text{C}$ or compressor discharge temperature $T_{\text{discharge}} > 105^\circ\text{C}$, $N_{\text{safety\_floor}} = 1100 \text{ RPM}$.

#### Patch Table Structure in Code Flash

- **Offset Location**: `TBD_STATIC_ANALYSIS` (located within `0xFFFC0000` – `0xFFFFFF7F`; exact address resolved post-dump via cross-reference analysis of ADC thermistor reads and MTU3 registers).
- **Data Structure**: 2D array of 16-bit unsigned integers (`uint16_t`) representing target RPM bounds (300 RPM to 1450 RPM).
- **Target Modification**: Lower standard heating mode nighttime/low-load ceiling from 1150 RPM down to 780 RPM (≈ -8.4 dB(A) acoustic power reduction) while enforcing a proportional compressor frequency ceiling ($f_{\text{comp}} \le 55 \text{ Hz}$).

### 3.3 Checksum and CRC Integrity Mechanisms

- **Verification Discovery**: The startup integrity check routine in `_PowerON_Reset` must be disassembled to verify the exact polynomial (typically CRC-16-CCITT, Polynomial `0x1021`, Seed `0xFFFF`), address range (`0xFFFC0000` to `END_OF_CODE`), and storage address inside the non-vector ROM space (`<= 0xFFFFFF7F`).
- **Patching Verification Tool**: `/src/tools/patch_checksum.py` recalculates the ROM checksum and validates linker section boundaries (`Start_Addr < End_Addr`) prior to flashing.

---

## 4. Hardware Interfaces & Signal Pinout Specification

### 4.1 Dual Fan Motor Interface Connectors (`CNF1` Upper Fan / `CNF2` Lower Fan)

The PUZ-WM85VAA utilizes two identical 6-pin BLDC motor interfaces. Both connectors carry lethal high-voltage DC alongside low-voltage logic:

| Pin No. | Signal Name | Type      | Voltage / Specification                             | Description                                                    |
| :------ | :---------- | :-------- | :-------------------------------------------------- | :------------------------------------------------------------- |
| **1**   | `Vcc_HV`    | HV Power  | **340V DC** (Rectified Mains Bus)                   | High-voltage DC power supply to internal BLDC inverter stage   |
| **2**   | `NC`        | Isolation | Unused / Air Gap Key Pin                            | Physical creepage/clearance isolation barrier                  |
| **3**   | `GND`       | Ground    | 0V Reference                                        | Common signal and logic ground (referenced to DC bus negative) |
| **4**   | `Vcc_Logic` | LV Power  | 15V DC ± 0.5V                                       | Internal BLDC driver IC logic power supply                     |
| **5**   | `Vsp`       | Analog In | 0V to 6.5V DC (0V=Off, 1.5V=300 RPM, 6.5V=1500 RPM) | Speed command voltage output from main board to fan motor      |
| **6**   | `FG`        | Pulse Out | 0–5V Open-Collector Pulse (4 pulses/rev)            | Tachometer feedback pulse from motor to main board MCU         |

### 4.2 Indoor Controller & Outdoor Interconnect Interfaces

- **Indoor `CN105` Interface (Located on FTC6 Main Board)**:
  - **Connector Type**: JST-PA 5-pin (2.0 mm pitch).
  - **Serial Protocol**: **2400 bps (up to 9600 bps), 8 Data bits, EVEN Parity, 1 Stop bit (8E1)**, 5V TTL Logic.
  - **Pinout**: Pin 1: +12V/+5V Supply | Pin 2: GND | Pin 3: TXD (5V) | Pin 4: RXD (5V) | Pin 5: GND/Mode.
- **Outdoor Interconnect Bus (`S1-S2-S3`)**:
  - `S1-S2`: 230V AC 50 Hz power supply.
  - `S2-S3`: 12–24V DC half-duplex opto-isolated current-loop serial communication between FTC6 and PUZ-WM85VAA.

### 4.3 DIP Switch Settings (`SW1` / `SW7` on Outdoor PCB)

| Switch  | Bit / Setting | Function                                 | Factory Default | Low-Noise Baseline                          |
| :------ | :------------ | :--------------------------------------- | :-------------- | :------------------------------------------ |
| **SW7** | Bit 1         | Outdoor Silent Mode Activation           | OFF             | ON (Enables step-down profile)              |
| **SW7** | Bit 2         | Low-Noise Priority vs. Capacity Priority | OFF             | ON (Capacity override on extreme cold)      |
| **SW1** | Bit 4         | Defrost / Frost Prevention Threshold     | OFF             | Factory Default (Preserved for coil safety) |

---

## 5. Dual-Channel Hardware Interceptor Design (Stage 1 Primary / Fallback)

Because the PUZ-WM85VAA operates two fans into a shared plenum, both `CNF1` and `CNF2` must be intercepted synchronously. Attenuating only one fan induces aerodynamic backflow stalling through the slower rotor.

```text
Main PCB (CNF1 & CNF2 Dual Channel)                             Fan Motor Harness (x2)
+------------------------+                                     +------------------------+
| Pin 1: 340V DC (HV)    +====================================>+ Pin 1: 340V DC (HV)    |
|                        |    (Isolated HV Pass-Through)       |                        |
| Pin 4: 15V DC Logic    +-----------------+------------------>+ Pin 4: 15V DC Logic    |
|                        |                 |                   |                        |
|                        |        +--------+--------+          |                        |
|                        |        | LDO (15V->3.3V) |          |                        |
|                        |        +--------+--------+          |                        |
|                        |                 | Vdd (3.3V)        |                        |
|                        |                 v                   |                        |
| Pin 5: Vsp_in (0-6.5V) +--[Div 0.50x]--->+ ADC0 PWM/PIO +--->+ OpAmp (G=2.0, 15V Rail)|
|                        |                 |              |    | +---[NC Relay Bypass]->+ Pin 5: Vsp_out
|                        |                 |    RP2350    |    |                        |
| Pin 6: FG_out (0-5V)   +<-[Open-Drain]---+ PIO    Timer +<---+-[Schmitt Trigger]------+ Pin 6: FG_in
+------------------------+                 +-------+------+    +------------------------+
                                                   |
                                      [NTC_Evap / WDT / Vsp > 5.2V]
                                                   |
                                                   +--> Drives NC Fail-Safe Relay
```

### 5.1 Hardware Signal Conditioning & Protection Specifications

1. **Input Overvoltage Attenuation (`Vsp_in` -> ADC)**:
   Since `Vsp_in` reaches 6.5V and the RP2350 operating at $V_{\text{DDIO}} = 3.3 \text{ V}$ has an absolute maximum pin rating of $V_{\text{DDIO}} + 0.3 \text{ V}$ (3.6V), a precision resistor divider ($R_1 = 10 \text{ k}\Omega$, $R_2 = 10 \text{ k}\Omega$, scaling factor 0.500) with a 3.3V Zener clamp scales 6.5V down to 3.25V prior to the 3.3V ADC input.
2. **15V OpAmp Output Restoration (PWM/DAC -> `Vsp_out`)**:
   The RP2350 PWM/DAC output (max 3.25V / 3.3V reference) cannot directly drive a 6.5V output required for 100% emergency fan speed. The output is buffered through a dual rail-to-rail operational amplifier (e.g., MCP6002 / TLV9062) powered directly from the 15V `Vcc_Logic` rail (Pin 4) with a non-inverting gain $G = 1 + \frac{R_f}{R_g} = 2.00$, restoring the full 0–6.5V dynamic range.
3. **Closed-Loop FG Pulse Synthesis & Stall Propagation**:
   To prevent `P8`/`P9` feedback mismatch faults during active attenuation ($V_{\text{sp,out}} = k \cdot V_{\text{sp,in}}$, with $k \in [0.68, 1.0]$), the MCU captures the real motor tachometer frequency $f_{\text{FG,in}}$ (via PIO / hardware timer input capture) and synthesizes $f_{\text{FG,out}} = f_{\text{FG,in}} / k$ via an open-drain MOSFET output.
   - **Critical Anti-Spoofing Rule**: If the physical fan motor stalls or fails ($f_{\text{FG,in}} < 10 \text{ Hz}$ while $V_{\text{sp,out}} > 1.8 \text{ V}$), the interceptor **immediately halts pulse synthesis** (`FG_out = LOW`), forcing the main board to register a legitimate `P8`/`P9` error and cut power before hardware damage occurs.
4. **Hardware Normally-Closed (NC) Fail-Safe Bypass**:
   A dual DPDT signal relay (or analog switch with NC contacts in the unpowered state) connects `Vsp_in` directly to `Vsp_out` and `FG_in` directly to `FG_out` whenever:
   - The interceptor loses 3.3V power or the RP2350 Watchdog Timer (WDT) trips.
   - `Vsp_in` exceeds 5.2V (indicating the main board requests high-load thermal dissipation).
   - The interceptor's clip-on evaporator NTC thermistor detects $T_{\text{evap}} < -3.0^\circ\text{C}$ (icing hazard).

---

## 6. Consolidated Evaluation of Engineering Decisions

| Decision Domain                     | Option A (Chosen)                                                                | Option B (Discarded)                                              | Option C (Discarded)                          | Selection Rationale                                                                                                                                                                                           |
| :---------------------------------- | :------------------------------------------------------------------------------- | :---------------------------------------------------------------- | :-------------------------------------------- | :------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| **1. Primary Execution Strategy**   | **Dual-Channel Closed-Loop Hardware Interceptor + Indoor `CN105` Load Cap**      | Direct Blind JTAG/SCI Flash Patching without Readout Verification | Passive Resistor Divider on `Vsp` Signal Line | Option A eliminates the risk of bricking the outdoor PCB via Renesas ID-Code protection while preserving full closed-loop safety; Option B risks flash erasure; Option C triggers immediate `P8`/`P9` faults. |
| **2. Firmware Analysis Toolchain**  | **Ghidra v11.x with Renesas RX Processor Module & Python Automation**            | IDA Pro with Proprietary RX Plugin                                | Radare2 CLI Disassembler                      | Ghidra provides deterministic C decompilation of RX memory-mapped peripherals and open-source script reproducibility in `/src/tools/`.                                                                        |
| **3. Interceptor Analog Front-End** | **0.50x Input Divider + RP2350 PWM/DAC + 15V Rail OpAmp ($G = 2.0$) + NC Relay** | Direct 6.5V Connection to 3.3V MCU Pins                           | 340V DC High-Voltage Bus PWM Chopping         | Direct 6.5V injection destroys the 3.3V MCU via ESD diode forward-biasing; 340V DC chopping causes lethal EMI and blows the internal BLDC inverter stage.                                                     |
| **4. Fault & Safety Handling**      | **Active Stall Passthrough + Evaporator NTC Override + WDT Relay Bypass**        | Continuous Blind FG Frequency Generation (Fixed Lookup)           | Permanent JTAG RAM Variable Overwriting       | Blind FG synthesis masks physical fan blockages and causes IPM thermal runaway; permanent JTAG probes suffer from EMI disconnects in outdoor heat pump chassis.                                               |
