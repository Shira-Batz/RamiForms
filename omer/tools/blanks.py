"""Find blank lines (____ or .....) in a docx. Run directly to list them with their position numbers."""
import re, sys, zipfile
from lxml import etree
W='http://schemas.openxmlformats.org/wordprocessingml/2006/main'
BLANK=re.compile(r'_{3,}|\.{5,}')
def blanks(path):
    root=etree.fromstring(zipfile.ZipFile(path).read('word/document.xml'))
    out=[]
    for p in root.iter(f'{{{W}}}p'):
        if any(a.tag.endswith('Fallback') for a in p.iterancestors()): continue
        t=''.join(x.text or '' for x in p.iter(f'{{{W}}}t'))
        for m in BLANK.finditer(t): out.append((t,m))
    return out
if __name__=='__main__':
    for i,(t,m) in enumerate(blanks(sys.argv[1])):
        print(i, repr(t[max(0,m.start()-35):m.start()].strip()), '>>', m.group(0)[:6], '<<', repr(t[m.end():m.end()+20].strip()))
