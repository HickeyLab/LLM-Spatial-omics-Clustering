#!/usr/bin/env python3
"""Package verified current manuscript figure files without image processing."""
from pathlib import Path
from zipfile import ZipFile, ZIP_DEFLATED, ZipInfo
import argparse
import hashlib
import json
ROOT=Path(__file__).resolve().parents[1]
def package(output):
    source=ROOT/'figures/current_manuscript'
    manifest=json.loads((source/'Figure_manifest.json').read_text())
    for item in manifest['files']:
        if hashlib.sha256((source/item['filename']).read_bytes()).hexdigest()!=item['sha256']:
            raise ValueError('Current image checksum differs')
    if output.exists():raise FileExistsError('Choose a new output path')
    output.parent.mkdir(parents=True,exist_ok=True)
    with ZipFile(output,'x',ZIP_DEFLATED) as archive:
        for path in sorted(p for p in source.rglob('*') if p.is_file()):
            info=ZipInfo(str(path.relative_to(source)),date_time=(2026,11,15,0,0,0))
            info.compress_type=ZIP_DEFLATED
            archive.writestr(info,path.read_bytes())
    return {'files':len(archive.namelist()),'pngs':len(manifest['files']),'sha256':hashlib.sha256(output.read_bytes()).hexdigest()}
if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--output',type=Path,required=True)
    print(json.dumps(package(parser.parse_args().output),indent=2))
