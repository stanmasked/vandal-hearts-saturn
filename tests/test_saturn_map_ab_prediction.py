"""Synthetic-only Stage 13 checks; no original Saturn media needed."""
import unittest
from collections import Counter
from tools.saturn_map_ab_prediction import (
    decode_ab, evaluate, mode, analyze_samples, rates,
    MAP_BYTES, TAIL_START, LAYER_WORDS
)


def make_map(a, b):
    if len(a) > LAYER_WORDS or len(b) > LAYER_WORDS:
        raise ValueError("fixture overflow")
    raw = bytearray(MAP_BYTES)
    for i, value in enumerate(a):
        at = TAIL_START + 2*i
        raw[at:at+2] = value.to_bytes(2, "big")
    for i, value in enumerate(b):
        at = TAIL_START + 2*(LAYER_WORDS+i)
        raw[at:at+2] = value.to_bytes(2, "big")
    return bytes(raw)


class Stage13Tests(unittest.TestCase):
    def test_decode(self):
        a, b = decode_ab(make_map([0x1234, 9], [11, 0xABCD]))
        self.assertEqual(a[:2], [0x1234, 9])
        self.assertEqual(b[:2], [11, 0xABCD])
        self.assertEqual(len(a), 1792)

    def test_reject_truncated_map(self):
        with self.assertRaises(ValueError):
            decode_ab(bytes(MAP_BYTES-2))

    def test_mode_and_tie(self):
        self.assertEqual(mode(Counter({7: 2, 3: 2})), 3)
        with self.assertRaises(ValueError):
            mode(Counter())

    def test_repeat_predicts_perfectly(self):
        a, b = [1, 2] * 896, [17, 18] * 896
        r = evaluate(a, b)
        self.assertEqual(r["test_nonzero"], 1792)
        self.assertEqual(r["covered"], 1792)
        self.assertEqual(r["model_correct"], 1792)

    def test_no_holdout_leakage(self):
        a, b = [0]*256, [0]*256
        for row in range(4):
            a[64*row] = 100+row
            b[64*row] = 200+row
        r = evaluate(a, b)
        self.assertEqual(r["test_nonzero"], 4)
        self.assertEqual(r["covered"], 0)

    def test_ignore_zeros(self):
        r = evaluate([1]*256, [0]*256)
        self.assertEqual(r["test_nonzero"], 0)

    def test_shift_control(self):
        a = [1]*128 + [2]*128
        b = [10]*128 + [20]*128
        self.assertGreater(evaluate(a,b)["model_correct"],
                           evaluate(a,b,shift=64)["model_correct"])

    def test_invalid_settings(self):
        a, b = [1]*256, [2]*256
        cases = (lambda: evaluate([], []), lambda: evaluate(a,b[:-1]),
                 lambda: evaluate(a[:-1],b[:-1]),lambda: evaluate(a,b,folds=1),
                 lambda: evaluate(a,b,folds=5),lambda: evaluate(a,b,shift=-1),
                 lambda: evaluate(a,b,shift=256),
                 lambda: evaluate([65536]+a[1:],b))
        for call in cases:
            with self.assertRaises(ValueError):
                call()

    def test_empty_rates(self):
        d = {"covered":0,"test_nonzero":0,"model_correct":0,
             "baseline_correct_covered":0,"baseline_correct_all":0}
        self.assertIsNone(rates(d)["coverage_fraction"])

    def test_numeric_only_report(self):
        report = analyze_samples({"M_MAP01.MAP":make_map(
            [111]*LAYER_WORDS,[222]*LAYER_WORDS)})
        self.assertEqual(report["map_count"],1)
        self.assertEqual(report["by_shift"]["0"]["counts"]["model_correct"],1792)
        self.assertNotIn("111",str(report))
        self.assertNotIn("222",str(report))

    def test_validation(self):
        with self.assertRaises(ValueError):
            analyze_samples({})
        with self.assertRaises(ValueError):
            analyze_samples({"BAD.BIN":make_map([1],[2])})


if __name__ == "__main__":
    unittest.main()
