"""Import the selected files from the two private, release-matched Indy audio CDs."""
import hashlib
import json
import subprocess

from . import ROOT

SOUNDS = '/emul/irix/usr/share/data/sounds/soundscheme'
PCM_LIBS = ('libaudio.so', 'libaudiofile.so', 'libawareaudio.so', 'libC.so.2',
            'libCsup.so', 'libdmedia.so', 'libm.so', 'libmalloc.so', 'libmutex.so',
            'dmedia/audioconverters/libaudioconvert.so',
            'dmedia/audioconverters/libaudiorateconv.so')


def audio_files(release, playback, effects, work, installed):
    """Check release and content, accepting locally rebuilt CD filesystems."""
    def extract(iso, member):
        return subprocess.check_output(['isoinfo', '-R', '-i', str(iso), '-x', '/' + member])

    for iso in (playback, effects):
        if extract(iso, 'release') != (release + '\n').encode():
            raise ValueError('Expected IRIX ' + release + ' audio media: ' + str(iso))
    files = [('sfplay', '/emul/irix/usr/sbin/sfplay', playback, 0o555),
             ('ssplay', '/emul/irix/usr/sbin/ssplay', effects, 0o555),
             ('example.aiff', SOUNDS + '/soundfiles/emptyDumpster.aiff', playback, 0o444)]
    for lib in PCM_LIBS:
        files.append(('lib32/' + lib, '/emul/irix/usr/lib32/' + lib, playback, 0o555))
    catalog = extract(effects, 'sounds/effects')
    indices = {int(row.split()[1]) for row in catalog.decode('ascii').splitlines()}
    if indices != set(range(37)):
        raise ValueError('Incomplete SGI default SoundScheme')
    for name in ['effects', *(str(i) + '.pcm' for i in sorted(indices))]:
        files.append(('sounds/' + name, SOUNDS + '/xiri/' + name, effects, 0o444))

    pins = json.loads((ROOT / 'lab/irix-hdsp/playback/installer-inputs.json').read_text())[release]
    digest = hashlib.sha256()
    additions = {}
    for member, dest, iso, mode in sorted(files):
        content = extract(iso, member)
        checksum = hashlib.sha256(content).hexdigest()
        digest.update((dest + ' ' + checksum + '\n').encode())
        if not content:
            raise ValueError('Missing audio resource: ' + member)
        if dest in installed:
            if installed[dest].get('sha256') != checksum:
                raise ValueError('Audio resource conflicts with base import: ' + dest)
            continue
        path = work / 'audio' / dest.lstrip('/')
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content)
        path.chmod(mode)
        additions[dest] = path
    if digest.hexdigest() != pins:
        raise ValueError('Unexpected SGI audio content for ' + release)
    return additions
