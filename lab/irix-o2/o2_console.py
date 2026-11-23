"""Confirm O2 guest shutdown through its graphical PROM."""
import hashlib
import time

from PIL import Image


def halt_to_prom(lab):
    lab.send('shutdown -h now')
    lab.wait(r'Done running shutdown hooks', 150)
    deadline = time.monotonic() + 90
    while time.monotonic() < deadline:
        path = lab.directory / 'halted.png'
        lab.ci('screenshot', str(path))
        # Fingerprint the six labels on the O2 PROM maintenance menu.
        # Exclude the mouse pointer, clock, graphics logo and surrounding artwork.
        with Image.open(path) as screen:
            labels = screen.convert('L').crop((205, 132, 550, 548))
            mask = labels.point(lambda v: 255 if v < 60 else 0, '1')
            if hashlib.sha256(mask.tobytes()).hexdigest() == (
                    '257b68448a88071e06e748b50cb979cf3063c1b0233ba03d9f6594469dd8fd76'):
                lab.logged_in = False
                lab.clean_shutdown = True
                return
        time.sleep(.25)
    raise ValueError('O2 did not return to the graphical PROM after shutdown')
