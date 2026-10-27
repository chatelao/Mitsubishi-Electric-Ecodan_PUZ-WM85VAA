# Renesas RX62T Microcontroller & Memory Architecture Specification

## 1. Overview & Silicon Specifications

The outdoor unit inverter control PCB of the **Mitsubishi Electric Ecodan PUZ-WM85VAA** heat pump is powered by a **Renesas RX62T** 32-bit microcontroller (part family `R5F562TxxDFP`).

### 1.1 Hardware Specifications

- **Core**: 32-bit RX CPU core with single-precision IEEE-754 hardware Floating-Point Unit (FPU), Harvard architecture, 5-stage pipeline.
- **Package**: 100-pin LQFP ($14 \times 14\text{ mm}$, $0.5\text{ mm}$ lead pitch).
- **Oscillator Frequency**: External crystal $X_1 = 12.000\text{ MHz}$.
- **Internal Clocks**:
  - **ICLK (CPU Clock)**: $96.0\text{ MHz}$ (via PLL $8\times$ multiplier).
  - **PCLK (Peripheral Clock)**: $48.0\text{ MHz}$ (via PLL $4\times$ multiplier).
- **Operating Voltage**: $V_{\text{CC}} = 4.5\text{V}$ to $5.5\text{V}$ (Nominal $5.0\text{V}$).

---

## 2. Memory Map & Address Allocation (256 KB Flash Variant)

| Memory Region          | Start Address | End Address  | Size       | Access Type  | Description / Hardware Assignments                                                     |
| :--------------------- | :------------ | :----------- | :--------- | :----------- | :------------------------------------------------------------------------------------- |
| **Internal SRAM**      | `0x00000000`  | `0x00003FFF` | 16 KB      | Read / Write | Variable storage, dynamic fan $N_{\text{target}}$, superheat FSM state, stack.         |
| **Peripheral SFRs**    | `0x00080000`  | `0x0009FFFF` | 128 KB     | Read / Write | ICU, MTU3 Timers (`CNF1`/`CNF2` PWM & FG capture), 12-bit ADC, SCI0/SCI1.              |
| **Data Flash (E2)**    | `0x00100000`  | `0x00107FFF` | 32 KB      | Read / Write | Non-volatile calibration values, DIP switch defaults, fault history logs.              |
| **Code Flash ROM**     | `0xFFFC0000`  | `0xFFFFFF7F` | 255.875 KB | Read / Exec  | Main firmware, relocatable vector table (`INTB`), fan lookup tables (`0xFFFD4120`).    |
| **Fixed Vector Table** | `0xFFFFFF80`  | `0xFFFFFFFF` | 128 Bytes  | Read-Only    | CPU Exceptions, 128-Bit ID-Code (`0xFFFFFFA0`), Option Function Select (`OFS`), Reset. |

---

## 3. Fixed Vector Table & Security Protection Field Layout

The top 128 bytes of flash memory (`0xFFFFFF80`–`0xFFFFFFFF`) contain critical hardware reset vectors and security fields:

```
Address Range          Size (Bytes)   Description
--------------------------------------------------------------------------------
0xFFFFFF80 - 0xFFFFFF9F   32 B        Reserved / Exception Vectors
0xFFFFFFA0 - 0xFFFFFFAF   16 B        128-Bit ID-Code Security Protection Field
0xFFFFFFB0 - 0xFFFFFFCF   32 B        Floating-Point / Privileged Instruction Exceptions
0xFFFFFFD0 - 0xFFFFFFF7   40 B        NMI & Bus Error Interrupt Vectors
0xFFFFFFF8 - 0xFFFFFFFB    4 B        Option Function Select Register 1 (OFS1)
0xFFFFFFFC - 0xFFFFFFFF    4 B        Reset Vector (_PowerON_Reset Entry Point)
```

### 3.1 128-Bit ID-Code Protection Gate (`0xFFFFFFA0`–`0xFFFFFFAF`)

- **Unlocked State**: `0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFF` (All bits `1`). SCI boot mode readout and JTAG debugger connection permitted.
- **Locked / Armed State**: Any value other than all `0xFF`. SCI boot mode attempts without providing matching 16-byte key results in complete flash erasure or serial communication lockout.
- **Mandatory Safety Rule**: Static silicon inspection and non-destructive JTAG probe readout check must verify unlocked state prior to any SCI re-flashing.

---

## 4. Interrupt Vector Architecture

1. **Relocatable Vector Table Base (`INTB` Register)**:
   - On reset, the CPU sets `INTB = 0xFFFC0000`.
   - Interrupt addresses are calculated as: $\text{Vector\_Addr} = \text{INTB} + (\text{Vector\_No} \times 4)$.
2. **Key Peripheral Interrupt Assignments**:
   - `MTU3 TGI0A / TGI1A`: Input capture interrupts measuring `CNF1` and `CNF2` tachometer $FG$ pulse inputs.
   - `MTU3 TGI2A`: Timer Compare Match generating $V_{\text{sp}}$ PWM speed commands for `CNF1`/`CNF2`.
   - `S12AD0`: 12-bit ADC conversion complete interrupt (sampling $T_{\text{evap}}$, $T_{\text{ambient}}$, $T_{\text{IPM}}$, $T_{\text{discharge}}$).
   - `SCI0`: Opto-isolated serial bus (`S2-S3`) communication interrupt.

---

## 5. References & Sources

1. **Renesas RX62T Group User's Manual: Hardware**:
   - https://www.renesas.com/en/products/microcontrollers-microprocessors/rx/rx600/rx62t
2. **Renesas RX 32-Bit MCU Architecture Overview**:
   - https://www.renesas.com/en/products/microcontrollers-microprocessors/rx
3. **Renesas Flash Programmer (RFP) & Boot Mode Flash Specifications**:
   - https://www.renesas.com/en/software-tool/renesas-flash-programmer-programming-gui
4. **Ghidra Processor Module for Renesas RX Family**:
   - https://ghidra-sre.org/
