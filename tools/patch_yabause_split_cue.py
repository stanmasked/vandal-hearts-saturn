#!/usr/bin/env python3
"""Stage89: pinned original Yabause with conservative two-file Saturn CUE support.

The historical Yabause revision rejects a second FILE statement. We retain
the original single-file parser unchanged, and route only exactly two-file
CUEs through a bounded, strict two-track MODE1/2352 + AUDIO parser.
"""
from __future__ import annotations

import argparse
from pathlib import Path
import sys

from tools.patch_yabause_full_cdbase import patch_full_cdbase

INCLUDE_BEFORE = "static int LoadBinCue(const char *cuefilename, FILE *iso_file)"
INIT_ORIGINAL = "ret = LoadBinCue(iso, iso_file);"
INIT_REPLACE = "ret = VHIsSplitCue(iso_file) ? VHLoadTwoFileCue(iso, iso_file) : LoadBinCue(iso, iso_file);"

C_SOURCE = r'''
/* Stage89: limited two-file BIN/CUE parser for T-9526G-shaped layout.
   Data track: MODE1/2352 INDEX01 00:00:00.
   Audio track: separate BINARY file with INDEX00 00:00:00,
   INDEX01 00:02:00 (150 in-file pregap frames).
   No game media is included in this public source patch. */
static int VHIsSplitCue(FILE *cue)
{
   char line[512];
   int files = 0;
   rewind(cue);
   while (fgets(line, sizeof(line), cue))
   {
      char *p = line;
      while (*p == ' ' || *p == '\t') p++;
      if (strncmp(p, "FILE ", 5) == 0)
      {
         files++;
         if (files >= 2) break;
      }
   }
   rewind(cue);
   return files >= 2;
}

static int VHLoadTwoFileCue(const char *cuefilename, FILE *cue)
{
   char line[512];
   char names[2][256] = {{0}};
   FILE *fp[2] = {NULL, NULL};
   long sizes[2] = {0, 0};
   int file_count = 0, track_count = 0;
   int data_index = -1, audio_index00 = -1, audio_index01 = -1;
   int failed = 1;
   int i;

   rewind(cue);
   while (fgets(line, sizeof(line), cue))
   {
      char *p = line;
      while (*p == ' ' || *p == '\t') p++;
      if (strncmp(p, "FILE ", 5) == 0)
      {
         char name[256] = {0};
         char type[16] = {0};
         if (file_count >= 2 ||
             sscanf(p, "FILE \"%255[^\"]\" %15s", name, type) != 2 ||
             strcmp(type, "BINARY") != 0 ||
             strchr(name, '/') || strchr(name, '\\') ||
             strstr(name, "..") || name[0] == '\0')
            goto done;
         strcpy(names[file_count++], name);
      }
      else if (strncmp(p, "TRACK ", 6) == 0)
      {
         int n = 0;
         char kind[24] = {0};
         if (sscanf(p, "TRACK %d %23s", &n, kind) != 2 ||
             track_count >= 2 || file_count != track_count + 1 ||
             n != track_count + 1 ||
             strcmp(kind, n == 1 ? "MODE1/2352" : "AUDIO") != 0)
            goto done;
         track_count++;
      }
      else if (strncmp(p, "INDEX ", 6) == 0)
      {
         int index = -1, min = 0, sec = 0, frame = 0;
         if (sscanf(p, "INDEX %d %d:%d:%d", &index, &min, &sec, &frame) != 4 ||
             track_count == 0 || min != 0 || sec >= 60 ||
             frame >= 75 || index < 0 || index > 1)
            goto done;
         if (track_count == 1 && index == 1)
         {
            if (data_index >= 0) goto done;
            data_index = sec * 75 + frame;
         }
         if (track_count == 2 && index == 0)
         {
            if (audio_index00 >= 0) goto done;
            audio_index00 = sec * 75 + frame;
         }
         if (track_count == 2 && index == 1)
         {
            if (audio_index01 >= 0) goto done;
            audio_index01 = sec * 75 + frame;
         }
      }
      else if (strncmp(p, "PREGAP ", 7) == 0 ||
               strncmp(p, "POSTGAP ", 8) == 0)
      {
         /* No additional synthetic gaps or offset interpretations. */
         goto done;
      }
   }

   if (ferror(cue) || file_count != 2 || track_count != 2 ||
       data_index != 0 || audio_index00 != 0 || audio_index01 != 150 ||
       strcmp(names[0], names[1]) == 0)
      goto done;

   for (i = 0; i < 2; i++)
   {
      char full[1024];
      const char *end = strrchr(cuefilename, '/');
      const char *slash = strrchr(cuefilename, '\\');
      size_t prefix;
      if (!end || (slash && slash > end)) end = slash;
      prefix = end ? (size_t)(end - cuefilename + 1) : 0;
      if (prefix + strlen(names[i]) + 1 > sizeof(full)) goto done;
      if (prefix) memcpy(full, cuefilename, prefix);
      strcpy(full + prefix, names[i]);
      fp[i] = fopen(full, "rb");
      if (!fp[i]) goto done;
      if (fseek(fp[i], 0, SEEK_END) != 0) goto done;
      sizes[i] = ftell(fp[i]);
      if (sizes[i] <= 0 || sizes[i] > 0x7fffffffL ||
          (sizes[i] % 2352) != 0 || fseek(fp[i], 0, SEEK_SET) != 0)
         goto done;
   }
   if (sizes[1] <= (150L * 2352L) ||
       sizes[0] / 2352L > (0x7fffffffL / 2352L))
      goto done;

   /* Saturn FAD begins at 150. Track 2 INDEX01 follows 150 pregap
      sectors that are stored inside the second file. */
   {
      const u32 data_count = (u32)(sizes[0] / 2352L);
      const u32 audio_count = (u32)(sizes[1] / 2352L);
      const u32 audio_start = 150U + data_count + 150U;
      session_info_struct *session = calloc(1, sizeof(*session));
      if (!session) goto done;
      session->track = calloc(2, sizeof(track_info_struct));
      if (!session->track)
      {
         free(session);
         goto done;
      }
      session->track_num = 2;
      session->fad_start = 150;
      session->fad_end = audio_start + audio_count - 150U - 1U;
      session->track[0].ctl_addr = 0x41;
      session->track[0].sector_size = 2352;
      session->track[0].fad_start = 150;
      session->track[0].fad_end = 150U + data_count - 1U;
      session->track[0].file_size = (int)sizes[0];
      session->track[0].file_id = 0;
      session->track[0].fp = fp[0];
      session->track[1].ctl_addr = 0x01;
      session->track[1].sector_size = 2352;
      session->track[1].fad_start = audio_start;
      session->track[1].fad_end = session->fad_end;
      session->track[1].file_offset = 150U * 2352U;
      session->track[1].file_size = (int)sizes[1];
      session->track[1].file_id = 1;
      session->track[1].fp = fp[1];
      disc.session = session;
      disc.session_num = 1;
      fp[0] = fp[1] = NULL; /* Core owns these handles on success. */
      failed = 0;
   }
done:
   for (i = 0; i < 2; i++)
      if (fp[i]) fclose(fp[i]);
   if (!failed) fclose(cue); /* historical success contract */
   return failed ? -1 : 0;
}

'''


def patch_split_cue(raw: bytes) -> bytes:
    # Full immutable-public-source check plus instrumented primary reads.
    source = patch_full_cdbase(raw).decode("utf-8")
    if source.count(INCLUDE_BEFORE) != 1 or source.count(INIT_ORIGINAL) != 1:
        raise ValueError("upstream CUE parser or init layout changed")
    if "VHLoadTwoFileCue" in source or "VHIsSplitCue" in source:
        raise ValueError("already patched upstream")
    source = source.replace(INCLUDE_BEFORE, C_SOURCE + INCLUDE_BEFORE)
    source = source.replace(INIT_ORIGINAL, INIT_REPLACE)
    # The actual Stage02 CUE begins with CATALOG, not FILE. Historical
    # ISOCDInit wrongly assumed every CUE's first six bytes are FILE ".
    # Route by verified .CUE extension; strict split parser enforces grammar.
    detector = [line for line in source.splitlines(keepends=True)
                if 'if (stricmp(ext, ".CUE")' in line and
                'strncmp(header,' in line]
    if len(detector) != 1:
        raise ValueError("unexpected old Yabause CUE header detector")
    line = detector[0]
    newline = "\r\n" if line.endswith("\r\n") else "\n"
    prefix = line[:line.index("if (stricmp")]
    source = source.replace(
        line, prefix + 'if (ext && stricmp(ext, ".CUE") == 0)' + newline
    )
    if (source.count('if (ext && stricmp(ext, ".CUE") == 0)') != 1 or
            source.count("VHLoadTwoFileCue(iso, iso_file)") != 1 or
            source.count("LoadBinCue(iso, iso_file)") != 1 or
            source.count("if (vh_primary_read == 1)") != 1):
        raise ValueError("invalid split-CUE integration")
    return source.encode("utf-8")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--source", type=Path, required=True)
    ap.add_argument("--output", type=Path, required=True)
    a = ap.parse_args()
    try:
        if (a.source.resolve() == a.output.resolve() or
                a.output.exists() or a.source.name != "cdbase.c" or
                a.output.suffix != ".c"):
            raise ValueError("input/output path not valid")
        patched = patch_split_cue(a.source.read_bytes())
        with a.output.open("xb") as out:
            out.write(patched)
    except (OSError, ValueError, UnicodeError, TypeError):
        print("STAGE89_PINNED_SPLIT_CUE_PATCH_REJECTED", file=sys.stderr)
        return 1
    print("STAGE89_PINNED_YABAUSE_TWO_FILE_CUE_PATCH_READY")
    return 0


if __name__ == "__main__":
    sys.exit(main())
