"""Find the '____' blank lines in a PDF and the label before each one (Hebrew, right-to-left).
Run directly to list them:  python3 tools/pdf_blanks.py file.pdf [page ...]"""
import sys
import pdfplumber


def blanks(page):
    """Return the blanks of a page in reading order (top to bottom, right to left)."""
    lines = []  # group underscores into text lines (a line's characters can differ slightly in height)
    for c in sorted((c for c in page.chars if c['text'] == '_'), key=lambda c: c['top']):
        if lines and c['top'] - lines[-1][-1]['top'] < 2:
            lines[-1].append(c)
        else:
            lines.append([c])
    runs = []
    for line in lines:  # within a line, join touching underscores (right to left) into one blank
        r = None
        for c in sorted(line, key=lambda c: -c['x0']):
            if r and abs(r['x0'] - c['x1']) < 3:
                r['x0'] = min(r['x0'], c['x0']); r['n'] += 1
            else:
                r = dict(x0=c['x0'], x1=c['x1'], top=c['top'], bottom=c['bottom'], size=c['size'], n=1)
                runs.append(r)
    runs = [r for r in runs if r['n'] >= 3]
    others = [c for c in page.chars if c['text'] != '_']
    for r in runs:
        # the label is the text on the same line, between this blank and the next blank to its right
        right_edge = min([o['x0'] for o in runs if o is not r and abs(o['top'] - r['top']) < 3 and o['x0'] > r['x1']] + [page.width])
        mid = (r['top'] + r['bottom']) / 2
        chars = sorted((c for c in others if c['top'] - 3 <= mid <= c['bottom'] + 3
                        and c['x0'] >= r['x1'] - 1 and c['x1'] <= right_edge + 1), key=lambda c: -c['x0'])
        label, prev = '', None
        for c in chars:
            if prev is not None and prev['x0'] - c['x1'] > 1.5: label += ' '
            label += c['text']; prev = c
        r['label'] = ' '.join(label.split())
    runs.sort(key=lambda r: (round(r['top'] / 4), -r['x1']))
    return [dict(label=r['label'], x0=round(r['x0'], 1), x1=round(r['x1'], 1), top=round(r['top'], 1),
                 bottom=round(r['bottom'], 1), size=round(r['size'], 1)) for r in runs]


if __name__ == '__main__':
    path, pages = sys.argv[1], [int(p) for p in sys.argv[2:]]
    with pdfplumber.open(path) as pdf:
        for n, page in enumerate(pdf.pages, 1):
            if pages and n not in pages:
                continue
            bs = blanks(page)
            print(f'--- page {n}: {len(bs)} blanks')
            for k, b in enumerate(bs):
                print(f"  {k:2} [{b['label'][-34:]}]  x={b['x0']}-{b['x1']} top={b['top']}")
