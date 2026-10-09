"""Build forms.js (the list of forms + which fields each one uses) from templates/*.docx.
Run from the omer folder:  python3 tools/build_forms.py
To add a form: put its tagged template in templates/ and add a line to FORMS below."""
import glob, json, re, zipfile

# (stage, id = template file name, title, signer = who signs the form, or None)
FORMS = [
    ('start', 'ג-1', 'הודעה על מינוי אחראי לביקורת על הביצוע', 'owner'),
    ('start', 'ג-2', 'הודעה על מינוי אחראי משנה לביקורת על הביצוע', 'owner'),
    ('start', 'ג-3', 'הודעה על מינוי האחראי לביצוע שלד הבניין', 'owner'),
    ('start', 'ג-4', 'הודעה על מינוי קבלן רשום לביצוע הבנייה או העבודה', 'owner'),
    ('start', 'ג-5', 'הודעה על מינוי אחראי לתיאום עם מכון הבקרה', 'owner'),
    ('start', 'ג-6', 'הצהרת אחראי לביקורת על הביצוע', 'supervisor'),
    ('start', 'ג-7', 'הצהרת אחראי משנה לביקורת על הביצוע', 'subSupervisor'),
    ('start', 'ג-8', 'הצהרת אחראי לביצוע שלד הבניין', 'skeleton'),
    ('start', 'ג-9', 'הצהרת קבלן רשום לביצוע הבנייה או העבודה', 'contractor'),
    ('start', 'ג-10', 'הצהרת אחראי לביקורת על הביצוע - פינוי פסולת בניין', 'supervisor'),
    ('start', 'ג-11', 'הצהרת אחראי לתיאום עם מכון הבקרה', 'coordinator'),
    ('start', 'ג-12', 'אישור מודד מוסמך בדבר סימון מתווה הבניין', 'surveyor'),
    ('start', 'ג-13', 'בקשה לאישור תחילת עבודות', 'supervisor'),
    ('start', 'פרטי-התקשרות', 'טופס פרטי התקשרות - מינוי בעלי תפקידים', None),
    ('start', '1.2', 'טופס 1.2 - התחייבות המבקש: טרם ביצוע תשתיות', None),
    ('start', '3.1', 'טופס 3.1 - התחייבות המבקש: טרם תחילת עבודות', None),
    ('during', 'ד-1', 'דיווח אחראי לביקורת על הביצוע על עריכת ביקורת באתר', 'supervisor'),
    ('during', 'ד-2', 'דיווח אחראי משנה לביקורת על הביצוע על עריכת ביקורת באתר', 'subSupervisor'),
    ('during', '4.1', 'טופס 4.1 - התאמת היסודות וגובה 0.00', None),
    ('during', '5.1', 'טופס 5.1 - תצהיר האחראי לביצוע השלד (ממ"ד)', None),
    ('during', '6.1', 'טופס 6.1 - תצהיר אחראי לביצוע שלד הבניין', None),
    ('final', 'ה-1', 'הצהרת עורך בקשה ראשי', 'architect'),
    ('final', 'ה-2', 'הצהרת עורך משנה הנדסת מבנים', 'structural'),
    ('final', 'ה-3', 'הצהרת עורך משנה', 'subEditor'),
    ('final', 'ה-5', 'הצהרת קבלן רשום לביצוע הבנייה או העבודה', 'contractor'),
    ('final', 'ה-6', 'הצהרת אחראי משנה לביקורת על הביצוע', 'subSupervisor'),
    ('final', 'ה-7', 'בקשה לקבלת תעודת גמר', 'supervisor'),
]

def keys_of(path):
    z = zipfile.ZipFile(path); keys = set()
    for n in z.namelist():
        if re.match(r'word/(document|header\d*|footer\d*)\.xml$', n):
            keys |= set(re.findall(r'\{\{([^|}]+)\|', z.read(n).decode()))
    return sorted(keys)

if __name__ == '__main__':
    templates = {p[len('templates/'):-len('.docx')] for p in glob.glob('templates/*.docx')}
    missing = templates ^ {f[1] for f in FORMS}
    assert not missing, f'templates and FORMS do not match: {missing}'
    out = []
    for stage, id, title, signer in FORMS:
        keys = keys_of(f'templates/{id}.docx')
        assert signer or not {'signerName', 'signerId'} & set(keys), f'{id} needs a signer'
        out.append(dict(id=id, stage=stage, title=title, signer=signer, keys=keys))
    lines = ',\n'.join('    ' + json.dumps(o, ensure_ascii=False) for o in out)
    with open('forms.js', 'w', encoding='utf-8') as f:
        f.write('// נוצר אוטומטית ע"י tools/build_forms.py - לא לערוך ידנית.\n'
                '// keys = השדות שמופיעים בכל טופס. signer = מי חותם (השם שלו נכנס ל"שם:" בתחתית הטופס).\n'
                'const FORMS = [\n' + lines + '\n];\n')
    print(f'forms.js: {len(out)} forms')
