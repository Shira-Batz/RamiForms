"""Make a PDF version of every Word template, so the site can download filled forms as PDF.

For each <site>/templates/<id>.docx this builds <site>/templates-pdf/<id>.pdf (the form with its fields
left blank) and adds "pdfFields" (where each field goes on the page) to the form in <site>/forms.js.
How: every {{tag}} gets a unique text colour, LibreOffice converts the file to PDF, the coloured text
shows where each field is, and then that placeholder text is deleted. Underscore lines and checkboxes stay.

Needs LibreOffice, pdfplumber, PyMuPDF and lxml, and fonts with the same widths as the Word fonts, or the
PDF's line breaks differ from Word's: Tahoma from Wine (apt install fonts-wine, then copy
/usr/share/wine/fonts/tahoma*.ttf to /usr/local/share/fonts), David -> Culmus "David CLM" (apt install culmus,
plus a fontconfig alias David -> David CLM), Calibri -> Carlito. Wine's Tahoma has no Hebrew letters, so
LibreOffice draws the Hebrew in DejaVu Sans; the site writes the values in DejaVu Sans too.
Run from the completion-forms folder, after build_forms.py:  python3 tools/build_word_pdfs.py general"""
import json, os, re, subprocess, sys, tempfile, zipfile
import pdfplumber, pymupdf
from lxml import etree

W = 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'
q = lambda t: f'{{{W}}}{t}'
TAG_RUN = re.compile(r'<w:r><w:rPr>((?:(?!</w:rPr>).)*)</w:rPr><w:t xml:space="preserve">\{\{([^|}]+)\|([^}]*)\}\}</w:t></w:r>', re.S)


def code_color(i):
    return f'01{i // 256:02X}{i % 256:02X}'  # almost black, unique per field


def display_text(key, original):
    if '=' in key:
        return '☐'  # checkbox
    if re.fullmatch(r'[_.]+', original):
        return original  # a line to write on: stays in the PDF
    return f'<{original}>' if original else '________'


def freeze_filename_fields(xml):
    """LibreOffice garbles a FILENAME field with a Hebrew file name: keep its last shown text instead."""
    root = etree.fromstring(xml.encode())
    for p in root.iter(q('p')):
        runs = list(p.iter(q('r')))
        i = 0
        while i < len(runs):
            fc = runs[i].find(q('fldChar'))
            if fc is not None and fc.get(q('fldCharType')) == 'begin':
                j, instr, sep = i, '', None
                while j < len(runs):
                    t = runs[j].find(q('instrText'))
                    if t is not None: instr += t.text or ''
                    f = runs[j].find(q('fldChar'))
                    if f is not None and f.get(q('fldCharType')) == 'separate': sep = j
                    if f is not None and f.get(q('fldCharType')) == 'end': break
                    j += 1
                if 'FILENAME' in instr and sep is not None and j < len(runs):
                    for r in runs[i:sep + 1] + [runs[j]]:
                        r.getparent().remove(r)
                i = j + 1
            else:
                i += 1
    return etree.tostring(root, xml_declaration=True, encoding='UTF-8', standalone=True).decode()


def mark_docx(src, dst):
    """Copy of the template where each tag shows its placeholder text in its own colour."""
    tags = []
    def repl(m):
        rpr, key, original = m.groups()
        i = len(tags) + 1
        tags.append(dict(key=key, original=original, display=display_text(key, original)))
        rpr = re.sub(r'<w:color [^>]*/>', '', rpr) + f'<w:color w:val="{code_color(i)}"/>'
        text = tags[-1]['display'].replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
        return f'<w:r><w:rPr>{rpr}</w:rPr><w:t xml:space="preserve">{text}</w:t></w:r>'
    zin, zout = zipfile.ZipFile(src), zipfile.ZipFile(dst, 'w', zipfile.ZIP_DEFLATED)
    for item in zin.infolist():
        data = zin.read(item.filename)
        if re.match(r'word/(document|header\d*|footer\d*)\.xml$', item.filename):
            xml = TAG_RUN.sub(repl, data.decode('utf8'))
            if 'footer' in item.filename or 'header' in item.filename:
                xml = freeze_filename_fields(xml)
            data = xml.encode('utf8')
        zout.writestr(item, data)
    zout.close()
    return tags


def color_index(c):
    col = c.get('non_stroking_color')
    if not isinstance(col, (list, tuple)) or len(col) != 3:
        return None
    r, g, b = (round(v * 255) for v in col)
    return g * 256 + b if r == 1 else None


def main_run(line, page_chars, i):
    """The longest stretch of the field's characters with no other text in between. In a left-to-right
    paragraph a bracket of "<השלם מידע>" can end up on the far side of the label: ignore such strays."""
    line = sorted(line, key=lambda c: c['x0'])
    mid = (line[0]['top'] + line[0]['bottom']) / 2
    between = lambda a, b: any(color_index(o) != i and o['text'].strip() and a['x1'] - 1 <= o['x0'] and o['x1'] <= b['x0'] + 1
                               and o['top'] - 1 <= mid <= o['bottom'] + 1 for o in page_chars)
    runs, run = [], [line[0]]
    for prev, c in zip(line, line[1:]):
        if between(prev, c):
            runs.append(run); run = []
        run.append(c)
    runs.append(run)
    return max(runs, key=len)


def locate(pdf_path, tags):
    """Where each tag ended up: page, box, and the free space to its left on the same line."""
    found = {}
    with pdfplumber.open(pdf_path) as pdf:
        for n, page in enumerate(pdf.pages):
            groups = {}
            for c in page.chars:
                i = color_index(c)
                if i and c['text'].strip():
                    groups.setdefault(i, []).append(c)
            for i, chars in groups.items():
                if i in found:
                    continue
                first_top = min(c['top'] for c in chars)
                line = [c for c in chars if abs(c['top'] - first_top) < 3]  # if it wrapped, use its first line
                line = main_run(line, page.chars, i)
                box = dict(page=n, x0=min(c['x0'] for c in line), x1=max(c['x1'] for c in line),
                           top=min(c['top'] for c in line), bottom=max(c['bottom'] for c in line),
                           size=round(sum(c['size'] for c in line) / len(line), 1),
                           all=[(c['x0'], c['top'], c['x1'], c['bottom']) for c in chars])
                mid = (box['top'] + box['bottom']) / 2
                others = [c for c in page.chars if color_index(c) != i and c['text'].strip()
                          and c['top'] - 1 <= mid <= c['bottom'] + 1 and c['x1'] <= box['x0'] + 1]
                walls = [e['x0'] for e in page.edges if e['orientation'] == 'v'
                         and e['top'] - 1 <= mid <= e['bottom'] + 1 and e['x0'] <= box['x0'] + 1]
                margin = min((c['x0'] for c in page.chars), default=30)
                box['left'] = max([c['x1'] for c in others] + walls + [margin])
                found[i] = box
    return found


def build(site, form_id, work):
    src = f'{site}/templates/{form_id}.docx'
    marked = os.path.join(work, f'f{abs(hash(form_id)) % 10**8}.docx')
    tags = mark_docx(src, marked)
    subprocess.run(['soffice', '--headless', '--convert-to', 'pdf', '--outdir', work, marked],
                   check=True, capture_output=True)
    pdf_path = marked[:-5] + '.pdf'
    found = locate(pdf_path, tags)
    missing = [t['key'] for i, t in enumerate(tags, 1) if i not in found]
    assert not missing, f'{form_id}: fields not found in the PDF: {missing}'

    # the exact baseline of each placeholder (so the value sits where the placeholder text sat)
    doc = pymupdf.open(pdf_path)
    baselines = {}
    for n, page in enumerate(doc):
        for block in page.get_text('rawdict')['blocks']:
            for line in block.get('lines', []):
                for span in line['spans']:
                    color = span['color']
                    if color >> 16 == 1 and span['chars']:
                        baselines.setdefault(color & 0xFFFF, round(span['chars'][0]['origin'][1], 1))

    # delete the placeholder text (lines to write on and checkboxes stay)
    removed = 0
    for i, t in enumerate(tags, 1):
        if t['display'] == t['original'] or '=' in t['key']:
            continue
        page = doc[found[i]['page']]
        for x0, top, x1, bottom in found[i]['all']:
            h = bottom - top  # only the middle of the line: close lines' character boxes overlap
            page.add_redact_annot(pymupdf.Rect(x0 + 0.3, top + 0.3 * h, x1 - 0.3, bottom - 0.3 * h), fill=None)
            removed += 1
    for page in doc:
        page.apply_redactions(images=pymupdf.PDF_REDACT_IMAGE_NONE, graphics=pymupdf.PDF_REDACT_LINE_ART_NONE,
                              text=pymupdf.PDF_REDACT_TEXT_REMOVE)
    os.makedirs(f'{site}/templates-pdf', exist_ok=True)
    out = f'{site}/templates-pdf/{form_id}.pdf'
    doc.save(out, garbage=3, deflate=True)

    # nothing but the placeholders may have been deleted
    with pdfplumber.open(pdf_path) as before, pdfplumber.open(out) as after:
        for pb, pa in zip(before.pages, after.pages):
            keep = lambda cs, drop: sorted(c['text'] for c in cs if c['text'].strip() and color_index(c) not in drop)
            drop = {i for i, t in enumerate(tags, 1) if t['display'] != t['original'] and '=' not in t['key']}
            assert keep(pb.chars, drop) == keep(pa.chars, drop), f'{form_id}: other text was deleted'
            assert not [c for c in pa.chars if color_index(c) in drop and c['text'].strip()], f'{form_id}: placeholder text left'

    fields = []
    for i, t in enumerate(tags, 1):
        b = found[i]
        f = dict(key=t['key'], page=b['page'], x0=round(b['left'] + 2, 1), x1=round(b['x1'], 1),
                 top=round(b['top'], 1), baseline=baselines.get(i), size=b['size'])
        if '=' in t['key']:  # checkbox: keep the box itself
            f.update(x0=round(b['x0'], 1), bottom=round(b['bottom'], 1))
        fields.append(f)
    return fields


if __name__ == '__main__':
    site = sys.argv[1]
    path = f'{site}/forms.js'
    text = open(path, encoding='utf-8').read()
    head, body = text.split('const FORMS = [', 1)
    forms = json.loads('[' + body.rsplit('];', 1)[0].strip().rstrip(',') + ']')
    with tempfile.TemporaryDirectory() as work:
        for form in forms:
            if form.get('type') == 'pdf':
                continue
            form['pdfFields'] = build(site, form['id'], work)
            print(f"{form['id']}: {len(form['pdfFields'])} fields")
    lines = ',\n'.join('    ' + json.dumps(o, ensure_ascii=False) for o in forms)
    with open(path, 'w', encoding='utf-8') as f:
        f.write(head + 'const FORMS = [\n' + lines + '\n];\n')
