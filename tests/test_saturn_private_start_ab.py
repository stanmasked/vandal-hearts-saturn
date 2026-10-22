"""Stage107: synthetic-only control-vs-START witness integrity checks."""
from pathlib import Path
import struct
import tempfile
import unittest
import zlib

from tools.saturn_private_start_ab import (
    CONTROL, START, FRAME_COUNT, audit_start_ab,
)


def chunk(kind, payload):
    return (struct.pack(">I", len(payload)) + kind + payload +
            struct.pack(">I", zlib.crc32(kind + payload) & 0xffffffff))


def png(rgb):
    w=h=64
    raw=bytes([0] + list(rgb)*w) * h
    return (b"\x89PNG\r\n\x1a\n" +
            chunk(b"IHDR", struct.pack(">IIBBBBB", w,h,8,2,0,0,0)) +
            chunk(b"IDAT", zlib.compress(raw)) +
            chunk(b"IEND",b""))


class ControlStartABTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        root=Path(self.temp.name)
        root.chmod(0o700)
        self.control=root/"control"
        self.start=root/"start"
        for folder,pad,rgb,fad in [
            (self.control,CONTROL,(0,0,0),b"VHCD_FAD 150\n"),
            (self.start,START,(1,2,3),b"VHCD_FAD 150\nVHCD_FAD 151\n"),
        ]:
            folder.mkdir(mode=0o700)
            for name,payload in (
                ("pad-events.txt",pad),
                ("fad.vhcdlog",fad),
                (f"frame-{FRAME_COUNT}.png",png(rgb)),
            ):
                out=folder/name
                out.write_bytes(payload)
                out.chmod(0o600)

    def test_good_invented_control_and_start_have_two_distinct_receipts(self):
        report=audit_start_ab(self.control,self.start)
        self.assertEqual(report["intervention_start_press_frame"],12000)
        self.assertEqual(report["intervention_start_release_frame"],12006)
        self.assertEqual(report["control_fad_events"],1)
        self.assertEqual(report["intervention_fad_events"],2)
        self.assertTrue(report["numeric_cd_logs_differ"])
        self.assertTrue(report["final_png_files_differ"])
        self.assertFalse(report["menu_content_visually_identified"])
        self.assertFalse(report["actual_controller_pulse_independently_verified_in_emulator"])
        self.assertNotIn(str(self.control), str(report))

    def test_identical_numeric_reads_and_png_do_not_imply_failure_or_success(self):
        (self.start/"fad.vhcdlog").write_bytes((self.control/"fad.vhcdlog").read_bytes())
        (self.start/f"frame-{FRAME_COUNT}.png").write_bytes(
            (self.control/f"frame-{FRAME_COUNT}.png").read_bytes())
        report=audit_start_ab(self.control,self.start)
        self.assertFalse(report["numeric_cd_logs_differ"])
        self.assertFalse(report["final_png_files_differ"])
        self.assertFalse(report["menu_content_visually_identified"])

    def test_wrong_controller_event_order_or_frame_is_rejected(self):
        file=self.start/"pad-events.txt"
        for payload in (
            CONTROL, START.replace(b"frame=12000",b"frame=11999"),
            START.replace(b"frame=12006",b"frame=12007"),
            START.splitlines(keepends=True)[0],
            START+b"VH_PAD frame=12012 button=START action=PRESS\n",
        ):
            with self.subTest(events=payload):
                file.write_bytes(payload)
                with self.assertRaises(ValueError):
                    audit_start_ab(self.control,self.start)

    def test_corrupt_fad_or_noncanonical_numeric_log_rejected(self):
        file=self.start/"fad.vhcdlog"
        for payload in (
            b"",b"VHCD_FAD -1\n",b"VHCD_FAD 00150\n",
            b"VHCD_FAD 150",b"VHCD_FAD 150\r\n",
            b"VHCD_FAD 150\nSECRET\n",
        ):
            with self.subTest(payload=payload):
                file.write_bytes(payload)
                with self.assertRaises(ValueError):
                    audit_start_ab(self.control,self.start)

    def test_reused_folder_is_rejected(self):
        with self.assertRaises(ValueError):
            audit_start_ab(self.control,self.control)

    def test_screenshot_corruption_rejected(self):
        file=self.control/f"frame-{FRAME_COUNT}.png"
        file.write_bytes(b"not PNG")
        with self.assertRaises(ValueError):
            audit_start_ab(self.control,self.start)

    def test_private_perms_required(self):
        file=self.control/"pad-events.txt"
        file.chmod(0o644)
        with self.assertRaises(ValueError):
            audit_start_ab(self.control,self.start)

    def test_symlink_pad_receipt_rejected(self):
        file=self.control/"pad-events.txt"
        original=self.control/"backing"
        file.rename(original)
        file.symlink_to(original)
        with self.assertRaises((OSError,ValueError)):
            audit_start_ab(self.control,self.start)


if __name__=="__main__":
    unittest.main()
