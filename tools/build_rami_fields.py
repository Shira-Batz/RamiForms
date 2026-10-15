"""Build rami-fields.js: where to write each field on the RAMI forms.
Each field is given by a point inside its table cell (the old hand-calibrated position: x from the left,
y from the top of an A4 page). The tool finds the cell in the PDF (dunam/formN.pdf, the same layout
as agro/) and the empty part of it (without the label text printed in the same cell). The site writes
the text right-aligned in that space and shrinks it if it doesn't fit.
Run from the repository root:  python3 tools/build_rami_fields.py"""
import json
import pdfplumber

# (form, downloaded file name, [(field name, key, x, y, page)])
FORMS = [
    ('form1', '1_הצהרת_בעלי_זכויות_ממולא.pdf', [
        ('יישוב', 'city', 466, 126, 0),
        ('רחוב', 'street', 333, 126, 0),
        ('מספר משק', 'farmNum', 255, 126, 0),
        ('ת.ד', 'mailBox', 170, 126, 0),
        ('מיקוד', 'zipCode', 68, 126, 0),
        ('גוש', 'block', 482, 157, 0),
        ('חלקה', 'parcel', 405, 157, 0),
        ('מגרש', 'plot', 335, 157, 0),
        ('תוכנית מתאר', 'plan', 190, 157, 0),
        ('מספר חוזה', 'contractNum', 62, 157, 0),
        ('מרחב מטפל', 'region', 482, 185, 0),
        # שני המגישים בשדה אחד ("שם 1, שם 2"), כדי שהשמות יהיו צמודים ולא מפוזרים על פני התא
        ('שמות מגישי הבקשה', 'applicantNames', 231, 278, 0),
    ]),
    ('form2', '2_בקשה_להקצאת_קרקע_ממולא.pdf', [
        ('מספר חוזה', 'contractNum', 350, 196, 0),
        ('שם פרטי 1', 'firstName1', 488, 242, 0),
        ('שם משפחה 1', 'lastName1', 402, 242, 0),
        ('ת.ז 1', 'idNum1', 175, 216, 0),
        ('שם פרטי 2', 'firstName2', 488, 298, 0),
        ('שם משפחה 2', 'lastName2', 402, 298, 0),
        ('ת.ז 2', 'idNum2', 175, 271, 0),
        ('יישוב', 'city', 448, 367, 0),
        ('רחוב', 'street', 330, 367, 0),
        ('מספר בית', 'houseNum', 266, 367, 0),
        ('מיקוד', 'zipCode', 128, 367, 0),
        ('ת.ד', 'mailBox', 42, 367, 0),
        ('מייל', 'email', 383, 406, 0),
        ('סעיף ג - יישוב', 'city', 408, 653, 0),
        ('סעיף ג - מספר משק', 'farmNum', 308, 653, 0),
        ('סעיף ג - גודל חלקה', 'livingArea', 192, 653, 0),
        ('סעיף ג - גוש', 'block', 504, 686, 0),
        ('סעיף ג - חלקה', 'parcel', 440, 686, 0),
    ]),
    ('form3', '3_תוספת_בנייה_ממולא.pdf', [
        ('מספר חוזה', 'contractNum', 30, 117, 0),
        ('שם פרטי 1', 'firstName1', 448, 203, 0),
        ('שם משפחה 1', 'lastName1', 300, 203, 0),
        ('ת.ז 1', 'idNum1', 130, 203, 0),
        ('שם פרטי 2', 'firstName2', 448, 215, 0),
        ('שם משפחה 2', 'lastName2', 300, 215, 0),
        ('ת.ז 2', 'idNum2', 130, 215, 0),
        ('יישוב', 'city', 450, 266, 0),
        ('רחוב', 'street', 295, 266, 0),
        ('מספר', 'houseNum', 184, 266, 0),
        ('מיקוד', 'zipCode', 42, 266, 0),
        ('מייל', 'email', 366, 314, 0),
        ('סעיף ה - גוש', 'block', 480, 85, 1),
        ('סעיף ה - חלקה', 'parcel', 370, 85, 1),
        ('סעיף ה - מגרש', 'plot', 184, 85, 1),
        ('סעיף ה - מס תוכנית', 'plan', 52, 85, 1),
        ('סעיף ה - יישוב', 'city', 464, 111, 1),
        ('סעיף ה - רחוב', 'street', 310, 111, 1),
        ('סעיף ה - מספר', 'houseNum', 185, 111, 1),
        ('סעיף ה - מיקוד', 'zipCode', 72, 111, 1),
    ]),
    ('form4', '4_ייפוי_כוח_ממולא.pdf', [
        ('מספר חוזה', 'contractNum', 22, 84, 0),
        ('שם פרטי 1', 'firstName1', 460, 494, 0),
        ('שם משפחה 1', 'lastName1', 312, 494, 0),
        ('תעודת זהות 1', 'idNum1', 190, 494, 0),
        ('שם פרטי 2', 'firstName2', 460, 514, 0),
        ('שם משפחה 2', 'lastName2', 312, 514, 0),
        ('תעודת זהות 2', 'idNum2', 190, 514, 0),
        ('יישוב', 'city', 460, 557, 0),
        ('רחוב', 'street', 300, 557, 0),
        ('מספר', 'houseNum', 186, 557, 0),
        ('מיקוד', 'zipCode', 45, 557, 0),
        ('מייל', 'email', 355, 597, 0),
        ('סעיף ג - גוש', 'block', 475, 681, 0),
        ('סעיף ג - חלקה', 'parcel', 375, 681, 0),
        ('סעיף ג - מגרש', 'plot', 185, 681, 0),
        ('סעיף ג - תוכנית', 'plan', 54, 681, 0),
        ('סעיף ג - עיר', 'city', 475, 707, 0),
        ('סעיף ג - רחוב', 'street', 326, 707, 0),
        ('סעיף ג - מספר', 'houseNum', 185, 707, 0),
        ('סעיף ג - מיקוד', 'zipCode', 54, 707, 0),
    ]),
    ('form5', '5_תצהיר_המבקש_ממולא.pdf', [
        ('מספר חוזה', 'contractNum', 48, 196, 0),
        ('שם פרטי 1', 'firstName1', 498, 292, 0),
        ('שם משפחה 1', 'lastName1', 412, 292, 0),
        ('תעודת זהות 1', 'idNum1', 185, 255, 0),
        ('שם פרטי 2', 'firstName2', 498, 360, 0),
        ('שם משפחה 2', 'lastName2', 412, 360, 0),
        ('תעודת זהות 2', 'idNum2', 185, 326, 0),
        ('יישוב', 'city', 480, 471, 0),
        ('רחוב', 'street', 365, 471, 0),
        ('מספר', 'houseNum', 284, 471, 0),
        ('מיקוד', 'zipCode', 60, 471, 0),
        ('תוכנית', 'plan', 472, 511, 0),
        ('מגרש', 'plot', 375, 511, 0),
        ('שטח', 'totalArea', 250, 511, 0),
        ('משק', 'farmNum', 108, 511, 0),
        ('גוש', 'block', 502, 555, 0),
        ('חלקה', 'parcel', 418, 555, 0),
    ]),
]

LINE = 2.5  # table borders are drawn as thin rectangles


def borders(page):
    vertical, horizontal = [], []
    for r in page.rects:
        w, h = r['x1'] - r['x0'], r['bottom'] - r['top']
        if w <= LINE and h > 4:
            vertical.append(((r['x0'] + r['x1']) / 2, r['top'], r['bottom']))
        if h <= LINE and w > 4:
            horizontal.append(((r['top'] + r['bottom']) / 2, r['x0'], r['x1']))
    return vertical, horizontal


def find_slot(page, x, y):
    """The empty space around point (x, baseline y from the top) inside its table cell."""
    baseline = page.height - (842 - y)  # the old code drew at 842 - y on every page size
    px, py = x + 2, baseline - 4        # a point inside the text the old code wrote
    vertical, horizontal = borders(page)
    left = max((vx for vx, t, b in vertical if vx <= px and t - 1 <= py <= b + 1), default=None)
    right = min((vx for vx, t, b in vertical if vx > px and t - 1 <= py <= b + 1), default=None)
    top = max((hy for hy, l, r in horizontal if hy <= py and l - 1 <= px <= r + 1), default=None)
    bottom = min((hy for hy, l, r in horizontal if hy > py and l - 1 <= px <= r + 1), default=None)
    if None in (left, right, top, bottom) or right - left > 560 or bottom - top > 45:
        return None
    # label text printed in the same cell, on the same line: keep clear of it
    line_chars = [c for c in page.chars if left < c['x0'] and c['x1'] < right and top < c['top'] < bottom
                  and c['bottom'] > baseline - 9 and c['top'] < baseline + 2 and c['text'].strip()]
    x0 = max([c['x1'] for c in line_chars if c['x1'] <= px] + [left])
    x1 = min([c['x0'] for c in line_chars if c['x0'] > px] + [right])
    return dict(x0=round(x0 + 2, 1), x1=round(x1 - 2, 1), baseline=round(842 - y, 1), cell=[round(left), round(right)])


if __name__ == '__main__':
    out = []
    for form, filename, fields in FORMS:
        with pdfplumber.open(f'dunam/{form}.pdf') as pdf:
            items = []
            for name, key, x, y, page in fields:
                slot = find_slot(pdf.pages[page], x, y)
                assert slot, f'{form} {name}: no table cell found around x={x} y={y}'
                items.append(dict(name=name, key=key, page=page, x=x, **slot))
            # two fields in the same cell and line (e.g. two names side by side): split the space
            # at the next field's starting point
            for f in items:
                nxt = [g['x'] for g in items if g is not f and g['page'] == f['page'] and g['cell'] == f['cell']
                       and g['baseline'] == f['baseline'] and g['x'] > f['x']]
                if nxt:
                    f['x1'] = min(f['x1'], min(nxt) - 4)
            for f in items:
                print(f"{form} {f['name']:22} x={f['x']:3} -> space {f['x0']:6}..{f['x1']:6} (cell {f['cell']})")
        out.append(dict(file=f'{form}.pdf', output=filename,
                        fields=[{k: v for k, v in f.items() if k not in ('cell', 'x')} for f in items]))
    with open('rami-fields.js', 'w', encoding='utf-8') as f:
        f.write('// נוצר אוטומטית ע"י tools/build_rami_fields.py - לא לערוך ידנית.\n'
                '// לכל שדה: העמוד, הרווח הפנוי בתא (x0..x1, בנקודות משמאל הדף) וגובה השורה (baseline, מתחתית הדף).\n'
                'const RAMI_FORMS = [\n' + ',\n'.join('    ' + json.dumps(o, ensure_ascii=False) for o in out) + '\n];\n')
