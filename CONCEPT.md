# Operational Concept (CONCEPT.md)

## 1. Executive Summary & Goal Definition

The primary objective of this project is to modify the fan speed parameters, software control logic, or electronic signal interfaces of the **Mitsubishi Electric Ecodan PUZ-WM85VAA** air-to-water heat pump outdoor unit (twin-fan chassis) and its associated **FTC6** (Flow Temperature Controller 6) main controller in order to achieve lower outdoor fan speeds and reduce operational noise levels.

While the PUZ-WM85VAA is designed for high efficiency and capacity delivery, its default fan control profile can generate unacceptable acoustic noise (exceeding 50 dB(A)) in sensitive residential environments (e.g., nighttime operation, close proximity to property boundaries). This project aims to analyze, evaluate, and implement methods to control and constrain outdoor fan RPM without compromising critical heat pump safety functions (such as suction superheat collapse prevention, defrost coil airflow requirements, or inverter IPM thermal thresholds).

---

## 2. Use Cases

### UC-1: Nighttime Low-Noise Operation

- **Description**: Limit maximum fan speed during designated nighttime hours (e.g., 22:00–07:00) to keep sound pressure levels below local residential noise regulations (<35 dB(A) at 3 meters).
- **Operational Requirement**: The system must enforce an upper bound on fan RPM ($N_{\text{target}} \le 780\text{ RPM}$) while continuously monitoring evaporator temperature ($T_{\text{evap}}$) and superheat ($\Delta T_{\text{SH}}$) to prevent ice buildup or system tripping.

### UC-2: Low-Heat-Load Acoustic Optimization

- **Description**: Reduce fan speed during mild ambient conditions (above 7°C outdoor air temperature) when heating demand is minimal and full evaporator airflow is unnecessary.
- **Operational Requirement**: Dynamic scaling of target fan RPM proportional to compressor frequency ($f_{\text{comp}}$) and thermal load demand, capping fan noise proportionally during partial-load conditions.

### UC-3: Custom Low-Noise Operation Profile

- **Description**: Provide user-configurable fan speed caps or offset curves tailored to specific installation acoustic requirements, bypassing rigid factory DIP switch presets.
- **Operational Requirement**: Reconfigurable parameter storage or real-time command injection via FTC6 `CN105` serial interface or an inline hardware signal interceptor.

---

## 3. High-Level Architectural Alternatives & Comparison

To achieve the lower fan speed goal, three high-level operational approaches have been conceptualized and evaluated:

```
+-----------------------------------------------------------------------------------+
|                            High-Level Operational Approaches                      |
+-----------------------------------+-----------------------------------------------+
| Approach 1: Software / Parameter  | Utilize native DIP switches (SW1/SW7), FTC6   |
|             Configuration & Cap   | service parameters, or CN105 serial capping.  |
+-----------------------------------+-----------------------------------------------+
| Approach 2: Dual-Channel Hardware | Intercept and attenuate Vsp signals on CNF1 & |
|             Signal Interceptor    | CNF2 while synthesizing FG pulses (ATtiny).   |
+-----------------------------------+-----------------------------------------------+
| Approach 3: Firmware Reverse Eng. | Read Renesas RX62T MCU flash, patch fan LUTs, |
|             & Logic Modification  | recalculate CRC-16, and reflash ROM.          |
+-----------------------------------+-----------------------------------------------+
```

### Approach 1: Software / Parameter Configuration & Thermal Load Capping

- **Mechanism**: Leverage factory-provided DIP switches (`SW7` Silent Mode bits, `SW1` demand control), FTC6 initial setting parameters, or serial control commands via the indoor `CN105` port (JST-PA 5-pin, 2400/9600 bps, 8E1) to restrict thermal load demand and fan speed targets.
- **Pros**: Non-invasive, preserves warranty/hardware integrity, zero risk of damaging electronics or bricking MCU flash.
- **Cons**: Limited flexibility; factory "Silent Mode" provided by `SW7` only reduces fan RPM by fixed step decrements (3–5 dB(A)) during low ambient demand and cannot enforce explicit acoustic limits under high heat loads.

### Approach 2: Dual-Channel Hardware Signal Interceptor (Stage 1 Primary)

- **Mechanism**: Place an inline microcontroller board (ATtiny1616-based) between the main inverter control PCB and both DC brushless fan motor connectors (`CNF1` Upper and `CNF2` Lower). The module attenuates analog speed command voltages ($V_{\text{sp}}$, 0–6.5V) while capturing actual motor tachometer pulses ($FG$) and synthesizing proportional $FG$ feedback pulses ($f_{\text{synth}} = f_{\text{actual}} / k$) to the main board MCU to prevent `P8`/`P9` feedback mismatch fault codes. An electro-thermal fail-safe relay bypasses intervention if $T_{\text{evap}} < -3^\circ\text{C}$ or $V_{\text{sp}} > 5.2\text{V}$.
- **Pros**: Direct control over fan motor speed independent of MCU flash protection or locking mechanisms; fully reversible; eliminates MCU bricking risks.
- **Cons**: Requires custom PCB hardware development and dual-channel signal conditioning; requires careful $FG$ pulse synthesis to avoid diagnostic trips.

### Approach 3: Firmware Reverse Engineering & Logic Modification (Stage 2 Advanced)

- **Mechanism**: Verify Renesas RX62T 128-bit ID-Code security state (`0xFFFFFFA0`), extract binary firmware from the outdoor inverter PCB code flash (`0xFFFC0000`–`0xFFFFFFFF`), decompile in Ghidra v11.x, locate target fan RPM lookup tables (`0xFFFD4120`), patch target RPM curves (lowering 1150 RPM ceiling to 780 RPM) while preserving superheat collapse and defrost safety overrides, recompute CRC-16-CCITT checksums, and reflash the MCU.
- **Pros**: Cleanest operational integration; preserves internal closed-loop safety logic natively; allows surgical, multi-variable dynamic scaling.
- **Cons**: High initial analysis complexity; potential risk of MCU write protection or lockouts (128-bit ID-code); requires hardware programming tooling.

---

## 4. Evaluation and Selected Strategy

### Evaluation Criteria Matrix

| Criterion                                  | Approach 1: Software Config & Cap | Approach 2: Hardware Interceptor          | Approach 3: Firmware Patching   |
| :----------------------------------------- | :-------------------------------- | :---------------------------------------- | :------------------------------ |
| **Acoustic Reduction Control**             | Low / Medium (Preset limits)      | High (Direct $V_{\text{sp}}$ attenuation) | High (Precise LUT tuning)       |
| **System Safety & Stability**              | High (Factory safeguards intact)  | High (NC Relay & NTC fail-safe)           | High (Preserves safety bounds)  |
| **Reversibility / Non-invasiveness**       | High                              | High (Plug-and-play harness)              | Medium (Requires reflashing)    |
| **Implementation Complexity**              | Low                               | Medium                                    | High                            |
| **Risk of Fault Codes (P8/P9 / Bricking)** | None                              | Low (Synthesized $FG$ closed-loop)        | Low (Post ID-code verification) |

### Chosen Strategy: Inverted Staged Hybrid Approach

1. **Stage 1 (Primary Execution)**: **Dual-Channel Hardware Signal Interceptor + Indoor CN105 Thermal Capping**.
   - To eliminate the risk of bricking the outdoor inverter MCU due to Renesas 128-bit ID-Code protection (`0xFFFFFFA0`), Stage 1 deploys a non-invasive dual-channel signal interceptor on `CNF1` and `CNF2` combined with indoor `CN105` thermal load capping. This achieves immediate, reliable acoustic reduction (<35 dB(A) nighttime ceiling) while incorporating hardware fail-safe relays driven by watchdog timers and evaporator thermistor ($T_{\text{evap}}$) monitoring.

2. **Stage 2 (Secondary / Advanced Execution)**: **MCU Readout Verification & Closed-Loop Firmware Patching**.
   - If silicon inspection and non-destructive debug connections confirm the 128-bit ID-Code field is unlocked (`0xFF...FF`), Stage 2 extracts the code flash, patches the fan target lookup table (`0xFFFD4120`), recalculates the CRC-16 checksum via `/src/tools/patch_checksum.py`, and reflashes the Renesas RX62T MCU to embed acoustic limits natively into the system logic.

---

## 5. Discarded & Alternative Options Summary

In accordance with project design standards, every major engineering decision domain is evaluated across three explicit alternatives, with chosen and discarded choices documented below:

### Decision Domain 1: Primary Execution Strategy

- **Chosen Option: Dual-Channel Closed-Loop Hardware Interceptor + Indoor CN105 Load Cap (Option A)**
  - _Reason for Choice_: Provides immediate acoustic reduction while guaranteeing zero risk of bricking the MCU flash or triggering ID-code lockout.
- **Discarded Alternative 1: Direct Blind JTAG/SCI Flash Patching without Readout Verification (Option B)**
  - _Reason for Discard_: If the Renesas 128-bit ID-Code protection at `0xFFFFFFA0` is active, blind SCI/JTAG connection attempts trigger automatic MCU flash block erasure or permanent readout lockout.
- **Discarded Alternative 2: Passive Resistor Divider on $V_{\text{sp}}$ Signal Line (Option C)**
  - _Reason for Discard_: Passive voltage division on $V_{\text{sp}}$ alters motor RPM without adjusting feedback, causing an immediate mismatch with actual tachometer $FG$ pulses and triggering diagnostic fault codes `P8`/`P9`.

### Decision Domain 2: Firmware Analysis & Modulation Toolchain

- **Chosen Option: Ghidra v11.x with Renesas RX Processor Module & Python Automation (Option A)**
  - _Reason for Choice_: Open-source, deterministic C decompilation for the 32-bit Renesas RX architecture, supporting automated Python scripts in `/src/tools/` for reproducible analysis and patching.
- **Discarded Alternative 1: IDA Pro with Proprietary RX Plugin (Option B)**
  - _Reason for Discard_: High licensing cost and non-reproducible environment for automated open-source CI/CD workflows.
- **Discarded Alternative 2: Radare2 CLI Disassembler (Option C)**
  - _Reason for Discard_: Inferior decompilation output for complex Renesas RX control loops and multi-variable lookup tables compared to Ghidra's C pseudocode AST.

### Decision Domain 3: Interceptor Signal Conditioning Front-End

- **Chosen Option: 0.68x Input Divider + ATtiny1616 DAC + 15V Rail OpAmp ($G=1.5$) + NC Relay Bypass (Option A)**
  - _Reason for Choice_: Safely attenuates $6.5\text{V}$ $V_{\text{sp}}$ down to $4.47\text{V}$ for the 5V ATtiny1616 ADC, while the 15V-powered rail-to-rail OpAmp restores full $0\text{–}6.5\text{V}$ dynamic range for 100% emergency fan override.
- **Discarded Alternative 1: Direct 6.5V Signal Connection to 5V MCU Pins (Option B)**
  - _Reason for Discard_: Exceeds ATtiny1616 absolute maximum pin ratings ($V_{\text{DD}} + 0.5\text{V} = 5.5\text{V}$), forward-biasing internal ESD diodes and causing MCU latch-up or silicon destruction.
- **Discarded Alternative 2: 340V DC High-Voltage Bus PWM Chopping (Option C)**
  - _Reason for Discard_: Chopping the high-voltage DC bus generates severe electromagnetic interference (EMI) and damages internal BLDC motor driver ICs.

### Decision Domain 4: Fault Handling & Safety Bypass Mechanisms

- **Chosen Option: Active Stall Passthrough + Evaporator NTC Override + Watchdog Relay Bypass (Option A)**
  - _Reason for Choice_: Guarantees physical fan motor failures pass through directly as genuine `P8`/`P9` fault trips, preventing IPM thermal runaway while NC relays restore factory operation on system faults or freeze detection ($T_{\text{evap}} < -3^\circ\text{C}$).
- **Discarded Alternative 1: Continuous Blind $FG$ Frequency Generation / Fixed Lookup (Option B)**
  - _Reason for Discard_: Spoofing valid $FG$ signals during a physical fan lockup masks fan failure from the main MCU, causing catastrophic IPM thermal overload and inverter failure.
- **Discarded Alternative 2: Permanent JTAG RAM Variable Overwriting (Option C)**
  - _Reason for Discard_: Running active JTAG hardware debug probes inside an outdoor heat pump enclosure suffers from severe EMI disconnects and vibration failures.
