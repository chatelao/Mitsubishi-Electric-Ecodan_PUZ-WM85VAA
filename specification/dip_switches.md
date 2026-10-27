# Outdoor Unit DIP Switch & Service Parameter Specification

## 1. Overview

The Mitsubishi Electric Ecodan PUZ-WM85VAA outdoor unit main PCB features several DIP switch blocks (`SW1`, `SW7`, `SW8`) and jumper blocks (`JMP1`) that configure factory operating modes, low-noise acoustic restrictions, demand response limits, and defrost parameters.

---

## 2. DIP Switch Configurations

### 2.1 DIP Switch `SW7`: Silent Mode & Capacity Control

`SW7` is the primary DIP switch block for outdoor acoustic noise management.

|  Bit No.  | Function                       | OFF State (Default)      | ON State                  | Operational Effect                                                                                                                                                                                                 |
| :-------: | :----------------------------- | :----------------------- | :------------------------ | :----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Bit 1** | Outdoor Silent Mode Enable     | Standard Factory Profile | **Low-Noise Mode Active** | Enforces an immediate step-down decrement on fan $N_{\text{target}}$ and caps maximum compressor frequency ($f_{\text{comp}}$) during low/moderate ambient conditions ($\approx -3\text{ dB(A)}$ noise reduction). |
| **Bit 2** | Acoustic vs. Capacity Priority | Capacity Priority        | **Acoustic Priority**     | Prevents the main board from overriding Silent Mode fan caps during high heating demand unless $T_{\text{ambient}} < -15^\circ\text{C}$ or $T_{\text{discharge}} > 105^\circ\text{C}$.                             |
| **Bit 3** | Low-Ambient Heating Boost      | Standard Target Temp     | Extended Target Boost     | Disables fan acoustic reduction under sub-zero ambient conditions to prevent evaporator icing.                                                                                                                     |
| **Bit 4** | Extended Capacity Lock         | Dynamic Scaling          | Fixed Max Capacity        | Disables all acoustic limits.                                                                                                                                                                                      |

### 2.2 DIP Switch `SW1`: Service & Operation Mode Control

`SW1` controls maintenance options, demand response overrides, and defrost cycle behavior.

|  Bit No.  | Function                     | OFF State (Default) | ON State              | Operational Effect                                                                                                                  |
| :-------: | :--------------------------- | :------------------ | :-------------------- | :---------------------------------------------------------------------------------------------------------------------------------- |
| **Bit 1** | Pump-Down Mode               | Normal Operation    | Pump-Down Active      | Forced pump-down operation for refrigerant recovery.                                                                                |
| **Bit 2** | Forced Defrost Cycle         | Normal Operation    | Forced Defrost Active | Forces instantaneous defrost cycle execution on coil thermistor $T_{\text{evap}} < 0^\circ\text{C}$.                                |
| **Bit 3** | Diagnostic LED Select        | Standard Diagnostic | Advanced Telemetry    | Selects error history readout vs. real-time sensor values on LED indicators.                                                        |
| **Bit 4** | Frost Prevention Sensitivity | Standard Threshold  | Aggressive Threshold  | Lowers frost gradient trigger threshold ($\frac{dT_{\text{evap}}}{dt}$) to initiate defrost earlier under high humidity conditions. |

---

## 3. Recommended Baseline DIP Switch Settings

For baseline low-noise operation prior to Stage 1 Interceptor deployment or Stage 2 Firmware Patching, the following DIP switch configuration is recommended:

```
Switch Block    Bit 1    Bit 2    Bit 3    Bit 4    Description
--------------------------------------------------------------------------------
SW7              ON       ON      OFF      OFF      Enables Silent Mode + Acoustic Priority
SW1             OFF      OFF      OFF      OFF      Standard Factory Defrost & Telemetry
```

- **Noise Reduction Delivered**: $\approx -3\text{ dB(A)}$ to $-5\text{ dB(A)}$ under moderate outdoor air temperatures.
- **Limitation**: Factory DIP switch presets cannot lower fan RPM below $950\text{ RPM}$ under peak heat demand, requiring the Stage 1 Dual-Channel Interceptor or Stage 2 Firmware LUT Patch to enforce the $<35\text{ dB(A)}$ ($780\text{ RPM}$) acoustic ceiling.

---

## 4. References & Sources

1. **Mitsubishi Electric PUZ-WM85VAA Service & Installation Manual**:
   - https://les.mitsubishielectric.co.uk/
2. **Mitsubishi Electric Outdoor Unit Service Handbook (DIP Switch Functions)**:
   - https://myelectricservice.mitsubishielectric.co.uk/
3. **Ecodan Selection & Technical Guide**:
   - https://ecodan.co.uk/
