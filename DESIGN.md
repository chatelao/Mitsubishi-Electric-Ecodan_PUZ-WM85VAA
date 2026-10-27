# Detailed Technical Design (DESIGN.md)

## 1. System Architecture & Overview

This document specifies the technical design for modifying the outdoor fan speed control logic of the **Mitsubishi Electric Ecodan PUZ-WM85VAA** air-to-water heat pump outdoor unit controlled by the **FTC6** (Flow Temperature Controller 6) main controller.

The chosen strategy is a **Staged Hybrid Approach** (Primary: Firmware Analysis & Software Patching; Secondary Fallback: Microcontroller Signal Interceptor Hardware), derived directly from `CONCEPT.md`.

```
                  +---------------------------------------------------+
                  |                 FTC6 Main Board                   |
                  |         (Serial Command / CN105 Interface)        |
                  +-------------------------+-------------------------+
                                            |
                                  CN105 Serial Protocol
                                 (1200 / 9600 Baud UART)
                                            |
                                            v
+-----------------------------------------------------------------------------------+
|                        PUZ-WM85VAA Outdoor Unit Main Board                        |
|                                                                                   |
|  +----------------------------+             +----------------------------------+  |
|  |  Microcontroller Unit      |             | Fan Motor Drive Circuit          |  |
|  |  (Renesas RX62T / M16C 32B)  |             | (Connector CNF1 / CNF2)          |  |
|  |                            |   Vsp/PWM   |                                  |  |
|  |  - Fan Target RPM Lookup   +------------>+ - Vcc: 340V DC                   |  |
|  |  - Safety Bounds & Defrost |             | - Vcc_logic: 15V DC              |  |
|  |  - CRC / Checksum Logic    |   FG Feedback| - Vsp: 0-6.5V DC (0-1500 RPM)    |  |
|  |                            |<------------+ - FG Feedback: 4 pulses/rev      |  |
|  +----------------------------+             +----------------------------------+  |
+-----------------------------------------------------------------------------------+
```

Refer to `TOP_ARCHITECTURE.puml` for the complete diagram structure.

---

## 2. Microcontroller Architecture & Firmware Memory Maps

### 2.1 MCU Target Hardware Specifications
- **MCU Architecture**: Renesas RX62T Family (32-bit RX CPU core with hardware FPU / DSP instructions) or Renesas M16C/64 Series.
- **Clock Frequency**: Main crystal Oscillator `X1` @ 12.000 MHz (PLL 8x scaling for 96 MHz ICLK, 48 MHz PCLK).
- **Package**: 100-pin LQFP (14x14mm, 0.5mm pitch).
- **Internal Storage**:
  - **Flash ROM**: 256 KB (0xFFFC0000 - 0xFFFFFFFF)
  - **Data Flash (EEPROM)**: 32 KB (0x00100000 - 0x00107FFF)
  - **SRAM**: 16 KB (0x00000000 - 0x00003FFF)

### 2.2 Memory Map Definition

| Memory Region | Start Address | End Address | Size | Access Type | Description |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **RAM** | `0x00000000` | `0x00003FFF` | 16 KB | R/W | Operational variables, dynamic fan target RPM, fault flags |
| **Data Flash** | `0x00100000` | `0x00107FFF` | 32 KB | R/W (EEPROM)| Factory calibration parameters, DIP switch overrides, user offsets |
| **Peripheral SFRs** | `0x00080000` | `0x0008FFFF` | 64 KB | R/W | Special Function Registers (MTU3 Timers, UART, ADC) |
| **Vector Table** | `0xFFFFFF80` | `0xFFFFFFFF` | 128 B | Read-Only | Interrupt and Reset Vector addresses |
| **Firmware Flash** | `0xFFFC0000` | `0xFFFBFFFF` | 256 KB | Read-Only | Decompiled control firmware, fan lookup tables, safety logic |

### 2.3 Vector Table Layout
- `0xFFFFFFFC`: Reset Vector (Entry Point `_start`)
- `0xFFFFFFE0`: MTU3 Channel 0 (PWM Fan Generation Interrupt)
- `0xFFFFFFE4`: MTU3 Channel 1 (FG Frequency Counter Input Capture Interrupt)
- `0xFFFFFFB0`: SCI1 RXI (Serial Communication / CN105 RX Interrupt)

---

## 3. Firmware Reverse Engineering & Patching Toolchain

### 3.1 Analysis Toolchain Integration
- **Decompiler / Disassembler**: Ghidra v10.x / radare2 with RX62T CPU plugin definition.
- **Binary Utilities**: Custom Python scripts located in `/src/tools/` supporting CLI arguments (`-i`/`--input`, `-o`/`--output`, `-v`/`--verbose`).
- **Decompilation Directory**: Processed pseudocode and patched assembly source resides in `/src/firmware/`.

### 3.2 Fan Speed Target RPM Calculation Algorithm & Patch Target

The outdoor fan motor speed $N_{\text{target}}$ (in RPM) is calculated as a function of compressor operating frequency $f_{\text{comp}}$, outdoor ambient temperature $T_{\text{ambient}}$, evaporator heat exchanger temperature $T_{\text{evap}}$, and active mode (Heating, Cooling, Defrost, Silent).

$$\text{RPM}_{\text{target}} = \min \left( \text{LookupTable}[f_{\text{comp}}][T_{\text{ambient}}] + \Delta_{\text{mode}}, \, \text{RPM}_{\text{cap}} \right)$$

#### Safety Threshold Rules (Preserved during Patching)
1. **Defrost Cycle Protection**: If $T_{\text{evap}} < -5^\circ\text{C}$ and Defrost Flag == Active, $\text{RPM}_{\text{target}} \ge 850\text{ RPM}$ (Mandatory minimum airflow to prevent coil icing).
2. **Inverter IPM Thermal Protection**: If $T_{\text{IPM}} > 85^\circ\text{C}$, $\text{RPM}_{\text{target}} = \max(\text{RPM}_{\text{target}}, 1100\text{ RPM})$.

#### Patch Table Structure in Flash
- **Offset Location**: `0xFFFD4120` in Flash ROM.
- **Data Table**: Array of 16-bit unsigned integers representing target RPM bounds (300 RPM to 1450 RPM).
- **Target Modification**: Cap standard heating mode target RPM from max 1150 RPM down to 780 RPM during low-ambient / nighttime operational profiles.

### 3.3 Checksum and CRC Integrity Mechanisms
The Renesas firmware binary uses a 16-bit CRC algorithm (CCITT-16, Polynomial `0x1021`, Initial Value `0xFFFF`) over address range `0xFFFC0000` to `0xFFFFFFBD`. The calculated CRC is stored at address `0xFFFFFFBE`.

- **Patching Verification Tool**: `/src/tools/patch_checksum.py`
  - CLI Flags: `-i / --input`, `-o / --output`, `-c / --check-only`
  - Recalculates CRC16 and injects value prior to EEPROM/Flash reprogramming.

---

## 4. Hardware Interfaces & Signal Pinout Specification

### 4.1 Fan Motor Interface Connector (CNF1 / CNF2)
The PUZ-WM85VAA uses a 5-pin / 6-pin BLDC motor interface (Nidec / Matsushita direct DC drive):

| Pin No. | Signal Name | Type | Voltage / Specification | Description |
| :--- | :--- | :--- | :--- | :--- |
| **1** | `Vcc_HV` | Power | 340V DC (High Voltage DC Bus) | Direct rectified DC power supply to motor coils |
| **2** | `NC` | - | Unused / Key Pin | Physical key isolation |
| **3** | `GND` | Ground | 0V Reference | Common signal and power ground |
| **4** | `Vcc_Logic`| Power | 15V DC $\pm 0.5\text{V}$ | Internal BLDC driver control circuit power |
| **5** | `Vsp` | Analog Control | 0V to 6.5V DC (0V = Off, 1.5V = 300 RPM, 6.5V = 1500 RPM) | Speed control voltage signal from main board MCU |
| **6** | `FG` | Pulse Output | 0–5V Square Wave (4 pulses per revolution) | Feedback pulse for speed monitoring & fault detection |

### 4.2 Serial Communication Interface (CN105)
- **Connector Type**: JST-PA 5-pin (2.0mm pitch).
- **Baud Rate**: 2400 bps / 9600 bps, 8 Data bits, No Parity, 1 Stop bit (8N1).
- **Pinout**:
  - Pin 1: 12V DC Supply
  - Pin 2: GND
  - Pin 3: RXD (3.3V TTL)
  - Pin 4: TXD (3.3V TTL)
  - Pin 5: Mode / Handshake

### 4.3 DIP Switch Settings (SW1 / SW7) Overview

| Switch | Bit / Setting | Function | Default | Custom Low-Noise Setting |
| :--- | :--- | :--- | :--- | :--- |
| **SW7** | Bit 1 | Silent Mode Level 1 (-3 dB(A)) | OFF | ON |
| **SW7** | Bit 2 | Silent Mode Level 2 (-5 dB(A)) | OFF | ON |
| **SW1** | Bit 4 | Demand Control Override | OFF | Configured via Firmware |

---

## 5. Fallback Hardware Interceptor Subsystem Design

In the event that firmware reflashing is restricted by MCU readout protection, an inline signal interceptor module is inserted between Connector `CNF1` on the main PCB and the motor harness.

```
+-------------------+        Vsp (0-6.5V)        +-------------------+
|                   +--------------------------->+ Analog ADC In     |
| Main PCB          |                            |                   |
| Connector CNF1    |        FG Pulse            | ATtiny1616 MCU    |
|                   +<---------------------------+ Pulse Synthesizer |
+-------------------+                            +---------+---------+
                                                           | Vsp_attenuated (0-4.5V)
                                                           v
                                                 +-------------------+
                                                 | Fan Motor Harness |
                                                 +-------------------+
```

### Hardware Circuit Components
- **MCU**: Microchip ATtiny1616 (16 KB Flash, 8-bit, low-power).
- **Vsp Manipulation**: ADC input sample $V_{\text{sp,in}}$ scaled down via internal DAC / RC low-pass filtered PWM output to yield $V_{\text{sp,out}} = k \cdot V_{\text{sp,in}}$ (where $k = 0.65$ to $0.80$).
- **FG Feedback Synthesizer**: To prevent `P8`/`P9` fan motor feedback error codes, the interceptor captures actual FG pulses, scales frequency $f_{\text{synth}} = f_{\text{actual}} / k$, and injects synthetically correct FG pulses back to the main PCB MCU.

---

## 6. Implementation Choices & Evaluated Alternatives

As mandated by design standards, every major implementation decision is evaluated across three alternatives, with chosen and discarded options detailed below:

### Decision 1: Firmware Analysis Toolchain Selection

- **Alternative A**: **Ghidra with Custom Renesas RX CPU Architecture Plugin (CHOSEN)**
  - *Description*: Open-source SRE framework with multi-user support, full decompilation to C pseudocode, and extensible Python/Java API for automated lookup table identification.
  - *Reason for Choice*: Provides full pseudocode reconstruction of memory-mapped I/O routines and enables reproducible scripting in `/src/tools/`.
- **Alternative B**: **IDA Pro with RX Architecture License**
  - *Description*: Industry standard disassembler.
  - *Reason for Discard*: Prohibitive licensing constraints for non-proprietary reproduction; limited automated C scripting capabilities across non-licensed environments.
- **Alternative C**: **Radare2 / Cutter CLI Utilities**
  - *Description*: Lightweight command-line binary analysis tool.
  - *Reason for Discard*: Inferior decompilation quality for Renesas RX complex address modes, leading to higher manual disassembly overhead.

### Decision 2: Fan Speed Override Signal Modulation Strategy (Hardware Fallback)

- **Alternative A**: **Active Dual-Microcontroller Vsp Attenuation & Synthetic FG Interception (CHOSEN)**
  - *Description*: Intercept $V_{\text{sp}}$ control voltage with ATtiny MCU and generate a synthetically matched $FG_{\text{return}}$ signal back to the main PCB to satisfy feedback checks.
  - *Reason for Choice*: Solves both motor speed reduction and `P8`/`P9` fault code prevention reliably.
- **Alternative B**: **Passive Resistor Divider on Vsp Line**
  - *Description*: Inline resistor attenuator to lower control voltage.
  - *Reason for Discard*: Disruption of expected FG feedback ratio triggers immediate system diagnostic fault code `P8` (Fan Motor Lock/Mismatch) and system shutdown.
- **Alternative C**: **Direct PWM Chopping via High-Voltage MOSFET on DC Bus Line**
  - *Description*: Pulse-width modulate the 340V High Voltage supply line ($V_{cc\_HV}$).
  - *Reason for Discard*: Extremely high hardware risk, high EMI, risk of motor inverter driver failure and electrical damage.

### Decision 3: Code Modification & Patching Mechanism

- **Alternative A**: **Direct Table Patching & CRC Recalculation in Flash ROM (CHOSEN)**
  - *Description*: Locate static target RPM lookup arrays in Flash ROM, modify target values, recalculate CRC16, and rewrite Flash block.
  - *Reason for Choice*: Cleanest integration; preserves internal closed-loop safety logic (defrost, over-temp) while enforcing lower target limits.
- **Alternative B**: **RAM Hooking via JTAG / SWD Debugger Interface**
  - *Description*: Attach permanent JTAG probe to continuously overwrite RAM variable `RPM_target_var` at address `0x00001240`.
  - *Reason for Discard*: Requires expensive permanently attached debugging hardware, vulnerable to electrical noise and power cycle disconnections.
- **Alternative C**: **CN105 Serial Command Injection Polling**
  - *Description*: Send continuous CN105 serial packets requesting Silent Mode / Fan Speed Overrides every 500ms.
  - *Reason for Discard*: CN105 protocol limits minimum fan speed to preset factory step levels (maximum reduction of ~200 RPM), failing nighttime acoustic targets (<35 dB(A)).

---

## 7. Summary of Discarded Alternatives

1. **IDA Pro Disassembler**: Discarded in favor of Ghidra due to open-source toolchain requirements and script reproducibility.
2. **Passive Resistor Divider Attenuation**: Discarded due to triggering `P8`/`P9` motor feedback fault codes.
3. **High-Voltage 340V DC Line Chopping**: Discarded due to severe safety risks, electrical noise, and high risk of motor driver damage.
4. **Permanent JTAG Debugger RAM Hooking**: Discarded due to poor operational reliability and hardware overhead.
5. **Continuous CN105 Serial Override**: Discarded due to hardcoded parameter limits within stock factory firmware.
