import re
import os

# 1. Check all url_for('static', filename=...) references exist
missing = []
for root, dirs, fnames in os.walk('templates'):
    for f in fnames:
        if not f.endswith('.html'):
            continue
        p = os.path.join(root, f)
        html = open(p, encoding='utf-8').read()
        for m in re.findall(r"url_for\('static',\s*filename='([^']+)'\)", html):
            if not os.path.exists(os.path.join('static', m)):
                missing.append((p, m))
print('MISSING STATIC FILES:', missing if missing else 'none')

# 2. Collect all function definitions from JS files and templates
funcs = set()
for jsf in os.listdir(os.path.join('static', 'js')):
    js = open(os.path.join('static', 'js', jsf), encoding='utf-8').read()
    funcs |= set(re.findall(r'function\s+([A-Za-z_$][\w$]*)', js))
    funcs |= set(re.findall(r'(?:const|let|var)\s+([A-Za-z_$][\w$]*)\s*=', js))
for root, dirs, fnames in os.walk('templates'):
    for f in fnames:
        if not f.endswith('.html'):
            continue
        p = os.path.join(root, f)
        html = open(p, encoding='utf-8').read()
        funcs |= set(re.findall(r'function\s+([A-Za-z_$][\w$]*)', html))

# 3. Check onclick/onsubmit handlers in host templates call defined functions
undef = []
builtin = {'confirm', 'alert', 'parseInt', 'setTimeout', 'location', 'event', 'parseFloat', 'isNaN'}
for root, dirs, fnames in os.walk(os.path.join('templates', 'host')):
    for f in fnames:
        if not f.endswith('.html'):
            continue
        p = os.path.join(root, f)
        html = open(p, encoding='utf-8').read()
        for h in re.findall(r'on(?:click|submit|keyup)=["\']([^"\']+)', html):
            for fn in re.findall(r'([A-Za-z_$][\w$]*)\s*\(', h):
                if fn not in funcs and fn not in builtin:
                    undef.append((p, fn))
print('UNDEFINED HANDLERS:', undef if undef else 'none')

# 4. Check JS element IDs referenced in host.js exist on host pages
host_js = open(os.path.join('static', 'js', 'host.js'), encoding='utf-8').read()
ids = set(re.findall(r"getElementById\('([^']+)'", host_js))
page_ids = {}
for root, dirs, fnames in os.walk(os.path.join('templates', 'host')):
    for f in fnames:
        if not f.endswith('.html'):
            continue
        p = os.path.join(root, f)
        page_ids[p] = set(re.findall(r'id="([^"]+)"', open(p, encoding='utf-8').read()))
print('JS-REFERENCED IDS NOT FOUND ON ANY HOST PAGE:',
      sorted(i for i in ids if not any(i in s for s in page_ids.values())) or 'none')

# 5. Check getElementById calls in host inline scripts against their own page ids
for root, dirs, fnames in os.walk(os.path.join('templates', 'host')):
    for f in fnames:
        if not f.endswith('.html'):
            continue
        p = os.path.join(root, f)
        html = open(p, encoding='utf-8').read()
        page_id_set = set(re.findall(r'id="([^"]+)"', html))
        # ids built dynamically with template parts, e.g. 'teamScore_' + t.id -> prefix check
        inline_ids = re.findall(r"getElementById\(\s*['\"]([\w-]+)['\"]", html)
        miss = [i for i in inline_ids if i not in page_id_set and not any(x.startswith(i) for x in page_id_set)]
        if miss:
            print(f'  {p}: missing ids for getElementById ->', miss)
print('INLINE ID CHECK DONE')
