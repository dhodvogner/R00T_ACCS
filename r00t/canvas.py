"""Virtual canvas.

All choreography is authored on a canvas that is 1920 units tall and `1920 * aspect` units wide
(1080 x 1920 for a phone, 3413 x 1920 on a 16:9 screen). The engine maps virtual units to real pixels with a single
uniform scale `s = pixel_height / 1920`, so layouts stay proportional on any display.
"""


class _Canvas:
    h = 1920.0
    w = 1080.0
    s = 1.0
    px_w = 1080
    px_h = 1920

    @property
    def cx(self):
        return self.w / 2.0

    def setup(self, px_w, px_h):
        self.px_w, self.px_h = int(px_w), int(px_h)
        self.s = self.px_h / self.h
        self.w = self.px_w / self.s


V = _Canvas()
