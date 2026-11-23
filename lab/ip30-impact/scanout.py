"""Count wrong pixels inside and outside the native HQ4 PIO test rectangle."""
from PIL import Image


def check(path):
    background = (0x21, 0x35, 0x4b)
    foreground = (0xf4, 0xa1, 0x39)
    x, y, w, h = 117, 203, 413, 239
    with Image.open(path) as png:
        frame = png.convert('RGB')
    if frame.size != (1280, 1024):
        raise ValueError(f'unexpected scanout size {frame.size}')
    inside = frame.crop((x, y, x + w, y + h))
    # Two exact colour counts check the entire frame, including all four edges.
    def count(image, colour):
        return sum(n for n, rgb in image.getcolors(image.width * image.height)
                   if rgb == colour)
    inside_errors = w * h - count(inside, foreground)
    outside_errors = frame.width * frame.height - w * h - (
        count(frame, background) - count(inside, background))
    return dict(size=frame.size, xywh=[x, y, w, h], foreground=foreground,
                background=background, inside_errors=inside_errors,
                outside_errors=outside_errors)
