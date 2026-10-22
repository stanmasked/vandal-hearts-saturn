"""Stage102 static public-only contracts for private original SH2 wait-loop diagnostics."""
import unittest
from tools.patch_yabause_private_sh2_window import (
    HELPER, instrument_sh2_window,
)

class PrivateSh2WindowTest(unittest.TestCase):
    def test_pinned_original_runner_required(self):
        for raw in (b"",b"hello world",b"int main(){}"):
            with self.subTest(size=len(raw)),self.assertRaises(ValueError):
                instrument_sh2_window(raw)

    def test_private_only_instruction_window_not_in_stdout(self):
        self.assertIn("MSH2->MappedMemoryReadWord",HELPER)
        self.assertIn("r.PC - 8U",HELPER)
        self.assertIn("SH2GetRegisters",HELPER)
        self.assertIn("VH_SH2 frame=%d",HELPER)
        self.assertNotIn("puts(",HELPER)
        self.assertNotIn("stdout",HELPER)
        self.assertNotIn("Vdp2Ram",HELPER)

    def test_bounded_only_private_guest_memory(self):
        self.assertIn("0x06000010U",HELPER)
        self.assertIn("0x060FFFF0U",HELPER)
        self.assertIn("u16 op[9];",HELPER)
        self.assertIn("int i=0; i<9",HELPER)
        self.assertIn("fflush(out)",HELPER)

    def test_numeric_sh2_registers_do_not_claim_battle(self):
        for reg in ("r.SR.all","r.PR","r.GBR","r.R[0]","r.R[15]"):
            self.assertIn(reg,HELPER)
        self.assertNotIn("first_battle_verified",HELPER)


if __name__=="__main__":
    unittest.main()
