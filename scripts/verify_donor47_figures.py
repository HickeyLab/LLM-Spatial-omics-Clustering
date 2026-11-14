"""Read-only source/readiness admission for cross-donor figure receipts.

The existing publication verifier retains responsibility for typography,
panels, editable text and raster identity. No fit or model request is made.
"""
from __future__ import annotations
import hashlib
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
DATA=Path('data/frozen/donor47_results_20261114')
DONOR_PANELS={'5':'ABCD','S12':'ABC','S13':'ABCD'}
REQUIRED_SOURCES={
    '5':{'annotation_donor_metrics.csv','annotation_equal_donor_metrics.csv','baselines_donor_metrics.csv'},
    'S12':{'clustering_donor_metrics.csv','spatialsort_seed_sensitivity.csv'},
    'S13':{'annotation_donor_metrics.csv'},
}


def digest(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def admit_donor_receipt(key,folder,receipt,*,root=ROOT):
    if key not in DONOR_PANELS:raise ValueError('Not a donor figure')
    root=Path(root).resolve();folder=Path(folder);data=root/DATA
    manifest_path=data/'manifest.json';manifest=json.loads(manifest_path.read_text())
    if key=='S12':
        if manifest.get('clustering_ready') is not True:
            raise ValueError('Donor clustering score bank is not admitted')
    elif (manifest.get('publication_ready') is not True
            or manifest.get('annotation_requests_terminal') is not True):
        raise ValueError('Donor annotation figure is not admitted')
    # Recheck the complete portable bank, including its scientific input proofs.
    for name,spec in manifest['files'].items():
        path=(data/name).resolve()
        expected=spec['sha256'] if isinstance(spec,dict) else spec
        if not path.is_relative_to(data) or digest(path)!=expected:
            raise ValueError('Donor score bank checksum differs: '+name)
    expected_inputs={str(DATA/'manifest.json'):digest(manifest_path)}
    for name in REQUIRED_SOURCES[key]:
        spec=manifest['files'][name]
        expected_inputs[str(DATA/name)]=spec['sha256'] if isinstance(spec,dict) else spec
    if receipt.get('inputs')!=expected_inputs:
        raise ValueError('Donor figure is not bound to the admitted score sources')
    figure='Figure_'+key
    if receipt.get('figure')!=figure:raise ValueError('Donor receipt identity differs')
    expected_files={figure+ext for ext in ['.svg','.pdf','.png','.tiff']}
    if set(receipt.get('files',{}))!=expected_files:
        raise ValueError('Donor receipt native format set differs')
    rendered=json.loads((folder/'donor47_figure_manifest.json').read_text())
    if rendered.get('source_manifest')!=str(DATA/'manifest.json'):
        raise ValueError('Donor figure source manifest must be repository-relative')
    if rendered.get('source_manifest_sha256')!=digest(manifest_path):
        raise ValueError('Donor figure manifest score source differs')
    if rendered.get('figures',{}).get(key)!=receipt:
        raise ValueError('Dedicated donor figure receipt differs')
    if rendered.get('new_calls_or_fits')!=0:
        raise ValueError('Publication renderer must be offline')
    for field,name in [('renderer_sha256','scripts/render_donor47_figures.py'),
                       ('shared_style_sha256','scripts/publication_figure_design.py')]:
        if rendered.get(field)!=digest(root/name):
            raise ValueError('Donor rendering source checksum differs')
    return {'route':'dedicated_donor47_receipt','panel_letters':DONOR_PANELS[key],
            'score_manifest_sha256':digest(manifest_path),'source_files_verified':len(manifest['files'])}
