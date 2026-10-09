"""Turn <השלם מידע>-style placeholders in the official forms into {{key|original}} tags."""
import copy, re, sys, zipfile, json
from lxml import etree

W = 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'
q = lambda t: f'{{{W}}}{t}'
XML_SPACE = '{http://www.w3.org/XML/1998/namespace}space'

ROLE_NAMES = [  # order matters: more specific first
    ('שם האחראי משנה לביקורת', 'subSupervisor'), ('שם אחראי משנה לביקורת', 'subSupervisor'),
    ('שם האחראי לביקורת', 'supervisor'), ('שם האחראי לביצוע שלד', 'skeleton'),
    ('שם קבלן רשום', 'contractor'), ('תיאום עם מכון הבקרה', 'coordinator'),
    ('שם מודד מוסמך', 'surveyor'), ('שם עורך בקשה ראשי', 'architect'),
    ('שם עורך משנה הנדסת מבנים', 'structural'), ('שם עורך משנה', 'subEditor'),
    ('שם העובד', 'worker'), ('שם בעל ההיתר', 'owner'),
]
PERSON_FIELDS = [('תוקף רישיון', 'licenseExpiry'), ('רישיון קבלן', 'license'), ('מ.ר', 'license'),
                 ('ח.פ', 'id'), ('ע.מ', 'id'), ('ת.ז', 'id'), ('דרכון', 'id'),
                 ('טלפון', 'phone'), ('מייל', 'email'), ('כתובת', 'address')]
HEADER = [('מהות הבקשה', 'nature'), ('מגרש לפי תכנית', 'plot'), ('מס\' בית', 'houseNum'),
          ('רחוב', 'street'), ('יישוב', 'city'), ('חלקה', 'parcel'), ('גוש', 'block'),
          ('מס\' בקשה להיתר', 'requestNum'), ('שם מכון הבקרה', 'controlInstitute'),
          ('מס\' היתר', 'permitNum'), ('שם בעל ההיתר', 'owner.name')]
SIGNERS = [('אחראי משנה', 'subSupervisor'), ('אחראי לביקורת', 'supervisor'), ('בעל ההיתר', 'owner'),
           ('מודד', 'surveyor'), ('קבלן', 'contractor'), ('שלד', 'skeleton'), ('תיאום', 'coordinator'),
           ('עורך בקשה ראשי', 'architect'), ('הנדסת מבנים', 'structural'), ('עורך משנה', 'subEditor')]

def first(pairs, text):
    return next((v for k, v in pairs if k in text), None)

def key_for(ph, label, role, para_text):
    """ph: text inside <>, label: text since previous placeholder, role: person of this paragraph."""
    if 'רשות' in ph and 'רישוי' in ph: return 'authority'
    r = first(ROLE_NAMES, ph)
    if r: return f'{r}.name'
    lab = label.strip()
    if role:
        f = first(PERSON_FIELDS, lab[-25:])
        if f: return f'{role}.{f}'
    if lab.endswith('הופיע בפניי'): return 'signerName'   # אישור עו"ד: המצהיר הוא החותם על הטופס
    if 'זיהה את עצמו' in lab: return 'signerId'
    if lab == 'שם:': return 'signerName'
    if lab == 'תאריך:': return 'date'
    if 'המועד הצפוי לתחילת ביצוע' in lab: return 'startDate'
    if lab.endswith('ביום') and 'מתווה' in para_text: return 'markingDate'
    if lab == 'ביום': return 'visitDate'
    h = first(HEADER, lab[-20:])
    if h: return h
    f = first(PERSON_FIELDS, lab[-25:])
    if f and lab.endswith(':'): return f'owner.{f}'  # בלוק "פרטי בעל ההיתר" (תוויות עם נקודתיים)
    return None

def texts(p):
    return [t for t in p.iter(q('t'))]

def process_para(p, report):
    ts = texts(p)
    full = ''.join(t.text or '' for t in ts)
    matches = list(re.finditer(r'<([^<>]{2,45})>', full))
    if not matches: return
    # decide keys left-to-right (role context flows forward)
    role, prev_end, keys = None, 0, []
    for m in matches:
        label = re.sub(r'<[^<>]*>', '', full[prev_end:m.start()])
        r = first(ROLE_NAMES, m.group(1))
        if r and r != 'owner' or (r == 'owner' and 'אני הח' in full[:m.start()]): role = r
        k = key_for(m.group(1), label, role, full)
        keys.append(k); prev_end = m.end()
        report.append((k, m.group(1), label.strip()[-30:]))
    for m, k in reversed(list(zip(matches, keys))):
        if k: replace_span(p, m.start(), m.end(), f'{{{{{k}|{m.group(1)}}}}}')

def replace_span(p, start, end, tag, blue=True):
    ts = texts(p)
    pos, spans = 0, []
    for t in ts:
        n = len(t.text or ''); spans.append((t, pos, pos + n)); pos += n
    inner = next(t for t, a, b in spans if a <= start + 1 < b)
    tag_rpr = inner.getparent().find(q('rPr'))
    anchor_t, anchor_off = next((t, start - a) for t, a, b in spans if a <= start < b)
    for t, a, b in spans:  # cut placeholder chars
        lo, hi = max(start, a), min(end, b)
        if lo < hi: t.text = t.text[:lo - a] + t.text[hi - a:]
    run = anchor_t.getparent()
    before, after = anchor_t.text[:anchor_off], anchor_t.text[anchor_off:]
    # split run: run keeps text before, run2 gets text after
    run2 = copy.deepcopy(run)
    kids = list(run); idx = kids.index(anchor_t)
    for c in kids[idx + 1:]: run.remove(c)
    anchor_t.text = before; anchor_t.set(XML_SPACE, 'preserve')
    kids2 = list(run2); t2 = kids2[idx]
    for c in kids2[:idx]:
        if c.tag != q('rPr'): run2.remove(c)
    t2.text = after; t2.set(XML_SPACE, 'preserve')
    # tag run: placeholder formatting without the gray placeholder style, in blue
    tr = etree.Element(q('r'))
    rpr = copy.deepcopy(tag_rpr) if tag_rpr is not None else etree.Element(q('rPr'))
    for el in rpr.findall(q('rStyle')) + rpr.findall(q('color')): rpr.remove(el)
    if blue:
        color = etree.Element(q('color')); color.set(q('val'), '0070C0'); rpr.append(color)
    tr.append(rpr)
    tt = etree.SubElement(tr, q('t')); tt.text = tag; tt.set(XML_SPACE, 'preserve')
    parent = run.getparent(); i = parent.index(run)
    parent.insert(i + 1, tr); parent.insert(i + 2, run2)
    for r in (run, run2):  # drop now-empty runs
        if not ''.join(x.text or '' for x in r.iter(q('t'))) and len([c for c in r if c.tag not in (q('rPr'), q('t'))]) == 0:
            r.getparent().remove(r)

def signer_of(root):
    paras = [''.join(t.text or '' for t in p.iter(q('t'))).strip() for p in root.iter(q('p'))]
    paras = [x for x in paras if x]
    for i, x in enumerate(paras):
        if x.startswith('חתימה') and i + 1 < len(paras):
            return first(SIGNERS, paras[i + 1]), paras[i + 1]
    return None, None

def tag_file(src, dst):
    zin = zipfile.ZipFile(src); report = []
    zout = zipfile.ZipFile(dst, 'w', zipfile.ZIP_DEFLATED)
    signer = None
    for item in zin.infolist():
        data = zin.read(item.filename)
        if re.match(r'word/(document|header\d*|footer\d*)\.xml$', item.filename):
            root = etree.fromstring(data)
            if item.filename == 'word/document.xml': signer = signer_of(root)
            for p in root.iter(q('p')): process_para(p, report)
            data = etree.tostring(root, xml_declaration=True, encoding='UTF-8', standalone=True)
        zout.writestr(item, data)
    zout.close()
    return report, signer

if __name__ == '__main__':
    src, dst = sys.argv[1], sys.argv[2]
    report, signer = tag_file(src, dst)
    print(json.dumps({'signer': signer, 'tags': report}, ensure_ascii=False))
