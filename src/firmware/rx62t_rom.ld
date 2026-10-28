/* Linker script for Renesas RX62T Microcontroller (256 KB Code Flash Variant)
 * Outdoor Unit Inverter Controller - Mitsubishi Electric Ecodan PUZ-WM85VAA
 */

OUTPUT_FORMAT("elf32-rx-le")
OUTPUT_ARCH(rx)
ENTRY(_PowerON_Reset)

MEMORY
{
    SRAM        (rwx) : ORIGIN = 0x00000000, LENGTH = 16K
    SFR         (rw)  : ORIGIN = 0x00080000, LENGTH = 128K
    DATA_FLASH  (rw)  : ORIGIN = 0x00100000, LENGTH = 32K
    CODE_FLASH  (rx)  : ORIGIN = 0xFFFC0000, LENGTH = 0x3FF80  /* 255.875 KB */
    FIXED_VECT  (r)   : ORIGIN = 0xFFFFFF80, LENGTH = 128      /* 128 Bytes */
}

SECTIONS
{
    /* Code Flash ROM Sections */
    .text 0xFFFC0000 :
    {
        *(.text)
        *(.text.*)
        *(.P)
        *(.P.*)
    } > CODE_FLASH

    .rodata :
    {
        *(.rodata)
        *(.rodata.*)
        *(.C)
        *(.C.*)
        *(.C_1)
        *(.C_2)
    } > CODE_FLASH

    /* Dynamic fan target RPM lookup tables mapped at 0xFFFD4120 */
    .fan_lut 0xFFFD4120 :
    {
        KEEP(*(.fan_lut))
    } > CODE_FLASH

    /* Data initialized values stored in Code Flash to be copied to SRAM */
    .idata :
    {
        _idata_start = .;
        *(.idata)
        *(.D)
        *(.D_1)
        *(.D_2)
        _idata_end = .;
    } > CODE_FLASH

    /* Internal SRAM Sections */
    .data 0x00000000 : AT(_idata_start)
    {
        _data_start = .;
        *(.data)
        *(.data.*)
        *(.B)
        *(.B_1)
        *(.B_2)
        _data_end = .;
    } > SRAM

    .bss (NOLOAD) :
    {
        _bss_start = .;
        *(.bss)
        *(.bss.*)
        *(COMMON)
        _bss_end = .;
    } > SRAM

    .stack (NOLOAD) :
    {
        . = ALIGN(4);
        _stack_bottom = .;
        . += 0x1000; /* 4 KB Stack */
        _stack_top = .;
    } > SRAM

    /* Data Flash (E2) Non-Volatile Memory */
    .data_flash 0x00100000 :
    {
        *(.data_flash)
        *(.D_E2)
    } > DATA_FLASH

    /* Peripheral Special Function Registers */
    .sfr 0x00080000 (NOLOAD) :
    {
        *(.sfr)
    } > SFR

    /* Fixed Vector Table & Security Field */
    .fixed_vectors 0xFFFFFF80 :
    {
        KEEP(*(.fixed_vectors))
        KEEP(*(.id_code))        /* 0xFFFFFFA0 ID-Code protection gate */
        KEEP(*(.fpu_vectors))
        KEEP(*(.ofs))            /* Option Function Select Register */
        KEEP(*(.reset_vector))   /* 0xFFFFFFFC Reset Vector */
    } > FIXED_VECT
}
