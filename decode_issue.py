from pathlib import Path
p = Path('c:/Users/hp/Downloads/welloyewa_new-main/welloyewa_new-main/pytest_output.txt')
raw = p.read_bytes()
for enc in ('utf-16', 'utf-8', 'utf-8-sig', 'cp1252'):
    try:
        text = raw.decode(enc)
        print('ENC', enc)
        print(text[:4000])
        print('---END---')
    except Exception as e:
        print('ERR', enc, repr(e))
