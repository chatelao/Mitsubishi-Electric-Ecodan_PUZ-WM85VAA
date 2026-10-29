# Physical Pinout & Voltage Check Protocol Specification (`physical_inspection_protocol.md`)

This specification details the non-destructive physical package inspection, operating mode pin states, voltage measurement check procedures, and safety lockout protocols for the **Renesas RX62T** microcontroller (`R5F562TxxDFP`) on the **Mitsubishi Electric Ecodan PUZ-WM85VAA** outdoor unit inverter PCB.

---

## 1. Executive Summary & Scope

Before connecting any hardware programmer or diagnostic interface (e.g., Renesas E1/E20 emulator or USB-to-UART converter) to the outdoor unit PCB, physical package verification and pin voltage measurement must be performed.

This protocol guarantees:

1. **Silicon Identification**: Visual verification of the Renesas RX62T 100-pin LQFP chip marking.
2. **Mode Pin Configuration**: Proper state setup of `MD0`, `MD1`, and `EMLE` pins to enter User Boot Mode or SCI Boot Mode without tripping silicon hardware lockouts.
3. **Power Rail Integrity**: Verification of 5.0V $V_{\text{CC}}$ logic rails, analog supply ($AV_{\text{CC0}}$), and reference voltage rails prior to probe attached state.
4. **Readout Security Safeguard**: Prevention of unexpected flash erasure triggered by connecting an active SCI bootloader to an ID-code locked MCU.

---

## 2. Visual Package Inspection & Chip Marking Verification

### 2.1 Chip Markings and Package Layout

- **Package Type**: 100-pin LQFP ($14 \times 14\text{ mm}$, $0.5\text{ mm}$ pin pitch).
- **Part Number**: `R5F562TxxDFP` (e.g., `R5F562T6EDFP` or `R5F562TAEDFP`, 256 KB Code Flash variant).
- **Top Marking Layout**:
  - Line 1: `R5F562T6EDFP` or `R5F562TAEDFP`
  - Line 2: Renesas logo and 3-digit mask / lot code (e.g., `245A12`)
  - Pin 1 Indicator: Laser-etched circular dot at top-left corner.

### 2.2 Mechanical Inspection Criteria

1. **Conformal Coating**: Outdoor unit PCBs feature a thin protective acrylic/silicone conformal coating. Before probing test points or header pins, clean contact points using isopropyl alcohol (IPA) and a fine soft probe tip.
2. **Solder Joint Integrity**: Inspect 100 QFP leads for pin bridge solder whiskers, micro-cracks, or corrosion signs on `Vcc`, `GND`, `RES#`, and `MD0`/`MD1` pins.

---

## 3. Mode Pin Configurations & Operating States

The Renesas RX62T MCU operating mode is established at power-on reset based on the logic levels applied to pins `MD0`, `MD1`, and `EMLE`.

| Mode Pin | RX62T Pin No. | User Application Mode (Normal Run) | SCI Boot Mode (Flash Programming / Readout) | On-Chip Emulator (E1/E20 JTAG) |
| :------- | :------------ | :--------------------------------- | :------------------------------------------ | :----------------------------- |
| `MD0`    | Pin 6         | **HIGH** ($V_{\text{CC}}$)         | **LOW** ($0\text{V}$)                       | **LOW** ($0\text{V}$)          |
| `MD1`    | Pin 7         | **HIGH** ($V_{\text{CC}}$)         | **HIGH** ($V_{\text{CC}}$)                  | **LOW** ($0\text{V}$)          |
| `EMLE`   | Pin 2         | **LOW** ($0\text{V}$)              | **LOW** ($0\text{V}$)                       | **HIGH** ($V_{\text{CC}}$)     |

### 3.1 Signal Thresholds ($V_{\text{CC}} = 5.0\text{V}$ Nominal)

- **Input Logic High ($V_{\text{IH}}$)**: $\ge 0.8 \times V_{\text{CC}} = 4.00\text{V}$ (Target: $5.0\text{V}$)
- **Input Logic Low ($V_{\text{IL}}$)**: $\le 0.2 \times V_{\text{CC}} = 1.00\text{V}$ (Target: $0.0\text{V}$)
- **Reset Pin (`RES#`, Pin 10)**: Active LOW with internal pull-up. Pull `RES#` to $0\text{V}$ for $> 2\text{ ms}$ to initiate mode transition.

---

## 4. Outdoor PCB Programming Header & Test Point Mapping

The outdoor unit PCB provides a dedicated multi-pin service programming header (`CN_PROG` or `JP1`) routed to RX62T peripheral pins:

| Header Pin | Signal Name | RX62T Pin No. | Function / Connection Description                        | Expected Idle Voltage |
| :--------- | :---------- | :------------ | :------------------------------------------------------- | :-------------------- |
| **1**      | `VCC_5V`    | Pin 11, 23    | MCU $V_{\text{CC}}$ +5.0V Logic Power Rail               | $5.00\text{V DC}$     |
| **2**      | `GND`       | Pin 13, 25    | Common Logic Signal Reference Ground                     | $0.00\text{V DC}$     |
| **3**      | `TXD0`      | Pin 36 (P20)  | SCI0 Serial Transmit Data (Connects to Programmer RXD)   | $5.00\text{V}$ (High) |
| **4**      | `RXD0`      | Pin 37 (P21)  | SCI0 Serial Receive Data (Connects to Programmer TXD)    | $5.00\text{V}$ (High) |
| **5**      | `RES#`      | Pin 10        | Hardware Reset Input (Active LOW)                        | $5.00\text{V}$ (High) |
| **6**      | `MD0`       | Pin 6         | Mode Pin 0 (Pulled HIGH via $10\text{ k}\Omega$ default) | $5.00\text{V}$ (High) |
| **7**      | `MD1`       | Pin 7         | Mode Pin 1 (Pulled HIGH via $10\text{ k}\Omega$ default) | $5.00\text{V}$ (High) |

---

## 5. Step-by-Step Voltage Measurement & Check Protocol

Execute the following steps sequentially using a calibrated digital multimeter (DMM) before attempting serial boot mode communication:

### Step 1: Unpowered Static Impedance Test

1. Disconnect main AC mains power to the outdoor unit. Wait 5 minutes for $340\text{V DC}$ bulk bus capacitors to discharge below $5\text{V DC}$.
2. Measure resistance between Header Pin 1 (`VCC_5V`) and Pin 2 (`GND`).
   - **Pass Criterion**: Resistance $> 1.0\text{ k}\Omega$ (No short circuits).
3. Measure resistance between `TXD0`/`RXD0` and `GND`.
   - **Pass Criterion**: Resistance $> 10\text{ k}\Omega$.

### Step 2: Power-On Voltage Level Verification

1. Apply logic power to outdoor board (or power via low-voltage DC bench supply on 5V rail).
2. Measure voltage levels at programming header pins:
   - `VCC_5V`: $4.85\text{V}$ to $5.15\text{V DC}$.
   - `RES#`: $4.85\text{V}$ to $5.15\text{V DC}$ (HIGH when released).
   - `MD0`: $4.85\text{V}$ to $5.15\text{V DC}$ (Default User Application Mode).
   - `MD1`: $4.85\text{V}$ to $5.15\text{V DC}$ (Default User Application Mode).

### Step 3: Boot Mode Entry Verification

1. Ground `MD0` (Header Pin 6 -> GND).
2. Pulse `RES#` (Header Pin 5) to `GND` for $10\text{ ms}$ and release.
3. Verify mode pin voltages:
   - `MD0`: $0.00\text{V}$ to $0.20\text{V DC}$ (LOW)
   - `MD1`: $4.85\text{V}$ to $5.15\text{V DC}$ (HIGH)
4. Verify MCU enters SCI Boot Mode (Serial TX line `TXD0` toggles bit rate auto-baud sync pulses at power-up/reset).

---

## 6. Safety Lockout Protocol (ID-Code Security Protection Gate)

To prevent catastrophic flash erasure or serial communication lockout when connecting serial boot tools:

1. **Rule 1: Always Execute ID-Code Check First**
   Before executing any flash readout or erase command, run `/src/tools/verify_id_code.py` against any preliminary dump or query the security field via 16-byte key match check:
   ```bash
   python3 src/tools/verify_id_code.py -i build/puz_wm85vaa_factory.bin -c -v
   ```
2. **Rule 2: Locked State Handling**
   If the ID-code security field (`0xFFFFFFA0`) is verified as **LOCKED** (`!= 0xFF...FF`), do NOT attempt blind bootloader read requests without providing the exact 16-byte security key (`--key`). Blind retries on a locked RX62T will trigger complete internal flash memory erasure by the hardware security gate.
3. **Rule 3: Voltage Clamping on Debug Harness**
   Ensure USB-to-UART serial interface signals (`TXD0`/`RXD0`) operate at $5.0\text{V}$ logic levels (or use level shifters if using 3.3V FTDI adapters) to avoid under-driving input logic thresholds.
