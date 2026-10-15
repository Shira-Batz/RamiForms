// הקוד המשותף לכל אתרי טפסי הוועדות (כללי, עומר, ...).
// כל אתר מגדיר לפני הקובץ הזה: FORMS (ב-forms.js) ו-SITE = { authority, city }.

const STAGES = {
    start: 'תחילת עבודות',
    during: 'מהלך ביצוע',
    final: 'תעודת גמר',
    during_final: 'מהלך ביצוע ותעודת גמר' // חוברת אחת לשני השלבים (שדות דן)
};

// שדות הבקשה. key = השם שמופיע בתבניות ({{key|...}})
const PROJECT_FIELDS = [
    { key: 'authority', label: 'רשות הרישוי', value: SITE.authority || '' },
    { key: 'nature', label: 'מהות הבקשה' },
    { key: 'city', label: 'יישוב', value: SITE.city || '' },
    { key: 'street', label: 'רחוב' },
    { key: 'houseNum', label: 'מס\' בית' },
    { key: 'block', label: 'גוש' },
    { key: 'parcel', label: 'חלקה' },
    { key: 'plot', label: 'מגרש לפי תכנית' },
    { key: 'requestNum', label: 'מס\' בקשה להיתר' },
    { key: 'permitNum', label: 'מס\' היתר' },
    { key: 'fileNum', label: 'מס\' תיק בניין' },
    { key: 'controlInstitute', label: 'שם מכון הבקרה' },
    { key: 'guaranteeNum', label: 'מס\' ערבות בנקאית' },
    { key: 'guaranteeAmount', label: 'סכום הערבות (בלי ₪)' }
];

const DATE_FIELDS = [
    { key: 'date', label: 'תאריך חתימה', today: true },
    { key: 'startDate', label: 'מועד צפוי לתחילת העבודה' },
    { key: 'markingDate', label: 'תאריך סימון מתווה הבניין' },
    { key: 'visitDate', label: 'תאריך הביקורת באתר' },
    { key: 'foundationsDate', label: 'תאריך בדיקת היסודות' },
    { key: 'measureDate', label: 'תאריך הבדיקה והמדידה' },
    { key: 'permitDate', label: 'תאריך מתן ההיתר' },
    { key: 'guaranteeDate', label: 'תאריך הערבות' }
];

const PEOPLE = [
    { role: 'owner', title: 'בעל ההיתר / המבקש' },
    { role: 'supervisor', title: 'אחראי לביקורת על הביצוע' },
    { role: 'subSupervisor', title: 'אחראי משנה לביקורת על הביצוע' },
    { role: 'skeleton', title: 'אחראי לביצוע שלד הבניין' },
    { role: 'contractor', title: 'קבלן רשום' },
    { role: 'coordinator', title: 'אחראי לתיאום עם מכון הבקרה' },
    { role: 'surveyor', title: 'מודד מוסמך' },
    { role: 'architect', title: 'עורך בקשה ראשי' },
    { role: 'structural', title: 'עורך משנה הנדסת מבנים' },
    { role: 'subEditor', title: 'עורך משנה' },
    { role: 'accessibility', title: 'מורשה נגישות' },
    { role: 'worker', title: 'עובד שערך ביקורים לפיקוח עליון' }
];

const PERSON_FIELDS = [
    { field: 'name', label: 'שם מלא' },
    { field: 'id', label: 'ת.ז. / ח.פ.' },
    { field: 'license', label: 'מ.ר. / מס\' רישיון' },
    { field: 'licenseExpiry', label: 'תוקף רישיון קבלן', date: true },
    { field: 'phone', label: 'טלפון' },
    { field: 'email', label: 'מייל' },
    { field: 'address', label: 'כתובת' }
];

// תיבות הסימון "☐ אדם פרטי ☐ תאגיד ☐ גוף..." בפרטי בעל ההיתר
const OWNER_TYPES = [
    { value: 'private', label: 'אדם פרטי' },
    { value: 'corp', label: 'תאגיד' },
    { value: 'body261', label: 'גוף כהגדרתו בסעיף 261 ד\' לחוק התכנון והבנייה או רשות מקומית' }
];

// תמונות החתימה שהועלו, לפי תפקיד: { data: 'data:image/png;base64,...', width, height }
const signatures = {};

// שדות שמחושבים מתוך שדות אחרים
const COMPUTED = {
    siteAddressBlockParcel: ['street', 'houseNum', 'city', 'block', 'parcel']
};

// ---------- בניית הדף ----------

// טפסים רשמיים מזוהים במספר (ג-1, ה-4...). לשאר הטפסים מציגים רק את השם.
const hasFormNumber = form => /^[א-ת]-\d+$/.test(form.id);

function buildStages() {
    const container = document.getElementById('stages');
    for (const [stage, title] of Object.entries(STAGES)) {
        if (!FORMS.some(f => f.stage === stage)) continue; // שלב בלי טפסים באתר הזה
        const box = document.createElement('div');
        box.className = 'stage';
        box.innerHTML = `<div class="stage-title"><span>${title}</span><button type="button">בחר הכל</button></div>`;
        box.querySelector('button').onclick = () => {
            const boxes = box.querySelectorAll('input');
            const allChecked = [...boxes].every(b => b.checked);
            boxes.forEach(b => { b.checked = !allChecked; });
            updateVisibleFields(); // מעדכן גם את הטקסט של הכפתור
        };
        for (const form of FORMS.filter(f => f.stage === stage)) {
            const option = document.createElement('label');
            option.className = 'form-option';
            const note = form.keys.length ? '' : ' <span class="hint">(טופס סרוק, יורד ריק)</span>';
            const label = hasFormNumber(form) ? `<span class="form-id">${form.id}</span> ${form.title}` : form.title;
            option.innerHTML = `<input type="checkbox" value="${form.id}"><span>${label}${note}</span>`;
            option.querySelector('input').onchange = updateVisibleFields;
            box.appendChild(option);
        }
        container.appendChild(box);
    }
}

function fieldHtml(key, label, type = 'text', value = '') {
    return `<div class="form-group" data-key="${key}"><label>${label}</label><input type="${type}" id="${key}" value="${value}"></div>`;
}

// קובץ שנגרר ונפל מחוץ למסגרת חתימה לא יפתח את התמונה במקום האתר
window.addEventListener('dragover', e => e.preventDefault());
window.addEventListener('drop', e => e.preventDefault());

function buildFields() {
    const container = document.getElementById('fields');
    let html = `<div class="section"><h3>פרטי הבקשה והמקרקעין</h3><div class="grid">`;
    html += PROJECT_FIELDS.map(f => fieldHtml(f.key, f.label, 'text', f.value || '')).join('');
    html += `</div></div><div class="section"><h3>תאריכים</h3><div class="grid">`;
    const today = new Date().toISOString().slice(0, 10);
    html += DATE_FIELDS.map(f => fieldHtml(f.key, f.label, 'date', f.today ? today : '')).join('');
    html += `</div></div>`;
    for (const p of PEOPLE) {
        html += `<div class="section person" data-role="${p.role}"><h3>${p.title}</h3>
            <div class="person-tools">
                <select><option value="">בחירה מאנשי צוות שמורים...</option></select>
                <button type="button" class="small-btn save">שמירת הפרטים לפעם הבאה</button>
                <button type="button" class="small-btn delete">מחיקה מהשמורים</button>
            </div><div class="grid">`;
        if (p.role === 'owner') {
            html += `<div class="form-group" data-key="ownerType"><label>סוג בעל ההיתר</label><select id="ownerType">
                <option value="">לא לסמן</option>${OWNER_TYPES.map(t => `<option value="${t.value}">${t.label}</option>`).join('')}</select></div>`;
        }
        html += PERSON_FIELDS.map(f => fieldHtml(`${p.role}.${f.field}`, f.label, f.date ? 'date' : 'text')).join('');
        // שדה החתימה מוצג רק אם נבחר טופס שהאדם הזה חותם עליו
        html += `<div class="form-group" data-key="${p.role}.signature"><label>תמונת חתימה</label>
            <div class="signature-box"><img class="hidden" alt="חתימה"><span class="hint">אפשר לגרור לכאן תמונה של החתימה</span></div>
            <div class="signature-actions"><input type="file" accept="image/*">
            <button type="button" class="small-btn remove-signature">הסרה</button></div></div>`;
        html += `</div></div>`;
    }
    container.innerHTML = html;

    document.querySelectorAll('.person').forEach(section => {
        const role = section.dataset.role;
        section.querySelector('.person-tools select').onchange = e => {
            const person = loadPeople()[e.target.value];
            if (!person) return;
            PERSON_FIELDS.forEach(f => { document.getElementById(`${role}.${f.field}`).value = person[f.field] || ''; });
            setSignature(role, person.signature || null);
        };
        const loadSignatureFile = async file => {
            if (!file) return;
            if (!file.type.startsWith('image/')) return alert('יש לבחור קובץ תמונה (למשל JPG או PNG).');
            try {
                setSignature(role, await processSignature(file));
            } catch (e) {
                console.error(e);
                alert('לא הצלחנו לקרוא את התמונה. כדאי לנסות תמונה ברורה של החתימה על רקע לבן.');
            }
        };
        const fileInput = section.querySelector('input[type="file"]');
        fileInput.onchange = async () => {
            await loadSignatureFile(fileInput.files[0]);
            fileInput.value = '';
        };
        // גרירת קובץ חתימה מהמחשב אל המסגרת
        const dropBox = section.querySelector('.signature-box');
        dropBox.ondragover = e => {
            e.preventDefault();
            dropBox.classList.add('dragover');
        };
        dropBox.ondragleave = () => dropBox.classList.remove('dragover');
        dropBox.ondrop = e => {
            e.preventDefault();
            dropBox.classList.remove('dragover');
            loadSignatureFile(e.dataTransfer.files[0]);
        };
        section.querySelector('.remove-signature').onclick = () => setSignature(role, null);
        section.querySelector('.save').onclick = () => savePerson(role);
        section.querySelector('.delete').onclick = () => deletePerson(section.querySelector('.person-tools select').value);
    });
    refreshPeopleLists();
}

// מציג רק שדות שמופיעים בטפסים שנבחרו
function updateVisibleFields() {
    const selected = selectedForms();
    const used = new Set();
    for (const form of selected) {
        for (const key of form.keys) {
            used.add(key);
            (COMPUTED[key] || []).forEach(k => used.add(k));
            if (key === 'signerName') used.add(`${form.signer}.name`);
            if (key === 'signerId') used.add(`${form.signer}.id`);
            if (key === 'signature') used.add(`${form.signer}.signature`);
            if (key.includes('=')) used.add(key.split('=')[0]);
        }
    }
    document.querySelectorAll('[data-key]').forEach(el => el.classList.toggle('hidden', !used.has(el.dataset.key)));
    document.querySelectorAll('.section').forEach(section => {
        section.classList.toggle('hidden', !section.querySelector('[data-key]:not(.hidden)'));
    });
    document.getElementById('noFormsHint').classList.toggle('hidden', selected.length > 0);
    updateStageButtons();
}

// "בחר הכל" הופך ל"הסר הכל" כשכל הטפסים בשלב מסומנים
function updateStageButtons() {
    document.querySelectorAll('.stage').forEach(stage => {
        const allChecked = [...stage.querySelectorAll('input')].every(b => b.checked);
        stage.querySelector('.stage-title button').innerText = allChecked ? 'הסר הכל' : 'בחר הכל';
    });
}

// ---------- חתימות ----------

function setSignature(role, signature) {
    signatures[role] = signature;
    const box = document.querySelector(`[data-key="${role}.signature"] .signature-box`);
    box.querySelector('img').src = signature ? signature.data : '';
    box.querySelector('img').classList.toggle('hidden', !signature);
    box.querySelector('.hint').classList.toggle('hidden', !!signature);
}

// מנקה את הרקע של תמונת החתימה (הופך אותו לשקוף) וחותך את השוליים
async function processSignature(file) {
    const img = await new Promise((resolve, reject) => {
        const i = new Image();
        i.onload = () => resolve(i);
        i.onerror = reject;
        i.src = URL.createObjectURL(file);
    });
    const scale = Math.min(1, 1000 / img.width);
    const canvas = document.createElement('canvas');
    canvas.width = Math.round(img.width * scale);
    canvas.height = Math.round(img.height * scale);
    const ctx = canvas.getContext('2d');
    ctx.drawImage(img, 0, 0, canvas.width, canvas.height);
    URL.revokeObjectURL(img.src);

    const image = ctx.getImageData(0, 0, canvas.width, canvas.height);
    const px = image.data;
    const brightness = i => (px[i] + px[i + 1] + px[i + 2]) / 3;
    // צבע הרקע = הבהירות החציונית (רוב התמונה היא נייר)
    const samples = [];
    for (let i = 0; i < px.length; i += 4 * 37) if (px[i + 3] > 0) samples.push(brightness(i));
    samples.sort((a, b) => a - b);
    const background = samples[Math.floor(samples.length / 2)] || 255;
    const threshold = background - Math.max(40, background * 0.25);

    let minX = canvas.width, minY = canvas.height, maxX = -1, maxY = -1;
    for (let y = 0; y < canvas.height; y++) {
        for (let x = 0; x < canvas.width; x++) {
            const i = (y * canvas.width + x) * 4;
            if (px[i + 3] < 20 || brightness(i) > threshold) {
                px[i + 3] = 0;
            } else {
                minX = Math.min(minX, x); maxX = Math.max(maxX, x);
                minY = Math.min(minY, y); maxY = Math.max(maxY, y);
            }
        }
    }
    if (maxX < 0) throw new Error('no signature found in image');
    ctx.putImageData(image, 0, 0);

    const pad = 4;
    const x0 = Math.max(0, minX - pad), y0 = Math.max(0, minY - pad);
    const width = Math.min(canvas.width, maxX + pad + 1) - x0;
    const height = Math.min(canvas.height, maxY + pad + 1) - y0;
    const out = document.createElement('canvas');
    out.width = width;
    out.height = height;
    out.getContext('2d').drawImage(canvas, x0, y0, width, height, 0, 0, width, height);
    return { data: out.toDataURL('image/png'), width, height };
}

function selectedForms() {
    const ids = [...document.querySelectorAll('#stages input:checked')].map(b => b.value);
    return FORMS.filter(f => ids.includes(f.id));
}

// ---------- אנשי צוות שמורים (נשמרים בדפדפן הזה בלבד) ----------

// משותף לכל אתרי הוועדות, כך שאיש צוות שנשמר באתר אחד זמין גם באחרים
const PEOPLE_STORAGE = 'planningForms.people';

// מעבר חד-פעמי מהשם הישן (כשהיה רק אתר עומר)
try {
    const old = localStorage.getItem('omerForms.people');
    if (old && !localStorage.getItem(PEOPLE_STORAGE)) localStorage.setItem(PEOPLE_STORAGE, old);
} catch (e) { }

function loadPeople() {
    try {
        return JSON.parse(localStorage.getItem(PEOPLE_STORAGE)) || {};
    } catch (e) {
        return {};
    }
}

function storePeople(people) {
    try {
        localStorage.setItem(PEOPLE_STORAGE, JSON.stringify(people));
    } catch (e) {
        alert('לא ניתן לשמור בדפדפן הזה.');
    }
    refreshPeopleLists();
}

function savePerson(role) {
    const person = {};
    PERSON_FIELDS.forEach(f => { person[f.field] = document.getElementById(`${role}.${f.field}`).value.trim(); });
    if (signatures[role]) person.signature = signatures[role];
    if (!person.name) return alert('יש למלא שם לפני השמירה.');
    const people = loadPeople();
    // שמירה מתפקיד בלי העלאת חתימה לא מוחקת חתימה ששמורה כבר לאותו אדם
    if (!person.signature && people[person.name]?.signature) person.signature = people[person.name].signature;
    people[person.name] = person;
    storePeople(people);
    alert(`${person.name} נשמר/ה. מעכשיו אפשר לבחור מהרשימה בכל אחד מבעלי התפקידים.`);
}

function deletePerson(name) {
    if (!name) return alert('יש לבחור קודם מהרשימה את מי למחוק.');
    if (!confirm(`למחוק את ${name} מהשמורים?`)) return;
    const people = loadPeople();
    delete people[name];
    storePeople(people);
}

function refreshPeopleLists() {
    const names = Object.keys(loadPeople()).sort((a, b) => a.localeCompare(b, 'he'));
    document.querySelectorAll('.person-tools select').forEach(select => {
        select.length = 1;
        names.forEach(name => select.add(new Option(name, name)));
    });
}

// ---------- מילוי התבניות ----------

function formatDate(iso) {
    const [y, m, d] = iso.split('-');
    return `${d}/${m}/${y}`;
}

function collectValues() {
    const values = {};
    document.querySelectorAll('#fields input[id], #fields select[id]').forEach(input => {
        const v = input.value.trim();
        values[input.id] = input.type === 'date' && v ? formatDate(v) : v;
    });
    const address = [[values.street, values.houseNum].filter(Boolean).join(' '), values.city].filter(Boolean).join(', ');
    const blockParcel = [values.block && `גוש ${values.block}`, values.parcel && `חלקה ${values.parcel}`].filter(Boolean).join(' ');
    values.siteAddressBlockParcel = [address, blockParcel].filter(Boolean).join(', ');
    return values;
}

const escapeXml = s => s.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');

// כל שדה בתבנית הוא ריצת טקסט אחת: {{key|הטקסט המקורי}}.
// אם יש ערך - הוא נכתב בשחור. אם אין - חוזר הטקסט המקורי (<השלם מידע> או קו ריק).
const TAG_RUN = /<w:r><w:rPr>((?:(?!<\/w:rPr>).)*)<\/w:rPr><w:t xml:space="preserve">\{\{([^|}]+)\|([^}]*)\}\}<\/w:t><\/w:r>/gs;

const SIGNATURE_REL = 'rIdSignature';

// תמונה בתוך השורה, בגובה 1.2 ס"מ (ולכל היותר 4.5 ס"מ רוחב)
function signatureRun(signature) {
    const EMU_PER_CM = 360000;
    let cy = 1.2 * EMU_PER_CM;
    let cx = cy * signature.width / signature.height;
    if (cx > 4.5 * EMU_PER_CM) {
        cy *= 4.5 * EMU_PER_CM / cx;
        cx = 4.5 * EMU_PER_CM;
    }
    cx = Math.round(cx);
    cy = Math.round(cy);
    return `<w:r><w:drawing><wp:inline distT="0" distB="0" distL="0" distR="0" xmlns:wp="http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing">`
        + `<wp:extent cx="${cx}" cy="${cy}"/><wp:docPr id="5001" name="חתימה"/>`
        + `<a:graphic xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main"><a:graphicData uri="http://schemas.openxmlformats.org/drawingml/2006/picture">`
        + `<pic:pic xmlns:pic="http://schemas.openxmlformats.org/drawingml/2006/picture"><pic:nvPicPr><pic:cNvPr id="5001" name="signature.png"/><pic:cNvPicPr/></pic:nvPicPr>`
        + `<pic:blipFill><a:blip r:embed="${SIGNATURE_REL}" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"/><a:stretch><a:fillRect/></a:stretch></pic:blipFill>`
        + `<pic:spPr><a:xfrm><a:off x="0" y="0"/><a:ext cx="${cx}" cy="${cy}"/></a:xfrm><a:prstGeom prst="rect"><a:avLst/></a:prstGeom></pic:spPr>`
        + `</pic:pic></a:graphicData></a:graphic></wp:inline></w:drawing></w:r>`;
}

function fillXml(xml, values) {
    return xml.replace(TAG_RUN, (match, rPr, key, original) => {
        if (key === 'signature' && values.signature) {
            values.signatureUsed = true;
            return signatureRun(values.signature);
        }
        if (key.includes('=')) { // תיבת סימון, למשל ownerType=private
            const [field, option] = key.split('=');
            return `<w:r><w:rPr>${rPr}</w:rPr><w:t xml:space="preserve">${values[field] === option ? '☒' : '☐'}</w:t></w:r>`;
        }
        const value = values[key];
        if (value) {
            return `<w:r><w:rPr>${rPr.replace(/<w:color [^>]*\/>/g, '')}</w:rPr><w:t xml:space="preserve">${escapeXml(value)}</w:t></w:r>`;
        }
        const text = /^[_.]*$/.test(original) ? original : `<${original}>`;
        return `<w:r><w:rPr>${rPr}</w:rPr><w:t xml:space="preserve">${escapeXml(text)}</w:t></w:r>`;
    });
}

async function fillForm(form, values) {
    // signerName / signerId = פרטי מי שחותם על הטופס הזה
    const formValues = {
        ...values,
        signerName: values[`${form.signer}.name`] || '',
        signerId: values[`${form.signer}.id`] || '',
        signature: signatures[form.signer] || null
    };
    if (form.type === 'pdf') return fillPdfForm(form, formValues);
    const response = await fetch(`templates/${form.id}.docx`);
    if (!response.ok) throw new Error(`לא הצלחנו לטעון את ${form.id}`);
    const zip = await JSZip.loadAsync(await response.arrayBuffer());
    for (const name of Object.keys(zip.files)) {
        if (/^word\/(document|header\d*|footer\d*)\.xml$/.test(name)) {
            zip.file(name, fillXml(await zip.file(name).async('string'), formValues));
        }
    }
    if (formValues.signatureUsed) await addSignatureImage(zip, formValues.signature);
    return zip.generateAsync({ type: 'blob', mimeType: 'application/vnd.openxmlformats-officedocument.wordprocessingml.document' });
}

// ---------- טפסי PDF (שדות דן) ----------
// בטופס PDF כותבים את הטקסט מעל הקווים הריקים, לפי המיקום שנשמר ב-forms.js.

let pdfFontBytes = null;

async function fillPdfForm(form, values) {
    const { PDFDocument, rgb } = PDFLib;
    const response = await fetch(`templates/${form.id}.pdf`);
    if (!response.ok) throw new Error(`לא הצלחנו לטעון את ${form.id}`);
    const doc = await PDFDocument.load(await response.arrayBuffer());
    doc.registerFontkit(fontkit);
    if (!pdfFontBytes) pdfFontBytes = await (await fetch('../shared/font.ttf')).arrayBuffer();
    const font = await doc.embedFont(pdfFontBytes, { subset: true });
    const pages = doc.getPages();
    const signatureImages = {};

    for (const field of form.fields) {
        const page = pages[field.page];
        const baseline = page.getHeight() - (field.top + field.size * 0.8) + 1.5; // קצת מעל הקו
        const right = field.x1 - 2;
        const room = field.x1 - field.x0 - 4;

        if (field.key === 'signature' || field.key.endsWith('.signature')) {
            // "signature" = מי שחותם על הטופס; "owner.signature" וכו' = בחוברת שבה כל מסמך נחתם ע"י מישהו אחר
            const signature = field.key === 'signature' ? values.signature : signatures[field.key.split('.')[0]];
            if (!signature) continue;
            signatureImages[field.key] = signatureImages[field.key] || await doc.embedPng(signature.data);
            let height = 26;
            let width = height * signature.width / signature.height;
            if (width > room) {
                width = room;
                height = width * signature.height / signature.width;
            }
            page.drawImage(signatureImages[field.key], { x: right - width, y: baseline - 3, width, height });
            continue;
        }

        const text = values[field.key];
        if (!text) continue;
        let size = 10; // מקטינים את הגופן אם הטקסט ארוך מהקו
        while (size > 6 && font.widthOfTextAtSize(text, size) > room) size -= 0.5;
        const width = font.widthOfTextAtSize(text, size);
        drawVisualText(page, text, right - width, baseline, size, font, rgb(0, 0, 0)); // מיושר לימין הקו
    }
    return new Blob([await doc.save()], { type: 'application/pdf' });
}

// סידור טקסט מעורב (עברית / מספרים / אנגלית) לציור ב-PDF - כמו באתר טפסי רמ"י
const HEBREW = /[\u0590-\u05FF]/;

function toVisual(str) {
    if (!HEBREW.test(str)) return str;
    const bidi = bidi_js();
    const levels = bidi.getEmbeddingLevels(str, 'rtl');
    const chars = str.split('');
    bidi.getMirroredCharactersMap(str, levels.levels).forEach((ch, i) => { chars[i] = ch; });
    bidi.getReorderSegments(str, levels).forEach(([start, end]) => {
        chars.splice(start, end - start + 1, ...chars.slice(start, end + 1).reverse());
    });
    return chars.join('');
}

// fontkit הופך מחרוזת שמתחילה בעברית, לכן מציירים בחלקים: חלק עברי נשלח הפוך וחלק בלי עברית כמו שהוא
function drawVisualText(page, text, x, y, size, font, color) {
    const visual = toVisual(text);
    const chunks = visual.match(/[\u0590-\u05FF](?:[^A-Za-z\u00C0-\u024F]*[\u0590-\u05FF])?|[^\u0590-\u05FF]+/g) || [];
    for (const chunk of chunks) {
        const toDraw = HEBREW.test(chunk) ? [...chunk].reverse().join('') : chunk;
        page.drawText(toDraw, { x, y, size, font, color });
        x += font.widthOfTextAtSize(chunk, size);
    }
}

// מוסיף את קובץ התמונה לקובץ ה-Word ומקשר אותו (rIdSignature)
async function addSignatureImage(zip, signature) {
    zip.file('word/media/signature.png', signature.data.split(',')[1], { base64: true });
    const relsPath = 'word/_rels/document.xml.rels';
    const rels = await zip.file(relsPath).async('string');
    zip.file(relsPath, rels.replace('</Relationships>',
        `<Relationship Id="${SIGNATURE_REL}" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/image" Target="media/signature.png"/></Relationships>`));
    const types = await zip.file('[Content_Types].xml').async('string');
    if (!/Extension="png"/i.test(types)) {
        zip.file('[Content_Types].xml', types.replace(/(<Types[^>]*>)/, '$1<Default Extension="png" ContentType="image/png"/>'));
    }
}

function fileName(form) {
    const name = hasFormNumber(form) ? `${form.id} - ${form.title}` : form.title;
    return name.replace(/["/\\:*?<>|]/g, '') + (form.type === 'pdf' ? '.pdf' : '.docx');
}

function download(blob, name) {
    const link = document.createElement('a');
    link.href = URL.createObjectURL(blob);
    link.download = name;
    link.click();
    setTimeout(() => URL.revokeObjectURL(link.href), 10000);
}

async function generate() {
    const forms = selectedForms();
    if (!forms.length) return alert('יש לבחור לפחות טופס אחד.');
    const btn = document.getElementById('generateBtn');
    btn.disabled = true;
    btn.innerText = 'מכין טפסים... נא להמתין';
    const values = collectValues();
    const failed = [];
    const zip = document.getElementById('asZip').checked ? new JSZip() : null;
    try {
        for (const form of forms) {
            try {
                const blob = await fillForm(form, values);
                if (zip) {
                    zip.file(fileName(form), blob);
                } else {
                    download(blob, fileName(form));
                    await new Promise(r => setTimeout(r, 300)); // דפדפנים חוסמים לפעמים הורדות צמודות מדי
                }
            } catch (e) {
                console.error(e);
                failed.push(form.id);
            }
        }
        if (zip) download(await zip.generateAsync({ type: 'blob' }), 'טפסים ממולאים.zip');
        if (failed.length) alert(`לא הצלחנו להכין את הטפסים: ${failed.join(', ')}`);
    } finally {
        btn.disabled = false;
        btn.innerText = 'מלא והורד את הטפסים שנבחרו';
    }
}

buildStages();
buildFields();
updateVisibleFields();
