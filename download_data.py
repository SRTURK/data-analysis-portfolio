"""Download only the two published datasets; preserve source URLs and SHA256."""
from pathlib import Path
from urllib.request import Request, urlopen
from datetime import datetime, timezone
import hashlib
import json
import zipfile

ROOT = Path(__file__).resolve().parent

def fetch(url, target):
    target.parent.mkdir(parents=True, exist_ok=True)
    if not target.exists():
        request = Request(url, headers={'User-Agent': 'Mozilla/5.0 (public-data-research)'})
        with urlopen(request, timeout=180) as response:
            blob = response.read()
        target.write_bytes(blob)
    return {'url': url, 'file': target.relative_to(ROOT).as_posix(),
            'bytes': target.stat().st_size,
            'sha256': hashlib.sha256(target.read_bytes()).hexdigest()}

def main():
    records = []
    archive = ROOT/'01-olist-operations/data/raw/olist.zip'
    records.append(fetch('https://www.kaggle.com/api/v1/datasets/download/olistbr/brazilian-ecommerce', archive))
    with zipfile.ZipFile(archive) as z:
        for member in z.namelist():
            name = Path(member).name
            if name.endswith('.csv'):
                dest = archive.parent/name
                dest.write_bytes(z.read(member))
                records.append({'file': dest.relative_to(ROOT).as_posix(), 'bytes': dest.stat().st_size,
                                'sha256': hashlib.sha256(dest.read_bytes()).hexdigest()})
    records.append(fetch('http://www.minethatdata.com/Kevin_Hillstrom_MineThatData_E-MailAnalytics_DataMiningChallenge_2008.03.20.csv',
                         ROOT/'02-marketing-experiment/data/raw/hillstrom.csv'))
    manifest = ROOT/'data_manifest.json'
    manifest.write_text(json.dumps({'retrieved_at_utc': datetime.now(timezone.utc).isoformat(),
                                   'files': records}, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps(records, indent=2))

if __name__ == '__main__':
    main()
