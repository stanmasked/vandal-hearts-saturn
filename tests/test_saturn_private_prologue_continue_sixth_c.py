"""Synthetic-only regressions for the Stage121 private auditor; no game media is used."""
import os, struct, tempfile, unittest, zlib
from pathlib import Path
from tools.saturn_private_prologue_continue_sixth_c import (
    audit_private_prologue_continue_sixth_c, CHECKPOINTS, FRAME_COUNT,
    PENTA_EVENTS_72, PENTA_STATE_72, HEXA_EVENTS, HEXA_STATE,
)

def _chunk(kind,data):
    return struct.pack(">I",len(data))+kind+data+struct.pack(">I",zlib.crc32(kind+data)&0xffffffff)

def _png(value):
    w=h=64
    raw=b"".join(b"\0"+bytes([value,value,value])*w for _ in range(h))
    ihdr=struct.pack(">IIBBBBB",w,h,8,2,0,0,0)
    return b"\x89PNG\r\n\x1a\n"+_chunk(b"IHDR",ihdr)+_chunk(b"IDAT",zlib.compress(raw))+_chunk(b"IEND",b"")

def _write(path,data):
    with path.open("xb") as f:
        os.fchmod(f.fileno(),0o600);f.write(data)

def _run(path,enabled):
    path.mkdir(mode=0o700)
    same,changed=_png(0),_png(1)
    _write(path/"pre.png",same);_write(path/"post.png",changed if enabled else same)
    for frame in CHECKPOINTS:
        _write(path/f"frame-{frame}.png",changed if enabled and frame>=60120 else same)
    _write(path/"frames.stats",(f"STAGE99_FRAMES {FRAME_COUNT}\nSTAGE99_PC_BEFORE 0\nSTAGE99_PC_AFTER 0\nSTAGE99_WIDTH 64\nSTAGE99_HEIGHT 64\n").encode())
    samples=[0]+list(CHECKPOINTS)+[FRAME_COUNT]
    _write(path/"sh2-window.txt","".join(f"VH_SH2 frame={f} pc=0 valid=1\n" for f in samples).encode())
    _write(path/"video-state.txt","".join(f"VH_VIDEO frame={f} pc=0\n" for f in samples).encode())
    _write(path/"fad.vhcdlog",b"VHCD_FAD 1\nVHCD_FAD 2\n" if enabled else b"VHCD_FAD 1\n")
    _write(path/"pad-events.txt",HEXA_EVENTS if enabled else PENTA_EVENTS_72)
    _write(path/"pad-state.txt",HEXA_STATE if enabled else PENTA_STATE_72)

class Stage121PrivateAuditorTests(unittest.TestCase):
    def _pair(self,tmp):
        a,b=Path(tmp)/"control",Path(tmp)/"enabled";_run(a,False);_run(b,True);return a,b
    def test_valid_pair_reports_integrity_not_gameplay(self):
        with tempfile.TemporaryDirectory(prefix="stage121-audit-") as tmp:
            a,b=self._pair(tmp);r=audit_private_prologue_continue_sixth_c(a,b)
            self.assertEqual(r["checkpoint_png_count_per_process"],600)
            self.assertEqual(r["pre_sixth_checkpoint_equal_count"],499)
            self.assertEqual(r["first_post_sixth_framebuffer_divergence_by_61200"],60120)
            self.assertFalse(r["first_battle_or_player_control_verified"])
    def test_rejects_pre_input_divergence(self):
        with tempfile.TemporaryDirectory(prefix="stage121-audit-") as tmp:
            a,b=self._pair(tmp);(b/"frame-59880.png").unlink();_write(b/"frame-59880.png",_png(2))
            with self.assertRaisesRegex(ValueError,"diverged before sixth C"):audit_private_prologue_continue_sixth_c(a,b)
    def test_rejects_wrong_pad_receipt(self):
        with tempfile.TemporaryDirectory(prefix="stage121-audit-") as tmp:
            a,b=self._pair(tmp);(b/"pad-events.txt").unlink();_write(b/"pad-events.txt",PENTA_EVENTS_72)
            with self.assertRaisesRegex(ValueError,"sixth-C event receipt mismatch"):audit_private_prologue_continue_sixth_c(a,b)

if __name__=="__main__":unittest.main()
