# Stage 18 — Fix a false rejection of valid NRO executables

## Verified bug

Stage 17's structural checker incorrectly required every nonempty NRO segment's file offset to be at least 0x80. Real `elf2nro` output commonly has the `.text` segment at offset **zero**: the NRO-start and NRO-header occupy the first 0x80 bytes of that segment. Consequently, a valid freshly cross-compiled executable could be rejected with 'text segment outside NRO body'.

Source references: Nintendo Switch NRO0 format description at https://switchbrew.org/wiki/NRO0 and the original `elf2nro.c` in the switchbrew/switch-tools GitHub repository. The NRO segment fields are file/memory offsets in the complete executable, not offsets after a separate file header.

## Code fix

- Permit `.text` offset zero and ensure the text section includes the initial 0x80-byte header and at least one byte of code.
- Check nonempty text, rodata, and data segments are in bounds and do not overlap one another.
- Validate the optional homebrew ASET header has its complete 0x38-byte structure, supported version zero, and in-bounds icon, NACP, and RomFS assets.
- Preserve the SHA-256 digest and explicit note that structural validity is **not** evidence of execution in NeXium or on Nintendo Switch.

## Tests performed before commit

Updated `tests/test_nro_verify.py` with 12 completely synthetic tests. The realistic minimal fixture uses `.text` offset zero, a 0x1000-byte text segment, and 0x1000-byte rodata and data segments, with an optional valid ASET/NACP section. Explicit negative tests check ELF impostors, short/truncated NROs, malformed lengths, empty code, overlapping segments, bad ASET version and out-of-range embedded NACP.

Local full baseline project suite: **15/15 Python tests passed**, C++ CTest **1/1 passed**, Python syntax compilation passed. No original Saturn game assets were needed or published.

## Remaining gate

The actual Switch NRO GitHub build for Stage 17 was still queued during this change. Do not claim the homebrew executable exists until GitHub Actions reports success and an artifact appears; then run this revised checker on the real produced NRO and, separately, test it in NeXium.
