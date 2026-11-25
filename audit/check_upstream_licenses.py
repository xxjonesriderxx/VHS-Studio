"""Read official project license files; this records evidence, not a legal verdict."""
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
from urllib.parse import urlparse
from urllib.request import Request, urlopen

HERE = Path(__file__).resolve().parent


def fetch(row):
    url = row.get('official_project', '')
    if row['name'].lower() == 'customtkinter':
        url = 'https://github.com/TomSchimansky/CustomTkinter'
    result = dict(name=row['name'], version=row['version'], official_project=url)
    parsed = urlparse(url)
    if parsed.hostname not in ('github.com', 'www.github.com'):
        return result | dict(status='other_official_host', explanation='Use the linked official host and original package license.')
    parts = parsed.path.strip('/').split('/')
    if len(parts) < 2:
        return result | dict(status='invalid_repository_url')
    repo = '/'.join(parts[:2]).removesuffix('.git')
    branch = parts[3] if len(parts) > 3 and parts[2] == 'tree' else 'HEAD'
    subtree = '/'.join(parts[4:]) + '/' if len(parts) > 4 and parts[2] == 'tree' else ''
    paths = [x['file'].removeprefix('licenses/') for x in row.get('notices', [])]
    paths += ['LICENSE', 'LICENSE.txt', 'LICENSE.md', 'COPYING', 'COPYING.txt', 'LICENSE.rst', 'LICENSE-MIT', 'LICENSES/Apache-2.0.txt']
    failures = []
    for path in dict.fromkeys(paths):
        if '..' in path or path.startswith('/'):
            continue
        source = f'https://raw.githubusercontent.com/{repo}/{branch}/{subtree}{path}'
        try:
            with urlopen(Request(source, headers={'User-Agent': 'VHS-Studio-license-audit'}), timeout=7) as response:
                body = response.read(300001)
            if len(body) > 300000:
                raise ValueError('License response exceeded limit')
            content = body.decode('utf8', errors='replace')
            checksum = hashlib.sha256(body).hexdigest()
            matched = any(n['sha256'] == checksum for n in row.get('notices', []))
            markers = [label for pattern,label in [
                (r'Permission is hereby granted, free of charge', 'MIT-style grant'),
                (r'Apache License', 'Apache license text'),
                (r'Redistribution and use in source and binary forms', 'BSD-style grant'),
                (r'GNU GENERAL PUBLIC LICENSE', 'GPL text'),
                (r'GNU LESSER GENERAL PUBLIC LICENSE', 'LGPL text'),
                (r'Mozilla Public License', 'MPL text'),
            ] if re.search(pattern, content, re.I)]
            return result | dict(status='fetched', source=source, sha256=checksum,
                byte_identical_to_packaged_notice=matched, text_markers=markers,
                first_nonempty_line=next((line.strip()[:180] for line in content.splitlines() if line.strip()), ''),
                scope='Current official default branch; the versioned original package remains the release-specific license evidence.')
        except Exception as error:
            failures.append(dict(source=source, error=type(error).__name__))
    return result | dict(status='not_fetched', attempts=failures)


if __name__ == '__main__':
    rows=json.loads((HERE/'artifact-inventory-b.json').read_text('utf8'))['python_distributions']
    results=[]
    with ThreadPoolExecutor(max_workers=12) as pool:
        futures=[pool.submit(fetch,row) for row in rows]
        for future in as_completed(futures):
            result=future.result()
            results.append(result)
            print(result['name'],result['status'],flush=True)
    record=dict(checked_at_utc=datetime.now(timezone.utc).isoformat(),
        method='Actual HTTPS fetch of official repository license files, with optional exact hash match to the version-specific original notice. Current HEAD is not substituted for the release license.',
        packages=sorted(results,key=lambda x:x['name'].lower()))
    (HERE/'upstream-license-check.json').write_text(json.dumps(record,ensure_ascii=False,indent=2),encoding='utf8')
    print('Completed',len(results),'packages;',sum(x['status']=='fetched' for x in results),'official GitHub license files fetched.',flush=True)
