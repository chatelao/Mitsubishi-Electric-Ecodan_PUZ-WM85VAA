# Operational Concept (CONCEPT.md)

## 1. Executive Summary & Goal Definition

The primary objective of this project is to modify the fan speed parameters, software control logic, or electronic signal interfaces of the **Mitsubishi Electric Ecodan PUZ-WM85VAA** air-to-water heat pump outdoor unit and its associated **FTC6** (Flow Temperature Controller 6) main controller in order to achieve lower outdoor fan speeds and reduce operational noise levels.

While the PUZ-WM85VAA is designed for high efficiency and capacity delivery, its default fan control profile can generate unacceptable acoustic noise in sensitive residential environments (e.g., nighttime operation, close proximity to property boundaries). This project aims to analyze, evaluate, and implement methods to control and constrain outdoor fan RPM without compromising critical heat pump safety functions (such as defrost air flow requirements or inverter cooling thresholds).

---

## 2. Use Cases

### UC-1: Nighttime Low-Noise Operation

- **Description**: Limit maximum fan speed during designated nighttime hours (e.g., 22:00–07:00) to keep sound pressure levels below local residential noise regulations (e.g., \<35 dB(A) at 3 meters).
- **Operational Requirement**: The system must enforce an upper bound on fan RPM while monitoring evaporator temperature to prevent ice buildup or system tripping.

### UC-2: Low-Heat-Load Acoustic Optimization

- **Description**: Reduce fan speed during mild ambient conditions (above 7°C outdoor air temperature) when heating demand is minimal and full evaporator airflow is unnecessary.
- **Operational Requirement**: Dynamic scaling of target fan RPM proportional to compressor frequency and thermal load demand.

### UC-3: Custom Low-Noise Operation Profile

- **Description**: Provide user-configurable fan speed caps or offset curves tailored to specific installation acoustic requirements, bypassing standard factory presets.
- **Operational Requirement**: Reconfigurable parameter storage or real-time command injection via auxiliary interfaces.

---

## 3. High-Level Architectural Alternatives & Comparison

To achieve the lower fan speed goal, three high-level operational approaches have been conceptualized and evaluated:

| High-Level Operational Approach                            | Summary & Mechanism                                                                          |
| :--------------------------------------------------------- | :------------------------------------------------------------------------------------------- |
| **Approach 1: Software / Parameter Configuration**         | Utilize native DIP switch settings, FTC6 service menu codes, or CN105/Modbus commands.       |
| **Approach 2: Electronics / Hardware Modification**        | Intercept and modify PWM/RPM signals between main PCB and DC fan motor using custom circuit. |
| **Approach 3: Firmware Reverse Eng. & Logic Modification** | Decompile, patch, and reflash PUZ-WM85VAA or FTC6 MCU firmware fan target tables.            |

### Approach 1: Software / Parameter Configuration

- **Mechanism**: Leverage factory-provided DIP switches (e.g., Silent Mode / Low Noise mode jumpers on PUZ outdoor main board), FTC6 initial settings parameters, or serial control commands (CN105 / M-Net / Modbus).
- **Pros**: Non-invasive, preserves warranty/hardware integrity, minimal risk of damaging electronics.
- **Cons**: Limited flexibility; factory "Silent Mode" often restricts maximum heating output capacity or has a fixed step reduction that may not satisfy specific acoustic requirements.

### Approach 2: Electronics / Hardware Modification

- **Mechanism**: Place an inline electronic module (e.g., microcontroller-based PWM signal manipulator, resistor attenuator, or feedback signal override) between the main inverter control PCB and the DC brushless fan motor connector (CNF1/CNF2).
- **Pros**: Direct control over actual motor speed regardless of software constraints; independent of firmware checksums or locking mechanisms.
- **Cons**: Requires custom PCB development; risk of triggering motor loss-of-sync or feedback error codes (e.g., fan motor feedback RPM mismatch fault code `P8` or `P9`); high hardware intervention risk.

### Approach 3: Firmware Reverse Engineering & Logic Modification

- **Mechanism**: Extract binary firmware from the PUZ-WM85VAA outdoor unit main controller (or FTC6 board), decompile and locate the fan speed calculation routines and target RPM lookup tables, patch the control logic to lower target RPM curves, recalculate CRCs/checksums, and reflash the MCU.
- **Pros**: Cleanest operational integration; preserves internal closed-loop safety logic while adjusting speed thresholds precisely; allows sophisticated dynamic scaling.
- **Cons**: High initial analysis complexity; requires MCU hardware programmer/debugger tooling; risk of bricking MCU if flashing fails.

---

## 4. Evaluation and Selected Strategy

### Evaluation Criteria Matrix

| Criterion                            | Approach 1: Software Config      | Approach 2: Hardware Mod       | Approach 3: Firmware Patching  |
| :----------------------------------- | :------------------------------- | :----------------------------- | :----------------------------- |
| **Acoustic Reduction Control**       | Low / Medium (Preset limits)     | High (Direct motor control)    | High (Precise curve tuning)    |
| **System Safety & Stability**        | High (Factory safeguards intact) | Low (Bypasses feedback safety) | High (Preserves safety bounds) |
| **Reversibility / Non-invasiveness** | High                             | Low                            | Medium                         |
| **Implementation Complexity**        | Low                              | Medium                         | High                           |
| **Risk of Fault Codes (E.g. P8/P9)** | None                             | High                           | Low                            |

### Chosen Approach: Staged Hybrid Strategy (Approach 1 -> Approach 3)

1. **Primary Selected Approach**: **Firmware Reverse Engineering & Software Parameter Modification (Hybrid Approach 1 & 3)**.
   - We select software and firmware reverse engineering as the primary strategy. By understanding the firmware's fan control algorithms and MCU registers, we can either reconfigure software parameters to their true limit or apply direct, surgical patches to the target fan RPM calculation tables in firmware. This guarantees system safety checks (such as defrost cycle minimum airflow and heat exchanger over-temperature prevention) remain operational while extending noise-reduction ranges.

2. **Secondary / Fallback Approach**: **Electronics / Hardware Interceptor (Approach 2)**.
   - If firmware write-protection or proprietary MCU lockdown prevents reflashing, an electronic signal interceptor board will serve as a secondary fallback.

---

## 5. Discarded & Alternative Options Summary

As required by repository design rules, all major choices and discarded alternatives are summarized below:

- **Discarded Alternative 1: Static Analog Voltage / Resistor Attenuation (Electronics Modification)**
  - _Reason for Discard_: Brushless DC (BLDC) fan motors in the PUZ-WM85VAA utilize active Hall-effect feedback signals to the controller. Passive signal attenuation disrupts feedback, triggering immediate diagnostic fault codes and shutdown.
- **Discarded Alternative 2: Pure Factory DIP Switch Configuration (Software Parameter Configuration)**
  - _Reason for Discard_: Factory Silent Mode settings provided by SW7/DIP switch configurations only lower the maximum speed by a fixed percentage during low-ambient conditions, which fails to meet the required noise reduction at high heat load or during low-load operation.
- **Chosen Alternative: Firmware Target Table Patching with Safety Logic Integrity**
  - _Reason for Choice_: Provides complete, precise control over the fan RPM target curve across all operating conditions while maintaining native defrost and thermal protection logic.
