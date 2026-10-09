"""Tag the blank lines of Omer's local forms using a per-form ordered mapping."""
import copy, re, sys, zipfile, json
from lxml import etree
from tag import q, replace_span, texts, XML_SPACE
from blanks import BLANK

MAPS = {  # blank index -> field key (None = leave blank, e.g. signature lines)
    '1.2': ['plot', 'fileNum', 'parcel', 'city', 'requestNum', 'nature', 'owner.name', 'owner.address', 'owner.phone'],
    '4.1': ['date', 'skeleton.name', 'skeleton.license', 'foundationsDate', 'plot', 'street', 'city', None, None],
    '5.1': ['fileNum', 'skeleton.name', 'skeleton.id', 'skeleton.address', None, 'block', 'parcel', 'permitNum'],
    '6.1': ['fileNum', 'skeleton.name', 'skeleton.id', 'skeleton.license', 'skeleton.address', 'siteAddressBlockParcel', 'permitNum', None],
    'פרטי-התקשרות': ['nature', 'city', 'street', 'houseNum', 'block', 'parcel', 'plot', 'requestNum', 'owner.name', 'date', None],
}
TABLE_ROLES = ['owner', 'architect', 'supervisor', 'skeleton', 'contractor']

def tag_blanks(root, mapping):
    paras = [p for p in root.iter(q('p')) if not any(a.tag.endswith('Fallback') for a in p.iterancestors())]
    found = []
    for p in paras:
        full = ''.join(t.text or '' for t in texts(p))
        found += [(p, m) for m in BLANK.finditer(full)]
    used = []
    for (p, m), key in reversed(list(zip(found, mapping))):
        if key:
            replace_span(p, m.start(), m.end(), f'{{{{{key}|{m.group(0)}}}}}', blue=False); used.append(key)
    return used

def tag_roles_table(root):
    used = []
    rows = list(root.iter(q('tr')))[1:]
    for role, tr in zip(TABLE_ROLES, rows):
        cells = tr.findall(q('tc'))
        label_rpr = next(cells[0].iter(q('rPr')), None)
        for tc, field in zip(cells[1:], ['name', 'phone', 'email']):
            p = tc.find(q('p'))
            r = etree.SubElement(p, q('r'))
            if label_rpr is not None:
                rpr = copy.deepcopy(label_rpr)
                for el in rpr.findall(q('b')) + rpr.findall(q('bCs')): rpr.remove(el)
                r.append(rpr)
            t = etree.SubElement(r, q('t')); t.text = f'{{{{{role}.{field}|}}}}'; t.set(XML_SPACE, 'preserve')
            used.append(f'{role}.{field}')
    return used

def main(src, dst, name):
    zin = zipfile.ZipFile(src); zout = zipfile.ZipFile(dst, 'w', zipfile.ZIP_DEFLATED); used = []
    for item in zin.infolist():
        data = zin.read(item.filename)
        if item.filename == 'word/document.xml':
            root = etree.fromstring(data)
            used += tag_blanks(root, MAPS[name])
            if name == 'פרטי-התקשרות': used += tag_roles_table(root)
            data = etree.tostring(root, xml_declaration=True, encoding='UTF-8', standalone=True)
        zout.writestr(item, data)
    zout.close()
    print(json.dumps(sorted(used), ensure_ascii=False))

if __name__ == '__main__':
    main(*sys.argv[1:4])
