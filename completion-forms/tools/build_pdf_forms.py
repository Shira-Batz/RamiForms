"""Build a PDF-based site (Sdot Dan): split the committee's booklets into one PDF per form,
find the position of every '____' blank, and write <site>/forms.js with the field coordinates.
Run from the completion-forms folder:
    python3 tools/build_pdf_forms.py sdot-dan path/to/start.pdf path/to/book.pdf
The booklets are given in the order of the SOURCES list below."""
import json, os, sys
import pdfplumber
from pypdf import PdfReader, PdfWriter
from pdf_blanks import blanks

# The blank-line header that opens most forms ("פרטי הבקשה והמקרקעין" + "פרטי בעל ההיתר"),
# mapped by its label.
HEADER = {
    'מהות הבקשה:': 'nature', 'יישוב:': 'city', 'רחוב:': 'street', "מס' בית:": 'houseNum', 'גוש:': 'block',
    'חלקה:': 'parcel', 'מגרש לפי תכנית:': 'plot', "מס' בקשה להיתר:": 'requestNum', 'שם בעל ההיתר:': 'owner.name',
    "מס' ת.ז./ מס' דרכון/ תאגיד:": 'owner.id', 'טלפון:': 'owner.phone', 'מייל:': 'owner.email', 'כתובת:': 'owner.address',
}
SIGN = ['signerName', 'date', 'signature']  # the "שם: / תאריך: / חתימה:" lines at the bottom


def person(role, contractor=False):
    """A person's details line: name, ID, license, (license expiry), phone, email, address."""
    return [f'{role}.name', f'{role}.id', f'{role}.license'] + ([f'{role}.licenseExpiry'] if contractor else []) + \
           [f'{role}.phone', f'{role}.email', f'{role}.address']


worker = person('worker')

SITES = {
    'sdot-dan': {
        'sources': ['start', 'book'],
        # (stage, id, title, signer, source, pages (1-based), {page: keys for the blanks after the header})
        # None = a blank the site doesn't fill. A page with header=False has no standard header.
        'forms': [
            ('start', 'start-0', 'אישור על קבלת הנחיות לאישור תחילת עבודות', 'owner', 'start', [1, 2], {1: SIGN}),
            ('start', 'start-1', 'מסמך 1 - בקשה לאישור תחילת עבודות', 'supervisor', 'start', [3],
             {3: person('supervisor') + [None, None, None, 'startDate'] + SIGN}),
            ('start', 'start-2', 'מסמך 2 - אישור מודד מוסמך בדבר סימון מתווה הבניין', 'surveyor', 'start', [4],
             {4: person('surveyor') + ['markingDate'] + SIGN}),
            ('start', 'start-3', 'מסמך 3 - הודעה על מינוי קבלן רשום', 'owner', 'start', [5],
             {5: ['owner.name'] + person('contractor', True) + SIGN}),
            ('start', 'start-4', 'מסמך 4 - הודעה על מינוי האחראי לביצוע שלד הבניין', 'contractor', 'start', [6],
             {6: person('contractor', True) + person('skeleton') + SIGN}),
            ('start', 'start-5', 'מסמך 5 - הודעה על מינוי אחראי לביקורת על הביצוע', 'owner', 'start', [7],
             {7: ['owner.name'] + person('supervisor') + SIGN}),
            ('start', 'start-6', 'מסמך 6 - הצהרת קבלן רשום', 'contractor', 'start', [8],
             {8: person('contractor', True) + SIGN}),
            ('start', 'start-7', 'מסמך 7 - הצהרת אחראי לביצוע שלד הבניין', 'skeleton', 'start', [9],
             {9: person('skeleton') + SIGN}),
            ('start', 'start-8', 'מסמך 8 - הצהרת אחראי לביקורת על הביצוע', 'supervisor', 'start', [10],
             {10: person('supervisor') + SIGN}),
            ('start', 'start-9', 'מסמך 9 - הצהרת אחראי לביקורת על הביצוע - פינוי פסולת בניין', 'supervisor', 'start', [11],
             {11: person('supervisor') + SIGN}),
            ('start', 'start-10', 'מסמך 10 - התחייבות לגידור האתר והצבת שלט', 'owner', 'start', [12],
             {12: ['owner.name'] + SIGN}),

            ('during', 'book-0', 'אישור על קבלת הנחיות למהלך הביצוע ולתעודת גמר', 'owner', 'book', [1, 2, 3, 4], {1: SIGN}),
            ('during', 'during-1', "מסמך 1 - דיווח אחראי לביקורת על הביצוע - שלב א'", 'supervisor', 'book', [5],
             {5: person('supervisor') + ['visitDate'] + SIGN}),
            ('during', 'during-2', "מסמך 2 - דיווח אחראי לביקורת על הביצוע - שלב ב'", 'supervisor', 'book', [6],
             {6: person('supervisor') + ['visitDate'] + SIGN}),
            ('during', 'during-3', "מסמך 3 - דיווח אחראי לביקורת על הביצוע - שלב ג'", 'supervisor', 'book', [7],
             {7: person('supervisor') + ['visitDate'] + SIGN}),
            ('during', 'during-4', "מסמך 4 - דיווח אחראי לביקורת על הביצוע - שלב ד'", 'supervisor', 'book', [8],
             {8: person('supervisor') + ['visitDate'] + SIGN}),

            ('final', 'final-5', 'מסמך 5 - בקשה לקבלת תעודת גמר', 'supervisor', 'book', [9, 10],
             {9: person('supervisor'), 10: ('no header', ['permitNum', None, None, None] + SIGN)}),
            ('final', 'final-6', 'מסמך 6 - הצהרת עורך בקשה ראשי', 'architect', 'book', [11],
             {11: person('architect') + worker + SIGN}),
            ('final', 'final-7', 'מסמך 7 - הצהרת עורך משנה הנדסת מבנים', 'structural', 'book', [12],
             {12: person('structural') + worker + SIGN}),
            ('final', 'final-8', 'מסמך 8 - הצהרת קבלן רשום', 'contractor', 'book', [13],
             {13: person('contractor', True) + SIGN}),
            ('final', 'final-9', 'מסמך 9 - הצהרת אחראי לביקורת על הביצוע', 'supervisor', 'book', [14],
             {14: person('supervisor') + [None] + SIGN}),
            ('final', 'final-10', 'מסמך 10 - הצהרת מודד', 'surveyor', 'book', [15],
             {15: person('surveyor') + ['measureDate', 'permitNum', 'permitDate'] + SIGN}),
            # no blank for the name after "אני הח"מ" - the name goes only next to "שם:"
            ('final', 'final-11', 'מסמך 11 - הצהרת מורשה נגישות', 'accessibility', 'book', [16],
             {16: person('accessibility')[1:] + worker + SIGN}),
            ('final', 'final-12', 'מסמך 12 - אישור ועד המושב', None, 'book', [17], {17: [None, None, None]}),
            ('final', 'final-13', 'מסמך 13 - אישור מחלקת גבייה', None, 'book', [18], {18: [None, None, None]}),
            ('final', 'final-14', 'מסמך 14 - בקשה לשחרור ערבות בנקאית', 'owner', 'book', [19],
             {19: ['guaranteeNum', 'guaranteeDate', 'guaranteeAmount', 'permitNum', 'permitDate'] + SIGN}),
        ],
    },
}


def page_fields(page, keys):
    """Match the blanks of a page to field keys: the standard header by label, then `keys` in order."""
    has_header = not (isinstance(keys, tuple) and keys[0] == 'no header')
    if not has_header:
        keys = keys[1]
    bs = blanks(page)
    head = []
    if has_header:
        head = [HEADER[b['label']] for b in bs[:13]]
        assert sorted(head) == sorted(HEADER.values()), [b['label'] for b in bs[:13]]
    rest = bs[len(head):]
    assert len(rest) == len(keys), f'page has {len(rest)} blanks after the header, mapping has {len(keys)}'
    fields = []
    for b, key in zip(bs, head + list(keys)):
        if key:
            fields.append(dict(key=key, x0=b['x0'], x1=b['x1'], top=b['top'], size=b['size']))
    return fields


if __name__ == '__main__':
    site, paths = sys.argv[1], sys.argv[2:]
    cfg = SITES[site]
    sources = dict(zip(cfg['sources'], paths))
    os.makedirs(f'{site}/templates', exist_ok=True)
    out = []
    for stage, id, title, signer, source, pages, mapping in cfg['forms']:
        reader, writer = PdfReader(sources[source]), PdfWriter()
        for n in pages:
            writer.add_page(reader.pages[n - 1])
        with open(f'{site}/templates/{id}.pdf', 'wb') as f:
            writer.write(f)
        fields = []
        with pdfplumber.open(sources[source]) as pdf:
            for i, n in enumerate(pages):
                if n in mapping:
                    fields += [dict(page=i, **f) for f in page_fields(pdf.pages[n - 1], mapping[n])]
        keys = sorted({f['key'] for f in fields})
        assert signer or not {'signerName', 'signature'} & set(keys), f'{id} needs a signer'
        out.append(dict(id=id, stage=stage, title=title, signer=signer, type='pdf', keys=keys, fields=fields))
    lines = ',\n'.join('    ' + json.dumps(o, ensure_ascii=False) for o in out)
    with open(f'{site}/forms.js', 'w', encoding='utf-8') as f:
        f.write('// נוצר אוטומטית ע"י tools/build_pdf_forms.py - לא לערוך ידנית.\n'
                '// טפסי PDF: fields = מיקום כל קו ריק בטופס (בנקודות, מראש העמוד) והשדה שנכתב עליו.\n'
                'const FORMS = [\n' + lines + '\n];\n')
    print(f'{site}/forms.js: {len(out)} forms, {sum(len(o["fields"]) for o in out)} fields')
