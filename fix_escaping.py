import re
for f_name in ['pb_public/dashboard.html', 'pb_public/guru.html']:
    with open(f_name, 'r', encoding='utf-8') as f:
        d = f.read()
    d = d.replace('\\`', '`').replace('\\${', '${')
    with open(f_name, 'w', encoding='utf-8') as f:
        f.write(d)
print("Done")
