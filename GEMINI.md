# Goal
Modify the Mitsubishi Electric Ecodan PUZ-WM85VAA fan parameter / software / electronics to lower the fan speed. If necessary provide a decompiled firmware of the PUZ-WM85VAA or FTC6. Document all explored and discarded options as well as the discovery process.

# Structure
- `CONCEPT.md`: The overall structure of the solution, including Use Cases (e.g. noise reduction, lower fan speed during night/low-load) and High-Level Approaches (Software parameter tuning, Firmware patching, Electronics/PWM hardware modification).
- `DESIGN.md`: The detailed technical design of the chosen approach, including hardware schematics, firmware decompilation/memory maps, MCU architecture, signal interfaces, and toolchains.
- `TOP_ARCHITECTURE.puml`: The top-level component overview showing all major hardware/software modules (PUZ-WM85VAA outdoor unit, FTC6 main controller, inverter driver, fan motor board) and dataflows/signals between them.
- `ROADMAP.md`: The list of accomplished and planned steps of the project.
- `TECHNICAL_DEBTS.md`: If you find technical debts, like outdated documentation, unknown register maps, or security/safety risks, log them here, but don’t fix them until asked to do so.
- `README.md`: Overview of the repository and links to generated documentation or GitHub Pages if present.
- `/specification/`: External datasheets, service manuals, register maps, standards, converted to Markdown where appropriate.
- `/src/`: Firmware binaries, decompiled source code, hardware schematics/PCB designs, patch scripts, and custom tools.
- `/test/`: Test benches, firmware emulation tests, signal validation scripts, and verification test cases.
- `/build/`: Temporary directory for decompilation artifacts, disassemblies, binary outputs, or compiled patches.

# `CONCEPT.md` handling
- The `CONCEPT.md` relates all trade-offs and functional choices back to the primary Goal.
- It contains high-level operational concepts comparing:
  1. Software / Parameter Configuration (e.g., DIP switches, service parameters, CN105/Modbus control commands).
  2. Electronics / Hardware Modification (e.g., resistor dividers, PWM attenuators, motor signal interceptors).
  3. Firmware Reverse Engineering & Modification (e.g., decompiling FTC6 / PUZ-WM85VAA control logic and patching fan target RPM tables).
- Every major choice is first drawn out as three alternatives, the best one is chosen and the other, discarded ones kept in summary in the last chapter of the concept.

# `DESIGN.md` handling
- The `DESIGN.md` derives all necessary technological choices from `CONCEPT.md`.
- It contains precise implementation choices, micro-architectural details, and circuit diagrams.
- Every major choice is first drawn out as three alternatives, the best one is chosen and the other, discarded ones kept in summary in the last chapter of the concept.
- It contains a detailed architecture of all components and their technical interfaces.
- Includes `TOP_ARCHITECTURE.puml` as a dynamically rendered image as soon as available.

## Firmware Decompilation & Reverse Engineering
- Document MCU architecture, chip markings, crystal frequencies, Flash/EEPROM memory maps, and vector tables.
- Use reverse engineering tools (e.g. Ghidra, radare2, binwalk) to analyze firmware binaries.
- Keep decompiled pseudocode / assembly clean and well-commented in `/src/`.
- Document fan speed calculation routines, PWM lookup tables, and safety threshold limits (e.g. defrost cycle, minimum airflow requirements).
- Document checksum, CRC, or signature mechanisms used by the firmware, providing script utilities to recompute valid checksums for patched binaries.

## Hardware & Electronics Design
- Document connector pinouts (e.g., CN105, fan motor connections, power boards, sensor lines).
- Provide circuit schematics (PlantUML or KiCad) for hardware interventions (e.g., signal attenuation, microcontroller-based signal interceptors).
- Document DIP switch configurations and jumper settings affecting fan modes or operating limits.

## Communication Protocols & Interfaces
- Document protocol register maps (e.g., CN105 serial protocol, M-Net, Modbus RTU/TCP).
- Define message formats, register addresses, and parameter bounds relevant to fan speed control.
- Ensure all serial/bus communication parameters are precisely documented for reproducible analysis.

## Command-Line Tools & Scripts
- Every command-line tool or decompilation/patch script should support both short and long flag options (e.g. `-i` / `--input`, `-o` / `--output`).
- Scripts for binary analysis, checksum calculation, or flashing must be reproducible and documented.

# `ROADMAP.md` handling
- The `ROADMAP.md` is the final plan to implement the `CONCEPT.md` and `DESIGN.md` to achieve the top goal.
- Define the steps in a way to allow for parallelization by defining interfaces and specification definitions first and implementing/analyzing functions later.
- The `ROADMAP.md` file is structured into several key sections:
  - **Progress Overview**: A table summarizing Phases, Descriptions, and Status (using ✅ for completed, 🚧 for in-progress, ⏳ for planned).
  - **Goals**: A high-level list of project objectives with status emojis.
  - **Phases**: Detailed chapters for each project phase.
- The Tasks, and Subtasks if necessary, have checkboxes to show the progress.
- Every task to be implemented has to be modest, feasible and reasonable.
  - If no such task is available, then break down bigger steps into modest ones without implementing anything, just changing the `ROADMAP.md`.
- Status Emojis:
  - ✅: Completed
  - 🚧: In Progress
  - ⏳: Planned / To Do
- The progress is updated with every increment.
- Finished tasks are linked to the corresponding issue/commit and timestamped at the end of the line.

# HOWTO
- Used "ReadTheDocs.org" (RTD) / GitHub Pages for documentation publishing from main branch.

# Testing & Verification
- CI/CD pipelines should run automated tests on decompilation scripts, checksum recalculations, documentation syntax, and static analysis on code/schematics.
- Run tests on every commit on every branch.
- Add caching for build tools and dependencies where appropriate.
