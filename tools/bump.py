"""Set the skin's version: addon.xml, and the literal Startup.xml compares with.

    python3 tools/bump.py 0.4.1

Startup.xml runs extras/setup.py at start only when the version setup last applied differs
from this one (Kodi's conditions cannot compare two live values, so the version is written in).
"""
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def main():
    version = sys.argv[1]
    if not re.fullmatch(r'\d+\.\d+\.\d+', version):
        raise SystemExit('version like 0.4.1')
    path = os.path.join(ROOT, 'addon.xml')
    text = open(path).read()
    text = re.sub(r'(<addon id="skin.appletv.minimal"\s+version=")[^"]+', r'\g<1>' + version, text, count=1)
    open(path, 'w').write(text)
    path = os.path.join(ROOT, 'xml', 'Startup.xml')
    text = open(path).read()
    text, n = re.subn(r'Skin\.String\(ATVSetupVersion\),[\d.]+\)', f'Skin.String(ATVSetupVersion),{version})', text)
    if not n:
        raise SystemExit('Startup.xml has no ATVSetupVersion condition')
    open(path, 'w').write(text)
    print('version', version)


if __name__ == '__main__':
    main()
