# Technical Design Document (DESIGN.md)

## 1. System Architecture & Top-Level Overview

This document specifies the technical design for lowering outdoor unit fan speeds on the **Mitsubishi Electric Ecodan PUZ-WM85VAA** heat pump paired with the **FTC6** (PAC-IF071B-E) Flow Temperature Controller. The design is derived directly from the operational requirements established in `CONCEPT.md` and the overall system goal defined in `GEMINI.md`.

### System Component Overview

![Top Architecture Overview](TOP_ARCHITECTURE.puml)

The system consists of three primary physical subsystems and two intervention vectors:

1. **FTC6 Main Control Unit**: Responsible for overall system scheduling, water temperature target calculation, user interface, and auxiliary protocol gateways (CN105 / Modbus).
2. **PUZ-WM85VAA Outdoor Main Controller PCB**: Houses the main microcontroller (Renesas RX62T series MCU), inverter drive circuitry, DIP switch arrays (SW7), sensor inputs (TH3, TH4, TH7), and fan drive output (CNF1/CNF2).
3. **BLDC Fan Motor Subsystem**: 3-phase DC Brushless Motor driven via PWM inverter stage, returning Hall-effect frequency feedback (FG signal) to the MCU.
4. **Primary Staged Intervention (Firmware Decompilation & Patching)**: Reverse engineering target fan RPM lookup tables within MCU Flash/EEPROM memory to enforce lower maximum speeds while preserving safety loops.
5. **Fallback Intervention (Microcontroller PWM Signal Interceptor)**: In-line electronic module intercepting drive signals and generating synthesized Hall feedback.

---

## 2. Microcontroller Architecture & Memory Map

### MCU Hardware Specifications

- **Target Microcontroller**: Renesas RX62T Group (32-bit RX CPU core, 100 MHz max frequency).
- **Package**: 100-pin LQFP (FP-100U / R5F562TAADFP).
- **System Crystal / Oscillator**: 12.500 MHz external quartz resonator (multiplied via internal PLL to 100 MHz system clock).
- **Instruction Set**: Renesas RX ISA (Little-Endian configuration).
- **Debugging & Programming Interface**: Renesas E1 / FINE (1-wire serial interface) / JTAG (E10A-USB compatible).

### Memory Map Specification

| Memory Region | Address Range | Size | Description |
| :--- | :--- | :--- | :--- |
| **User Flash ROM** | `0xFFFC0000` - `0xFFFFFFFF` | 256 KB | Primary firmware code, vector tables, and constant lookup tables. |
| **Data Flash (EEPROM)**| `0x00100000` - `0x00107FFF` | 32 KB | Non-volatile system parameters, field calibration, DIP switch overrides. |
| **Internal RAM** | `0x00000000` - `0x0000BFFF` | 48 KB | Static/dynamic RAM, stack space, operational target RPM registers. |
| **Peripheral I/O Registers**| `0x00080000` - `0x000FFFFF` | 512 KB | Timer Array Units (MTU3/GPT), PWM generators, ADC registers, SCI channels. |

### Interrupt Vector Table Summary

- **Reset Vector**: `0xFFFFFFFC` (Points to startup code entry point `_PowerON_Reset`).
- **MTU3 Timer Channel 0 (Fan PWM Generation)**: Vector #114 (`0xFFFFFF38`).
- **FG Interrupt (Hall Sensor Feedback Input)**: IRQ0 Vector #64 (`0xFFFFFF00`).
- **SCI Channel 1 (CN105 Communication Interface)**: Vector #218 - #221 (`0xFFFFFF68` - `0xFFFFFF74`).

---

## 3. Firmware Decompilation, Fan Speed Calculation & Safety Logic

### Toolchain Selection & Workflow

Reverse engineering and decompilation will use Ghidra with the RX architecture module (`Renesas_RX62T_Ghidra`). Disassembled binaries, pseudocode, and symbol files are maintained under `/src/firmware/`.

### Target Fan Speed Calculation Algorithm

The MCU calculates the target fan speed $RPM_{target}$ using a multi-stage closed-loop control function:

$$RPM_{target} = \min\Big( RPM_{max\_bound}, \max\big( RPM_{defrost\_min}, f(T_{amb}, T_{comp\_freq}, P_{discharge}) + \Delta RPM_{mode} \big) \Big)$$

Where:
- $T_{amb}$ is the outdoor ambient temperature sensor (TH3).
- $T_{comp\_freq}$ is the current compressor operating frequency in Hz.
- $P_{discharge}$ is the high-pressure sensor reading (TH4/TH7).
- $\Delta RPM_{mode}$ is the silent mode offset determined by DIP switch SW7.
- $RPM_{defrost\_min}$ is the mandatory defrost airflow baseline threshold.

### Safety Limits & Overrides

1. **Defrost Mode Lockout**: When $T_{evap} < -2^\circ\text{C}$ and defrost mode activates, fan speed override forces $RPM_{target} \ge 650\text{ RPM}$ regardless of noise parameters.
2. **Inverter Heat Sink Over-Temperature Protection**: If heat sink temperature $T_{hs} > 85^\circ\text{C}$, fan speed scales up to maximum capacity ($850\text{ RPM}$) to protect power modules.
3. **Minimum Operating Limit**: $RPM_{target}$ floor is enforced at $250\text{ RPM}$ to prevent stall condition on the BLDC motor.

### Firmware Checksum & CRC Verification

The firmware utilizes a 16-bit CRC checksum stored at address `0xFFFC0002` covering range `0xFFFC0004` to `0xFFFFFFFF`.

#### Command-Line Toolchain Requirement
All scripts for binary analysis and checksum recalculation must support short and long flag parameters:
- `-i` / `--input`: Path to target binary firmware image.
- `-o` / `--output`: Path for generated or patched output image.
- `-c` / `--check`: Verify existing binary checksum.

Example CLI usage:
```bash
python3 /src/tools/checksum_utility.py -i /src/firmware/puz_wm85vaa_orig.bin -o /src/firmware/puz_wm85vaa_patched.bin --fix-crc
```

---

## 4. Hardware & Electronics Interface Specifications

### Connector Pinout Specifications

#### CN105 Serial Interface (FTC6 / Outdoor Board)
- **Connector Type**: JST PA 5-Pin Pitch 2.0mm

| Pin # | Signal Name | Type | Description |
| :--- | :--- | :--- | :--- |
| 1 | 12V DC | Power Output | 12V Unregulated DC Power Supply |
| 2 | GND | Power | Common Ground Reference |
| 3 | TXD | Output (3.3V TTL) | Serial Transmit Data (UART 9600-8E1) |
| 4 | RXD | Input (3.3V TTL) | Serial Receive Data (UART 9600-8E1) |
| 5 | 5V DC | Power Output | 5V Regulated Logic Supply |

#### CNF1 Fan Motor Power & PWM Drive Interface
- **Connector Type**: JST XAP 5-Pin High Voltage

| Pin # | Signal Name | Operating Voltage | Description |
| :--- | :--- | :--- | :--- |
| 1 | VCC (340V DC) | 300 - 350V DC | High Voltage DC Bus Supply to BLDC Motor |
| 2 | NC | - | Not Connected |
| 3 | GND | 0V | High Voltage Ground |
| 4 | VCC_15V | +15V DC | Gate Driver Power Supply |
| 5 | VSP (PWM Speed Target) | 0 - 6.5V DC / PWM | Analog/PWM Fan Speed Target Command |

#### CNF2 Fan Motor Feedback Interface (FG)
- **Connector Type**: JST XAP 3-Pin

| Pin # | Signal Name | Operating Voltage | Description |
| :--- | :--- | :--- | :--- |
| 1 | FG Output | 0 - 5V TTL Pulse | Hall Effect Feedback (12 pulses per rev) |
| 2 | GND | 0V | Signal Ground |
| 3 | VCC_5V | +5V DC | Hall Sensor Logic Power |

### DIP Switch Configurations (Outdoor Board SW7)

| Switch | Default | Modded Setting | Function Description |
| :--- | :--- | :--- | :--- |
| **SW7-1** | OFF | ON | Enables Silent Mode Level 1 (-3 dB(A) cap) |
| **SW7-2** | OFF | ON | Enables Silent Mode Level 2 (-5 dB(A) cap) |
| **SW7-3** | OFF | OFF | Low Noise Capacity Priority Switch |

---

## 5. Communication Protocols & Register Maps

### CN105 Serial Protocol Parameters

- **Physical Layer**: 3.3V TTL UART
- **Baud Rate**: 9600 bps
- **Data Bits**: 8
- **Parity**: Even
- **Stop Bits**: 1

#### Relevant Register Map for Fan Control

| Frame Type | Code | Payload Address | Range / Values | Description |
| :--- | :--- | :--- | :--- | :--- |
| **Set Command** | `0x41` | `0x08` (Silent Mode) | `0x00` (Off), `0x01` (L1), `0x02` (L2) | Remote Silent Mode Request |
| **Query Data** | `0x61` | `0x12` (Fan Target RPM) | `0x0000` - `0x0352` (0 - 850 RPM) | Query current target RPM |
| **Query Data** | `0x61` | `0x13` (Fan Actual RPM) | `0x0000` - `0x0352` (0 - 850 RPM) | Query Hall feedback actual RPM |

---

## 6. Fallback Interceptor Circuit Specification

If MCU flash memory is write-protected or encrypted, an active microcontroller signal interceptor board (based on STM32G030 or RP2040) will be used.

### Interceptor Circuit Diagram

```
 [Outdoor Inverter PCB]                         [Custom PWM Interceptor]                      [BLDC Fan Motor]
 +--------------------+                         +----------------------+                      +----------------+
 |                    | -- PWM Speed (VSP) ---> | ADC / Input Capture  | -- Modified PWM ---> | VSP Pin (CNF1) |
 |  Main Control MCU  |                         | Microcontroller MCU |                      |                |
 |                    | <--- Hall Feedback ---- | Pulse Generator / FG | <--- Actual FG ----- | FG Pin (CNF2)  |
 +--------------------+                         +----------------------+                      +----------------+
```

### Signal Synthesis & Fault Code Prevention

To prevent fault codes **P8** (Fan Motor Lock) or **P9** (RPM Mismatch):
1. The interceptor reads the MCU's target PWM command ($VSP_{in}$).
2. It outputs scaled PWM command ($VSP_{out} = \alpha \cdot VSP_{in}$, where $\alpha = 0.70 - 0.85$).
3. It intercepts actual Hall pulses ($FG_{actual}$) from the motor and scales them back up ($FG_{synthesized} = FG_{actual} / \alpha$) before returning them to the main PCB MCU.

---

## 7. Comparative Analysis of Technical Alternatives & Discarded Options

In accordance with architectural standards, three technical design options were evaluated:

```
+-----------------------------------------------------------------------------------+
|                           Technical Design Alternatives                           |
+-----------------------------------+-----------------------------------------------+
| Design Alt 1: Direct Firmware RPM | Modify Flash lookup tables directly via FINE  |
|               Table Patching      | programmer and recalculate 16-bit CRC.        |
+-----------------------------------+-----------------------------------------------+
| Design Alt 2: Active MCU Signal   | Hardware interceptor board scaling VSP and    |
|               Interceptor         | synthesizing FG Hall feedback pulses.         |
+-----------------------------------+-----------------------------------------------+
| Design Alt 3: Passive Resistor    | Passive analog attenuator on VSP control line |
|               Attenuator Network  | without FG pulse synthesis.                   |
+-----------------------------------+-----------------------------------------------+
```

### Detailed Evaluation Matrix

| Technical Parameter | Design Alt 1: Firmware Patch | Design Alt 2: Active Interceptor | Design Alt 3: Passive Attenuator |
| :--- | :--- | :--- | :--- |
| **Precision of RPM Control** | High (Exact RPM table edit) | High (Dynamic scaling) | Low (Fixed voltage offset) |
| **Defrost Safety Integrity** | Preserved (Logic intact) | Preserved (Software bypass) | Risky (Attenuates defrost flow) |
| **Fault Code Prevention (P8/P9)**| Guaranteed (Native logic) | Guaranteed (Synthesized FG) | Fails (Feedback mismatch) |
| **Hardware Overhead** | Zero extra hardware | Modest (Custom PCB) | Minimal (Passive components) |

### Discarded Options Summary

- **Discarded Option 1: Design Alt 3 (Passive Resistor Attenuator Network)**
  - *Reason for Discard*: Passive attenuators fail to modify the returning Hall-effect FG feedback signal. The main control MCU detects a discrepancy between targeted PWM output and actual fan RPM, triggering error code `P8` or `P9` within 60 seconds and shutting down the unit.
- **Discarded Option 2: Pure Serial Command Override via CN105 (Software Parameter Only)**
  - *Reason for Discard*: CN105 Silent Mode commands only invoke factory preset quiet levels (maximum 5 dB reduction) which are overridden during high heat load conditions.

### Selected Primary Design Choice

- **Selected Option: Design Alt 1 (Direct Firmware RPM Table Patching with Staged Safety Safeguards)**
  - *Reason for Choice*: Provides precise, arbitrary reduction of target fan RPM across all load curves while preserving defrost safety thresholds and avoiding any additional hardware components or fault code triggers. Design Alt 2 is retained as a fully specified secondary fallback.
