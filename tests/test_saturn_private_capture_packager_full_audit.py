"""Invented-only full-size Stage126 packaging preflight."""
import tempfile
import unittest
from pathlib import Path
from tools.saturn_private_capture_packager import package_stage124_style_pair
from tools.saturn_private_prologue_continue_ninth_c import OCTA_EVENTS_108
from test_saturn_private_prologue_continue_ninth_c import _run

class Stage126FullAuditTest(unittest.TestCase):
    def test_full_capture_auditor_precedes_packaging(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            control, enabled=root/"control",root/"enabled"
            _run(control,False)
            _run(enabled,True)
            output=root/"new-pair.tar.gz"
            report=package_stage124_style_pair(control,enabled,output)
            self.assertTrue(report["stage124_paired_capture_audit_executed"])
            self.assertFalse(report["original_gameplay_verified"])
            self.assertEqual(report["checkpoint_pngs"],1800)
            (enabled/"pad-events.txt").write_bytes(OCTA_EVENTS_108)
            with self.assertRaises(ValueError):
                package_stage124_style_pair(control,enabled,root/"invalid.tar.gz")
            self.assertFalse((root/"invalid.tar.gz").exists())
