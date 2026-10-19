# Stage 02 — Sega Saturn disc investigation (2026-10-20)

This report records a **read-only, local, metadata-only** inspection of the user-supplied Saturn game image. No original game bytes, assets, scene files or audio are committed.

## Received local inputs

- English v1.1 Sega Saturn disc image (two ZIP parts for Track 1, extracted locally).
- RAW Track 2 audio BIN and an accompanying CUE.

## Verified results

- Split ZIP: assembled; archive CRC passes.
- Track 1: 621,755,904 bytes; 264,352 RAW MODE1/2352 sectors.
- Track 2: 2,102,688 bytes; 894 raw audio sectors.
- CUE: Track 02 AUDIO, INDEX 00 at 00:00:00, INDEX 01 at 00:02:00, indicating 150 sectors of in-file pregap.
- Boot header: SEGA SEGASATURN, game product code T-9526G.
- ISO9660 PVD: VANDAL_HEARTS; declared sectors match track 1.
- Filesystem: 2 directories, 848 files.
- File extension counts: MAP 74, PRG 157, DAT 293, BIN 283, AVI 18, PCM 8, TEX 8, TXT 3, CRT 1, EMR 1, and two files whose extensions are blank.

Metadata-only filenames suggest potential entry points for further format research: BATL1PRG.BIN, BATLEPRG.BIN, MAP_1_1C.BIN, MAP_1_1P.BIN, EVENT01.DAT, B_TXT00.DAT and SD/SD00.PCM. Their contents and exact roles remain unverified.

## Private image fingerprint (SHA-256)

- Track 1: d9855ae466725056dbb1f42c852cb02c4c35f223b4b6f9d481c9605ff786fe45
- Track 2: 245f3f846b483bb2028f2ce86277b4fea5c98f2f5412450f97b6e3b198ac4915
- CUE: a97fcec5d7168a91c2d79f87053b75b7e1dc124fd48bb4fae9d12fd114d6112c

## Scope and limitations

The image is labeled **English v1.1**, an altered/translated release. It is not evidence by itself that the unpatched Japanese version shares identical battle data. A separate original-disc comparison is required.

The new read-only inspector at tools/saturn_iso.py validates sector sync, MODE1 framing, primary volume descriptor, ISO9660 endianness and file bounds. It does not extract data. Its test suite uses synthetic images and never requires copyrighted media.

Next milestones: analyze game-specific MAP/BIN/DAT formats using privately held original media, map their relationships, construct a neutral data schema and verify combat behavior against a running Saturn reference before claiming an authentic first battle.