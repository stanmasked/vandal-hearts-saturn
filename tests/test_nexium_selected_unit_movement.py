"""Stage62 synthetic/adversarial MOV glyph checks; not guest NeXium evidence."""
from __future__ import annotations
import unittest
from PIL import ImageDraw
from test_nexium_selected_unit_hud import frame as selected_frame
from tools.nexium_selected_unit_movement import expect_movement,expect_hidden,GLYPHS,X,Y
from tools.nexium_selected_unit_hud import WHITE,DARK,HELP

def movement_frame(points=4,*,selected=True,shift_y=0,forged=None):
    image=selected_frame(selected=selected)
    draw=ImageDraw.Draw(image)
    if selected:
        for i,char in enumerate("MOV "+str(points)):
            for y,mask in enumerate(GLYPHS.get(char,(0,0,0,0,0))):
                for x in range(3):
                    if mask & (1 << (2-x)):
                        left=X+8*i+2*x
                        top=Y+2*y+shift_y
                        draw.rectangle((left,top,left+1,top+1),fill=WHITE)
    if forged is not None:
        x,y,color=forged
        draw.rectangle((x,y,x+1,y+1),fill=color)
    return image

class SelectedMovementGlyphTests(unittest.TestCase):
    def test_scout_movement_four(self):
        self.assertTrue(expect_movement(movement_frame(4),4))
    def test_guard_movement_three(self):
        self.assertTrue(expect_movement(movement_frame(3),3))
    def test_movement_value_five(self):
        self.assertTrue(expect_movement(movement_frame(5),5))
    def test_bounded_guest_y_shift(self):
        self.assertTrue(expect_movement(movement_frame(4,shift_y=-2),4))
    def test_wrong_scout_value_rejected(self):
        with self.assertRaisesRegex(ValueError,"bitmap mismatch"):
            expect_movement(movement_frame(4),3)
    def test_wrong_guard_value_rejected(self):
        with self.assertRaisesRegex(ValueError,"bitmap mismatch"):
            expect_movement(movement_frame(3),4)
    def test_missing_movement_label_rejected(self):
        image=selected_frame(selected=True)
        with self.assertRaisesRegex(ValueError,"bitmap mismatch"):
            expect_movement(image,4)
    def test_hidden_without_selection(self):
        self.assertTrue(expect_hidden(movement_frame(selected=False)))
    def test_ghost_movement_stat_rejected(self):
        with self.assertRaisesRegex(ValueError,"ghost MOV"):
            expect_hidden(movement_frame(4))
    def test_forged_one_pixel_rejected(self):
        image=movement_frame(4,forged=(573,683,DARK))
        with self.assertRaisesRegex(ValueError,"bitmap mismatch"):
            expect_movement(image,4)
    def test_invalid_negative_movement_rejected(self):
        with self.assertRaisesRegex(ValueError,"unsupported"):
            expect_movement(movement_frame(4),-1)
    def test_invalid_large_movement_rejected(self):
        with self.assertRaisesRegex(ValueError,"unsupported"):
            expect_movement(movement_frame(4),10)

if __name__=="__main__":unittest.main()
