"""Add a content-based version (?v=...) to the local .js/.css files every page loads, so browsers
download the new file after a change instead of showing an old cached copy.
Run from the repository root after changing a .js/.css file:  python3 tools/stamp_versions.py"""
import glob, hashlib, os, re

ASSET = re.compile(r'''((?:src|href)=")([^":?#]+\.(?:js|css))(?:\?v=[0-9a-f]+)?(")''')


def stamp(html_path):
    folder = os.path.dirname(html_path)
    text = open(html_path, encoding='utf-8').read()

    def version(m):
        path = os.path.normpath(os.path.join(folder, m.group(2)))
        if not os.path.exists(path):  # e.g. a CDN script - leave it alone
            return m.group(0)
        digest = hashlib.sha1(open(path, 'rb').read()).hexdigest()[:8]
        return f'{m.group(1)}{m.group(2)}?v={digest}{m.group(3)}'

    new = ASSET.sub(version, text)
    if new != text:
        open(html_path, 'w', encoding='utf-8').write(new)
        print('updated', html_path)


if __name__ == '__main__':
    for path in glob.glob('*.html') + glob.glob('completion-forms/**/*.html', recursive=True):
        stamp(path)
