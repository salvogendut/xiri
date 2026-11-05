"""Pixel and metric controls for native text on the accelerated desktop."""
from collections import Counter
import itertools
import re
import shlex
import time

from . import sha256

FACE = '-adobe-courier-bold-r-normal--20-140-100-100-m-110-iso8859-1'


def verify(entry):
    output = entry['output']
    text = re.findall(r'^TEXT clip=(\d) style=(\d) ascent=(\d+) descent=(\d+) '
                      r'window_ink=(\d+) pixmap_ink=(\d+) mismatch=(\d+)$', output, re.M)
    assert len(text) == 45
    expected = Counter((clip, style, ascent, descent)
        for clip, style, (ascent, descent) in itertools.product(
            range(3), range(5), [(11, 2), (13, 3), (13, 5)]))
    assert Counter(tuple(map(int, row[:4])) for row in text) == expected
    assert all(int(row[4]) > 0 and row[4] == row[5] and row[6] == '0' for row in text)
    xft = re.findall(r'^XFT clip=(\d) render=(\d) aa=(\d) color=(\d) actual=(\d),(\d) '
                     r'ascent=\d+ descent=\d+ window_ink=(\d+) pixmap_ink=(\d+) '
                     r'mismatch=(\d+) max_delta=(\d+) file=.+$', output, re.M)
    assert len(xft) == 24
    assert {tuple(map(int, row[:4])) for row in xft} == set(itertools.product(range(3), range(2), range(2), range(2)))
    assert all(row[1:3] == row[4:6] and int(row[6]) > 0 and row[6] == row[7]
               and row[8:] == ('0', '0') for row in xft)
    assert output.count('TEXT_PASS mismatches=0') == 3 and output.count('XFT_PASS failures=0') == 1
    metrics = entry['metrics']
    assert re.findall(r'^SET repeat=(\d) count=1 missing=0 width=44 ', metrics, re.M) == list('012345')
    assert metrics.count('FONT '+FACE+' ascent=13 descent=5 width=11,11 glyph=15,5') == 6


def compile(guest):
    guest.command('for name in text-pixels font-metrics; do '
        'cc -O2 -Wall -Wextra -Werror -I/usr/X11R7/include "$name.c" '
        '-L/usr/X11R7/lib -Wl,-rpath,/usr/X11R7/lib -lX11 -o "$name" || exit; done; '
        'cc -O2 -Wall -Wextra -Werror -I/usr/X11R7/include -I/usr/X11R7/include/freetype2 '
        'xft-pixels.c -L/usr/X11R7/lib -Wl,-rpath,/usr/X11R7/lib -lXft -lX11 -lfontconfig -o xft-pixels', 180)


def check(guest, directory, record, label):
    log = 'fonts-'+label+'.log'
    guest.command('{ ./text-pixels && ./text-pixels "-adobe-helvetica-bold-o-normal--14-*" '
        '&& ./text-pixels '+shlex.quote(FACE)+' && ./xft-pixels; } >'+log+' 2>&1', 120)
    entry = dict(output=guest.read_text('cat '+log),
                 metrics=guest.read_text('./font-metrics '+shlex.quote(FACE)),
                 pixel_checks=69*300*60)
    (directory/log).write_text(entry['output'])
    verify(entry)
    record.setdefault('font_checks', {})[label] = entry
    print(label+': 69 native text cases and six Courier metric cycles passed', flush=True)


def capture_menus(guest, directory, record):
    if 'menu_captures' in record:
        return
    # Keep the terminal away from Help and drive real pointer motion. A
    # screenshot of an obscured main button is not evidence of its menu.
    guest.command('./place winterm 350 280 903 480')
    captures = {}
    cases = [('desktop', 40, None), ('selected', 66, None),
             ('internet', 92, None), ('find', 118, None),
             ('system', 144, None), ('help', 170, None),
             ('access-files', 40, 42), ('shared-resources', 40, 64),
             ('customize', 40, 86), ('utilities', 144, 324)]
    for name, top, row in cases:
        guest.monitor('ptr click 55 '+str(top))
        time.sleep(3)
        if row is not None:
            guest.monitor('ptr click 250 '+str(row))
            time.sleep(2)
        guest.monitor('screen wait 500 10000')
        path = directory/('toolchest-'+name+'.png')
        guest.monitor('screen shot '+str(path)+' 0 0 720 620')
        captures[name] = dict(path=path.name, sha256=sha256(path))
        guest.monitor('key Escape')
        if row is not None:
            guest.monitor('key Escape')
        time.sleep(1)
    record['menu_captures'] = captures
    print('Toolchest menu captures saved for visual review', flush=True)
