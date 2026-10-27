# Indoor `CN105` Serial Interface & Command Protocol Specification

## 1. Physical Interface Specification

The `CN105` connector is a standard 5-pin JST-PA header located on the FTC6 (Flow Temperature Controller 6) main board (and standard Mitsubishi Electric indoor unit boards). It provides a direct TTL serial communication channel for remote monitoring, diagnostic tools, and external capacity capping/demand control modules.

### 1.1 Pinout Assignment

| Pin No. | Signal Name |     Voltage / Specification     | Description                                                     |
| :-----: | :---------: | :-----------------------------: | :-------------------------------------------------------------- |
|  **1**  |    `VCC`    | **12V DC / 5V DC** (100 mA max) | Logic power output for external interfaces / optical isolators. |
|  **2**  |    `GND`    |        **0V Reference**         | Signal Ground reference.                                        |
|  **3**  |    `TXD`    |        **5V TTL Level**         | Transmit line from FTC6 board to external controller.           |
|  **4**  |    `RXD`    |        **5V TTL Level**         | Receive line into FTC6 board from external controller.          |
|  **5**  |   `MODE`    |         **5V / Ground**         | Selects operating mode or expansion detection signal.           |

---

## 2. Serial Port Parameters

- **Baud Rate**: **2400 bps** (Standard factory rate) or **9600 bps** (High-speed service mode)
- **Data Bits**: **8 bits**
- **Parity**: **EVEN Parity** (`8E1`)
- **Stop Bits**: **1 bit**
- **Flow Control**: None (Software packet framing with checksum)

---

## 3. Packet Frame Format

All communication over `CN105` follows a structured binary packet format:

|     Byte Offset     |     Field Name     |           Description           | Value Range / Notes                                  |
| :-----------------: | :----------------: | :-----------------------------: | :--------------------------------------------------- |
|       `0x00`        |    **Header 1**    |          Sync Marker 1          | `0x52` (`'R'`) or `0xFC`                             |
|       `0x01`        |    **Header 2**    |    Sync Marker 2 / Direction    | `0x42` (Request) / `0x61` (Response)                 |
|       `0x02`        | **Payload Length** | Size of payload + command bytes | $N$ (typically `0x05` to `0x16`)                     |
|       `0x03`        |  **Command Type**  |   Function or register group    | e.g., `0x02` (Set), `0x03` (Get), `0x07` (Telemetry) |
| `0x04` .. `0x(N+2)` |  **Payload Data**  |   Function code + parameters    | Control bytes (Power, Mode, Temp, Capacity Cap)      |
|      `0x(N+3)`      |    **Checksum**    |     Byte summation checksum     | Calculated as `0x100 - (Sum(Bytes 0..N+2) % 256)`    |

---

## 4. Capacity Capping & Nighttime Sound Reduction Control

To enforce nighttime noise reduction (<35 dB(A) acoustic target), the `CN105` interface allows external injection of thermal load capping commands directly into the FTC6 control loop.

### 4.1 Demand / Capacity Cap Packet Structure (`Command 0x02` - Function `0x0B`)

```
Byte 00: 0x52  (Sync 1)
Byte 01: 0x42  (Sync 2)
Byte 02: 0x07  (Payload Length = 7 bytes)
Byte 03: 0x02  (Command: Set Parameter)
Byte 04: 0x0B  (Function: Night Mode / Demand Cap)
Byte 05: 0x01  (Enable Demand Limit)
Byte 06: 0x4B  (Demand Cap Level: 0x32 = 50%, 0x4B = 75%, 0x64 = 100%)
Byte 07: 0x00  (Reserved)
Byte 08: [CS]  (Checksum Byte)
```

### 4.2 Telemetry Readout Registers

The FTC6 responds to poll commands (`Command 0x03`) by broadcasting system state telemetries:

- **Compressor Operating Frequency ($f_{\text{comp}}$)**: Register `0x10` (Hz)
- **Evaporator Temperature ($T_{\text{evap}}$)**: Register `0x12` ($\text{Temp in } ^\circ\text{C} + 40$)
- **Suction Superheat ($\Delta T_{\text{SH}}$)**: Register `0x15` (Kelvin x 10)
- **Outdoor Fan Speed Status**: Register `0x1A` (Step 0..8)
