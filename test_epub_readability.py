"""Generate synthetic EPUB fixtures and audit EPUB Health Checker classifications.
Run at project root: python test_epub_readability.py
No user EPUBs are modified. All fixtures are written to test_fixtures_readability/.
"""
from __future__ import annotations

import csv
from pathlib import Path
import zipfile

OUT = Path('test_fixtures_readability')
CONTAINER = b'''<?xml version="1.0" encoding="UTF-8"?>
<container xmlns="urn:oasis:names:tc:opendocument:xmlns:container" version="1.0">
<rootfiles><rootfile full-path="OEBPS/content.opf" media-type="application/oebps-package+xml"/></rootfiles>
</container>'''

def opf(chapters, spine=None, include_image=False):
    spine = chapters if spine is None else spine
    manifest = '\n'.join(f'<item id="{x}" href="{x}.xhtml" media-type="application/xhtml+xml"/>' for x in chapters)
    if include_image:
        manifest += '\n<item id="coverimage" href="images/missing.png" media-type="image/png"/>'
    return f'''<?xml version="1.0" encoding="UTF-8"?>
<package xmlns="http://www.idpf.org/2007/opf" version="3.0" unique-identifier="bookid">
<metadata xmlns:dc="http://purl.org/dc/elements/1.1/">
<dc:identifier id="bookid">urn:uuid:epub-health-fixture</dc:identifier>
<dc:title>EPUB Health Fixture</dc:title><dc:language>en</dc:language>
</metadata><manifest>{manifest}</manifest><spine>{''.join(f'<itemref idref="{x}"/>' for x in spine)}</spine></package>'''.encode()

def xhtml(body):
    return f'''<?xml version="1.0" encoding="UTF-8"?>
<html xmlns="http://www.w3.org/1999/xhtml"><head><title>Test</title></head><body>{body}</body></html>'''.encode()

def make_epub(name, chapters, spine=None, include_image=False):
    path = OUT / name
    with zipfile.ZipFile(path, 'w') as z:
        z.writestr('mimetype', b'application/epub+zip', compress_type=zipfile.ZIP_STORED)
        z.writestr('META-INF/container.xml', CONTAINER)
        z.writestr('OEBPS/content.opf', opf(chapters, spine, include_image))
        for key, value in chapters.items():
            if value is not None:
                z.writestr(f'OEBPS/{key}.xhtml', value)
    return path

# Expected statuses correspond to current design, not reader compatibility.
CASES = {
    '01_valid.epub': ('READABLE', 'valid XHTML'),
    '02_missing_chapter.epub': ('UNREADABLE', 'only spine document is absent'),
    '03_bad_xhtml.epub': ('UNREADABLE', 'only spine document has invalid XML'),
    '04_partial_bad_xhtml.epub': ('UNKNOWN', 'one of two chapters has invalid XML'),
    '05_missing_image.epub': ('READABLE', 'referenced image is absent (warning)'),
    '06_nbsp_entity.epub': ('UNREADABLE', 'XML parser rejects undeclared &nbsp; entity'),
    '07_no_spine.epub': ('UNREADABLE', 'spine is empty'),
    '08_invalid_zip.epub': ('UNREADABLE', 'not a ZIP archive'),
    '09_empty_body.epub': ('READABLE', 'blank body warning'),
}

def generate():
    OUT.mkdir(exist_ok=True)
    make_epub('01_valid.epub', {'c1': xhtml('<p>Readable text.</p>')})
    make_epub('02_missing_chapter.epub', {'c1': None})
    make_epub('03_bad_xhtml.epub', {'c1': xhtml('<p>Unclosed paragraph')})
    make_epub('04_partial_bad_xhtml.epub', {
        'c1': xhtml('<p>Readable text.</p>'), 'c2': xhtml('<p>Broken')})
    make_epub('05_missing_image.epub', {'c1': xhtml('<p>Text.</p><img src="images/missing.png" alt="missing"/>')}, include_image=True)
    make_epub('06_nbsp_entity.epub', {'c1': xhtml('<p>Word&nbsp;word</p>')})
    make_epub('07_no_spine.epub', {'c1': xhtml('<p>Text</p>')}, spine=[])
    (OUT / '08_invalid_zip.epub').write_bytes(b'Not a valid ZIP or EPUB file')
    make_epub('09_empty_body.epub', {'c1': xhtml('')})


def run():
    generate()
    try:
        from cli import build_registry
        from engine.runner import Runner
        from models import ScanJob
    except Exception as exc:
        print('Cannot import project modules:', repr(exc))
        print('Place this script in the EPUB_Health_Checker project root and activate its venv.')
        raise SystemExit(2)

    runner = Runner(build_registry())
    rows = []
    for filename, (expected, note) in CASES.items():
        path = (OUT / filename).resolve()
        job = ScanJob(path=path, size=path.stat().st_size, relative_path=filename)
        try:
            book = runner.run_file(job)
            actual = book.readability_status
            issues = ' | '.join(
                f'{r.checker}: {r.message}' for r in book.results
                if r.checker in ('Integrity', 'ReadableContent') and not r.success
            )
            outcome = 'MATCH' if actual == expected else 'MISMATCH'
            health = book.health_status
        except Exception as exc:
            actual, health, issues, outcome = 'EXCEPTION', '-', repr(exc), 'ERROR'
        rows.append({'file': filename, 'expected': expected, 'actual': actual,
                     'health': health, 'outcome': outcome, 'scenario': note, 'findings': issues})
        print(f'{outcome:9} {filename:29} expected={expected:10} actual={actual}')

    report = OUT / 'audit_results.csv'
    with report.open('w', encoding='utf-8-sig', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    print('\nReport:', report.resolve())
    print('Matches:', sum(r['outcome'] == 'MATCH' for r in rows), '/', len(rows))
    print('Note: &nbsp; is deliberately malformed XHTML XML; some readers may recover.')
    print('Do not interpret synthetic expectations as proof of real-world reader compatibility.')

if __name__ == '__main__':
    run()
