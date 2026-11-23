/**
 * @file stub_rtkit_linker.ld
 * @brief Bare-Metal ARM64 Linker Script for RTKit Coprocessor Images
 *
 * Target: Apple Silicon A19 Pro (t8150 / v57ap / iOS 27.2 Build 24B119)
 */

OUTPUT_FORMAT("elf64-littleaarch64")
OUTPUT_ARCH(aarch64)
ENTRY(_start)

MEMORY
{
    SRAM (rwx) : ORIGIN = 0x100000000, LENGTH = 5M
}

SECTIONS
{
    . = ORIGIN(SRAM);

    .text : {
        KEEP(*(.text.boot))
        *(.text .text.*)
    } > SRAM

    .rodata : {
        *(.rodata .rodata.*)
    } > SRAM

    .data : {
        *(.data .data.*)
    } > SRAM

    .bss : ALIGN(16) {
        _bss_start = .;
        *(.bss .bss.*)
        *(COMMON)
        . = ALIGN(16);
        _bss_end = .;
    } > SRAM

    .stack : ALIGN(16) {
        _stack_bottom = .;
        . += 0x10000; /* 64 KB Stack */
        _stack_top = .;
    } > SRAM

    /DISCARD/ : {
        *(.comment)
        *(.note*)
        *(.eh_frame*)
    }
}
