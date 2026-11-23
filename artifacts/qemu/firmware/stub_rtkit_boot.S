/**
 * @file stub_rtkit_boot.S
 * @brief ARM64 Bare-Metal Boot Entrypoint & Exception Vectors for RTKit Coprocessor Stubs
 *
 * Target: Apple Silicon A19 Pro (t8150 / v57ap / iOS 27.2 Build 24B119)
 */

    .text
    .align 11
    .global _vectors
_vectors:
    /* Current EL with SP0 */
    .align 7
    b   .
    .align 7
    b   .
    .align 7
    b   .
    .align 7
    b   .

    /* Current EL with SPx */
    .align 7
    b   .
    .align 7
    b   .
    .align 7
    b   .
    .align 7
    b   .

    /* Lower EL using AArch64 */
    .align 7
    b   .
    .align 7
    b   .
    .align 7
    b   .
    .align 7
    b   .

    /* Lower EL using AArch32 */
    .align 7
    b   .
    .align 7
    b   .
    .align 7
    b   .
    .align 7
    b   .

    .section .text.boot, "ax"
    .global _start
    .type _start, @function
_start:
    /* Set Vector Base Address Register (VBAR_EL1) */
    adr     x0, _vectors
    msr     vbar_el1, x0
    isb

    /* Initialize Stack Pointer to top of retention SRAM stack */
    ldr     x0, =_stack_top
    mov     sp, x0

    /* Write mandatory RTKSTACK canary watermark at stack bottom */
    ldr     x1, =0x52544B535441434B     /* 'RTKSTACK' */
    ldr     x2, =_stack_bottom
    str     x1, [x2]

    /* Clear BSS section */
    ldr     x0, =_bss_start
    ldr     x1, =_bss_end
    cmp     x0, x1
    b.ge    .Lbss_done
.Lbss_loop:
    str     xzr, [x0], #8
    cmp     x0, x1
    b.lt    .Lbss_loop
.Lbss_done:

    /* Enter RTKit C runtime */
    bl      rtkit_main

    /* Hang in WFI if rtkit_main returns */
.Lhalt:
    wfi
    b       .Lhalt

    .size _start, . - _start
