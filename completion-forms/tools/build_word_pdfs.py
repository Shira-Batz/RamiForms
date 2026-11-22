"""Make a PDF version of every Word template, so the site can download filled forms as PDF.

For each <site>/templates/<id>.docx this builds <site>/templates-pdf/<id>.pdf (the form with its fields
left blank) and adds "pdfFields" (where each field goes on the page) to the form in <site>/forms.js.
How: every {{tag}} gets a unique text colour, LibreOffice converts the file to PDF, the coloured text
shows where each field is, and then that placeholder text is deleted. Underscore lines and checkboxes stay.

Needs LibreOffice, pdfplumber, pypdf, PyMuPDF and lxml, and fonts with the same widths as the Word fonts, or the
PDF's line breaks differ from Word's: Tahoma from Wine (apt install fonts-wine, then copy
/usr/share/wine/fonts/tahoma*.ttf to /usr/local/share/fonts), David -> Culmus "David CLM" (apt install culmus,
plus a fontconfig alias David -> David CLM), Calibri -> Carlito. Wine's Tahoma has no Hebrew letters, so
LibreOffice draws the Hebrew in DejaVu Sans; the site writes the values in DejaVu Sans too.
Run from the completion-forms folder, after build_forms.py:  python3 tools/build_word_pdfs.py general"""
import json, os, re, shutil, subprocess, sys, tempfile, zipfile
import pdfplumber, pymupdf  # PyMuPDF: to read exact baselines
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


def mark_docx(src, dst, keep_colors=False):
    """Copy of the template where each tag shows its placeholder text in its own colour.
    keep_colors: the same text in its original colour instead (the form as Word shows it when empty)."""
    tags = []
    def repl(m):
        rpr, key, original = m.groups()
        i = len(tags) + 1
        sz = re.search(r'<w:sz w:val="(\d+)"', rpr); szcs = re.search(r'<w:szCs w:val="(\d+)"', rpr)
        tags.append(dict(key=key, original=original, display=display_text(key, original),
                         sz=int(sz.group(1)) / 2 if sz else None, szcs=int(szcs.group(1)) / 2 if szcs else None,
                         rtl=bool(re.search(r'<w:rtl(?: w:val="(?:true|1|on)")?\s*/>', rpr))))
        if not keep_colors:
            rpr = re.sub(r'<w:color [^>]*/>', '', rpr) + f'<w:color w:val="{code_color(i)}"/>'
        # the empty form shows exactly what Word shows for an empty field (nothing, for an empty table cell)
        text = (tags[-1]['display'] if original or not keep_colors else '').replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
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
                           bold=sum('Bold' in c['fontname'] for c in line) > len(line) / 2,
                           all=[(c['x0'], c['top'], c['x1'], c['bottom']) for c in chars])
                mid = (box['top'] + box['bottom']) / 2
                others = [c for c in page.chars if color_index(c) != i and c['text'].strip()
                          and c['top'] - 1 <= mid <= c['bottom'] + 1 and c['x1'] <= box['x0'] + 1]
                walls = [e['x0'] for e in page.edges if e['orientation'] == 'v'
                         and e['top'] - 1 <= mid <= e['bottom'] + 1 and e['x0'] <= box['x0'] + 1]
                margin = min((c['x0'] for c in page.chars), default=30)
                box['left'] = max([c['x1'] for c in others] + walls + [margin])
                # signature image: keep clear of the line right above (e.g. its "חתימה:" label)...
                above = [c for c in page.chars if color_index(c) != i and c['text'].strip()
                         and box['top'] - 10 < c['bottom'] <= box['top'] + 4 and c['top'] < box['top'] - 2
                         and c['x1'] > box['left'] and c['x0'] < box['x1']]
                box['clear_right'] = min([c['x0'] for c in above] + [box['x1']])
                # ...and no taller than the free space above the line, left of that label
                over = [c['bottom'] for c in page.chars if color_index(c) != i and c['text'].strip()
                        and c['bottom'] < box['top'] + 4 and c['top'] < box['top'] - 2 and box['top'] - c['bottom'] < 45
                        and c['x1'] > box['left'] and c['x0'] < box['clear_right'] - 3]
                box['room_above'] = round(box['bottom'] - max(over + [box['top'] - 40]), 1)
                found[i] = box
    return found


def remove_colored_text(src, dst, colors):
    """Copy the PDF without the text drawn in one of `colors` (hex RRGGBB), touching nothing else."""
    from pypdf import PdfWriter
    from pypdf.generic import ContentStream
    targets = {tuple(round(int(c[k:k + 2], 16) / 255, 3) for k in (0, 2, 4)) for c in colors}
    writer = PdfWriter(clone_from=src)
    for page in writer.pages:
        content = ContentStream(page.get_contents(), writer)
        fill, stack, kept = None, [], []
        for operands, op in content.operations:
            if op == b'q': stack.append(fill)
            elif op == b'Q': fill = stack.pop() if stack else None
            elif op == b'rg': fill = tuple(round(float(v), 3) for v in operands)
            elif op in (b'g', b'k', b'sc', b'scn'): fill = None
            if op in (b'Tj', b'TJ', b"'", b'"') and fill in targets:
                continue
            kept.append((operands, op))
        content.operations = kept
        page.replace_contents(content)
    writer.write(dst)


def build(site, form_id, work):
    src = f'{site}/templates/{form_id}.docx'
    marked = os.path.join(work, f'f{abs(hash(form_id)) % 10**8}.docx')
    empty = os.path.join(work, f'e{abs(hash(form_id)) % 10**8}.docx')
    tags = mark_docx(src, marked)
    mark_docx(src, empty, keep_colors=True)  # same layout, original colours: the form left empty
    subprocess.run(['soffice', '--headless', '--convert-to', 'pdf', '--outdir', work, marked, empty],
                   check=True, capture_output=True)
    os.makedirs(f'{site}/templates-pdf-empty', exist_ok=True)
    shutil.copyfile(empty[:-5] + '.pdf', f'{site}/templates-pdf-empty/{form_id}.pdf')
    pdf_path = marked[:-5] + '.pdf'
    found = locate(pdf_path, tags)
    missing = [t['key'] for i, t in enumerate(tags, 1) if i not in found]
    assert not missing, f'{form_id}: fields not found in the PDF: {missing}'

    # the exact baseline of each placeholder (so the value sits where the placeholder text sat)
    doc = pymupdf.open(pdf_path)  # (only read here)
    baselines = {}
    for n, page in enumerate(doc):
        for block in page.get_text('rawdict')['blocks']:
            for line in block.get('lines', []):
                for span in line['spans']:
                    color = span['color']
                    if color >> 16 == 1 and span['chars']:
                        baselines.setdefault(color & 0xFFFF, round(span['chars'][0]['origin'][1], 1))

    # delete the placeholder text (lines to write on and checkboxes stay): only the text commands drawn
    # in a placeholder's colour are removed, so everything else in the PDF stays exactly as it was
    drop = {i for i, t in enumerate(tags, 1) if t['display'] != t['original'] and '=' not in t['key']}
    os.makedirs(f'{site}/templates-pdf', exist_ok=True)
    out = f'{site}/templates-pdf/{form_id}.pdf'
    remove_colored_text(pdf_path, out, {code_color(i) for i in drop})

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
        if b['bold']:
            f['bold'] = True  # Word writes the value in the formatting of the spot it replaces
        # Word sizes Hebrew by w:szCs and digits/English by w:sz: the measured size is the Hebrew one
        # (in a right-to-left run Word uses the Hebrew size for everything, digits included)
        if not t['rtl'] and t['sz'] and abs((t['sz'] if not t['szcs'] else b['size'] * t['sz'] / t['szcs']) - b['size']) > 0.2:
            f['sizeLatin'] = round(t['sz'] if not t['szcs'] else b['size'] * t['sz'] / t['szcs'], 1)
        if t['key'] == 'signature' or t['key'].endswith('.signature'):
            f['x1'] = round(b['clear_right'] - 3, 1)  # the image stays clear of the label above
            f['maxHeight'] = b['room_above']
        if t['display'] != t['original'] and t['original'] and '=' not in t['key']:
            # "<השלם מידע>": when the field is left empty the site copies these areas from the empty form,
            # so it looks exactly as in Word (also when the placeholder wrapped onto two lines)
            lines = {}
            for x0, top, x1, bottom in b['all']:
                key = next((k for k in lines if abs(k - top) < 3), top)
                lines.setdefault(key, []).append((x0, top, x1, bottom))
            f['placeholder'] = [[round(min(c[0] for c in cs) - 0.6, 1), round(min(c[1] for c in cs), 1),
                                 round(max(c[2] for c in cs) + 0.6, 1), round(max(c[3] for c in cs), 1)]
                                for cs in lines.values()]
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
