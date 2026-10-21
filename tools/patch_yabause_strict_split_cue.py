#!/usr/bin/env python3
"""Stage91: pin the Stage89 real Yabause CUE path to exact 8-line grammar.

The public upstream Git blob is authenticated by Stage80 then Stage89. This
stage changes only the bounded 2-file handler, not the fallback or CD reader.
"""
from __future__ import annotations

import argparse
from pathlib import Path
import sys

from tools.patch_yabause_split_cue import patch_split_cue

START = '   rewind(cue);\n   while (fgets(line, sizeof(line), cue))\n'
END = '   if (ferror(cue) || file_count != 2 || track_count != 2 ||'

STRICT_LOOP = r'''   rewind(cue);
   {
      int directive = 0;
      while (fgets(line, sizeof(line), cue))
      {
         size_t length = strlen(line);
         char *p = line;
         /* Never accept CUE lines truncated by fgets or missing LF. */
         if (!length || length >= sizeof(line) - 1 ||
             line[length - 1] != '\n' || ++directive > 8)
            goto done;
         line[--length] = '\0';
         if (length && line[length - 1] == '\r')
            line[--length] = '\0';
         while (*p == ' ' || *p == '\t') p++;
         if (directive == 1)
         {
            int k;
            if (strlen(p) != 21 || strncmp(p, "CATALOG ", 8) != 0)
               goto done;
            for (k = 8; k < 21; ++k)
               if (p[k] < '0' || p[k] > '9') goto done;
         }
         else if (directive == 2 || directive == 5)
         {
            char name[256] = {0};
            char type[16] = {0};
            int used = -1;
            if (strncmp(p, "FILE ", 5) != 0 ||
                sscanf(p, "FILE \"%255[^\"]\" %15s%n",
                       name, type, &used) != 2 ||
                used < 0 || (size_t)used != strlen(p) ||
                strcmp(type, "BINARY") != 0 ||
                name[0] == '\0' || strstr(name, "..") ||
                strpbrk(name, "/\\:") != NULL ||
                file_count != (directive == 2 ? 0 : 1))
               goto done;
            strcpy(names[file_count++], name);
         }
         else if (directive == 3)
         {
            if (strcmp(p, "TRACK 01 MODE1/2352") != 0 ||
                track_count != 0) goto done;
            track_count++;
         }
         else if (directive == 4)
         {
            if (strcmp(p, "INDEX 01 00:00:00") != 0 ||
                track_count != 1 || data_index >= 0) goto done;
            data_index = 0;
         }
         else if (directive == 6)
         {
            if (strcmp(p, "TRACK 02 AUDIO") != 0 ||
                track_count != 1) goto done;
            track_count++;
         }
         else if (directive == 7)
         {
            if (strcmp(p, "INDEX 00 00:00:00") != 0 ||
                track_count != 2 || audio_index00 >= 0) goto done;
            audio_index00 = 0;
         }
         else if (directive == 8)
         {
            if (strcmp(p, "INDEX 01 00:02:00") != 0 ||
                track_count != 2 || audio_index01 >= 0) goto done;
            audio_index01 = 150;
         }
         else goto done;
      }
      if (directive != 8) goto done;
   }

'''


def patch_strict_split_cue(raw: bytes) -> bytes:
    source = patch_split_cue(raw).decode("utf-8")
    start_func = source.index("static int VHLoadTwoFileCue(")
    i = source.find(START, start_func)
    j = source.find(END, i)
    if (i < 0 or j <= i or source.count(END) != 1 or
            source.count("static int VHLoadTwoFileCue(") != 1):
        raise ValueError("unexpected pinned Stage89 parser boundaries")
    original = source[i:j]
    if (original.count('else if (strncmp(p, "PREGAP ", 7)') != 1 or
            original.count('sscanf(p, "FILE ') != 1 or
            original.count('rewind(cue);') != 1):
        raise ValueError("Stage89 parser drift")
    patched = source[:i] + STRICT_LOOP + source[j:]
    if (patched[:i] != source[:i] or patched[i+len(STRICT_LOOP):] != source[j:] or
            patched.count("VHLoadTwoFileCue(") != 2 or
            patched.count("if (vh_primary_read == 1)") != 1 or
            patched.count('if (ext && stricmp(ext, ".CUE") == 0)') != 1):
        raise ValueError("incomplete strict source patch")
    return patched.encode("utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    try:
        if (args.source.resolve() == args.output.resolve() or
                args.output.exists() or args.source.name != "cdbase.c" or
                args.output.suffix != ".c"):
            raise ValueError("unrecognized input/output")
        patched = patch_strict_split_cue(args.source.read_bytes())
        with args.output.open("xb") as out:
            out.write(patched)
    except (ValueError, TypeError, UnicodeError, OSError):
        print("STAGE91_STRICT_PINNED_CUE_PATCH_REJECTED", file=sys.stderr)
        return 1
    print("STAGE91_STRICT_PINNED_PUBLIC_CUE_PATCH_READY")
    return 0


if __name__ == "__main__":
    sys.exit(main())
