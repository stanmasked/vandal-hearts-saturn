"""Synthetic-only tests for the Stage123 private auditor; no original game files."""
import os, struct, tempfile, unittest, zlib
from pathlib import Path
from tools.saturn_private_prologue_continue_eighth_c import (
    audit_private_prologue_continue_eighth_c, CHECKPOINTS, FRAME_COUNT,
    HEPTA_EVENTS_96, HEPTA_STATE_96, OCTA_EVENTS, OCTA_STATE,
)

def _chunk(kind,data):
    return struct.pack(">I",len(data))+kind+data+struct.pack(">I",zlib.crc32(kind+data)&0xffffffff)
def _png(v):
    w=h=64
    raw=b"".join(b"\0"+bytes([v,v,v])*w for _ in range(h))
    return b"\x89PNG\r\n\x1a\n"+_chunk(b"IHDR",struct.pack(">IIBBBBB",w,h,8,2,0,0,0))+_chunk(b"IDAT",zlib.compress(raw))+_chunk(b"IEND",b"")
def _write(p,data):
    with p.open("xb") as f:os.fchmod(f.fileno(),0o600);f.write(data)
def _run(p,enabled):
    p.mkdir(mode=0o700);same,changed=_png(0),_png(1)
    _write(p/"pre.png",same);_write(p/"post.png",changed if enabled else same)
    for frame in CHECKPOINTS:_write(p/f"frame-{frame}.png",changed if enabled and frame>=84120 else same)
    _write(p/"frames.stats",(f"STAGE99_FRAMES {FRAME_COUNT}\nSTAGE99_PC_BEFORE 0\nSTAGE99_PC_AFTER 0\nSTAGE99_WIDTH 64\nSTAGE99_HEIGHT 64\n").encode())
    samples=[0]+list(CHECKPOINTS)+[FRAME_COUNT]
    _write(p/"sh2-window.txt","".join(f"VH_SH2 frame={f} pc=0 valid=1\n" for f in samples).encode())
    _write(p/"video-state.txt","".join(f"VH_VIDEO frame={f} pc=0\n" for f in samples).encode())
    _write(p/"fad.vhcdlog",b"VHCD_FAD 1\nVHCD_FAD 2\n" if enabled else b"VHCD_FAD 1\n")
    _write(p/"pad-events.txt",OCTA_EVENTS if enabled else HEPTA_EVENTS_96)
    _write(p/"pad-state.txt",OCTA_STATE if enabled else HEPTA_STATE_96)

class Stage123PrivateAuditorTests(unittest.TestCase):
    def _pair(self,tmp):
        a,b=Path(tmp)/"control",Path(tmp)/"enabled";_run(a,False);_run(b,True);return a,b
    def test_valid_pair_reports_integrity_not_gameplay(self):
        with tempfile.TemporaryDirectory(prefix="stage123-audit-") as tmp:
            a,b=self._pair(tmp);r=audit_private_prologue_continue_eighth_c(a,b)
            self.assertEqual(r["checkpoint_png_count_per_process"],800)
            self.assertEqual(r["pre_eighth_checkpoint_equal_count"],699)
            self.assertEqual(r["first_post_eighth_framebuffer_divergence_by_85200"],84120)
            self.assertFalse(r["first_battle_or_player_control_verified"])
    def test_rejects_pre_input_divergence(self):
        with tempfile.TemporaryDirectory(prefix="stage123-audit-") as tmp:
            a,b=self._pair(tmp);(b/"frame-83880.png").unlink();_write(b/"frame-83880.png",_png(2))
            with self.assertRaisesRegex(ValueError,"diverged before eighth C"):audit_private_prologue_continue_eighth_c(a,b)
    def test_rejects_wrong_pad_receipt(self):
        with tempfile.TemporaryDirectory(prefix="stage123-audit-") as tmp:
            a,b=self._pair(tmp);(b/"pad-events.txt").unlink();_write(b/"pad-events.txt",HEPTA_EVENTS_96)
            with self.assertRaisesRegex(ValueError,"eighth-C event receipt mismatch"):audit_private_prologue_continue_eighth_c(a,b)

if __name__=="__main__":unittest.main()
