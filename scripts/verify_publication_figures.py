#!/usr/bin/env python3
"""Check native figure typography, resolution, inputs and manuscript placement.

Google Docs exports compressed previews. Their geometry and visual identity
are checked separately from the original 600 dpi submission files.
"""
from __future__ import annotations

import argparse
from collections import Counter
import hashlib
from io import BytesIO
import json
from pathlib import Path
import re
import xml.etree.ElementTree as ET
import zipfile

import fitz
import numpy as np
import pandas as pd
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
ORDER = ['5','1','2','3','4','S1','S2','S3A','S3B','S3C','S4','S5','S6','S7','S8','S9','S10']
PANELS = {'1':'ABCDEF','2':'ABCDEFGHIJ','3':'ABCDEFGH','4':'ABCDE','5':'ABCD',
          'S1':'ABC','S2':'AB','S3A':'A','S3B':'B','S3C':'C','S4':'ABCDE',
          'S5':'AB','S6':'AB','S7':'','S8':'AB','S9':'ABCD','S10':'ABCD'}
NS = {'w':'http://schemas.openxmlformats.org/wordprocessingml/2006/main',
      'a':'http://schemas.openxmlformats.org/drawingml/2006/main',
      'wp':'http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing',
      'r':'http://schemas.openxmlformats.org/officeDocument/2006/relationships'}


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def verify_selected_e():
    """Independently check the archived selection values against cell labels."""
    selected = pd.read_csv(ROOT/'data/frozen/publication_design/figure3_celltype_selected.csv')
    annotations = pd.read_csv(ROOT/'data/frozen/manuscript_replay/figure_03/annotations.csv.gz')
    count = 0
    for row in selected.itertuples():
        group = annotations.loc[annotations.truth_normalized.eq(row.truth_label)]
        correct = (group.phase7_prediction.eq(group.truth_normalized) |
                   group['leiden__'+row.llm].eq(group.truth_normalized))
        assert len(group) == row.n_cells
        assert int(correct.sum()) == row.correct_cells
        np.testing.assert_allclose(correct.mean(),row.exact_cell_accuracy,rtol=0,atol=1e-12)
        count += 1
    return count


def verify_native(folder, render_qa=None):
    data = ROOT/'data/frozen/publication_design'
    manifest = json.loads((data/'manifest.json').read_text())
    for name,entry in manifest['files'].items():
        assert digest(data/name) == entry['sha256'], f'Frozen input changed: {name}'
    results = []
    for key in ORDER:
        name = 'Figure_'+key
        receipt = json.loads((folder/(name+'_verification.json')).read_text())
        for filename,entry in receipt['files'].items():
            assert digest(folder/filename) == entry['sha256'], filename
        for source,sha in receipt['inputs'].items():
            assert digest(ROOT/source) == sha, source
        with Image.open(folder/(name+'.png')) as image:
            pixels = np.asarray(image.convert('RGB'))
            width,height = image.size
            assert min(image.info['dpi']) >= 599.9
        with Image.open(folder/(name+'.tiff')) as image:
            assert image.size == (width,height)
            assert min(image.info['dpi']) >= 600
            assert image.mode == 'RGB'
            np.testing.assert_array_equal(pixels,np.asarray(image))
        # A one-pixel rounding allowance is appropriate for raster dimensions.
        assert abs(width-receipt['width_mm']/25.4*600) <= 1.01
        assert abs(height-receipt['height_mm']/25.4*600) <= 1.01
        doc = fitz.open(folder/(name+'.pdf'))
        assert len(doc) == 1
        page = doc[0]
        spans = [s for b in page.get_text('dict')['blocks'] if 'lines' in b
                 for line in b['lines'] for s in line['spans'] if s['text'].strip()]
        minimum = min(s['size'] for s in spans)
        assert minimum >= 5.4999, (name,minimum)
        assert abs(minimum-receipt['minimum_font_pt']) < .001
        assert {s['font'] for s in spans}.issubset({'ArialMT','Arial-BoldMT','Arial-ItalicMT'})
        letters = [s['text'] for s in spans if s['size'] >= 7.99 and 'Bold' in s['font']
                   and re.fullmatch('[A-J]',s['text'])]
        assert ''.join(sorted(letters)) == PANELS[key], (name,letters)
        assert not any(re.fullmatch(r'\([A-J]\)',s['text']) for s in spans)
        assert not re.search(r'\bFigure\s+(?:[1-5]|S\d)',page.get_text())
        assert abs(page.rect.width-receipt['width_mm']/25.4*72) < .01
        assert abs(page.rect.height-receipt['height_mm']/25.4*72) < .01
        image_dpi = []
        original_workflow = receipt.get('original_raster_workflow')
        original_workflow_count = 0
        for layer in page.get_image_info(xrefs=True):
            box = fitz.Rect(layer['bbox'])
            # MuPDF can report a zero-size placeholder for a redacted source
            # object. It has no pixels, footprint or printed resolution.
            if not box.width or not box.height:
                assert layer['width'] == layer['height'] == 0
                continue
            layer_dpi = [72*layer['width']/box.width,72*layer['height']/box.height]
            image_dpi.extend(layer_dpi)
            if original_workflow and [layer['width'],layer['height']] == original_workflow['native_size_pixels']:
                # Verify the original bitmap's actual pixels and placement;
                # its source detail is independent of the output container dpi.
                assert key == '1'
                spec = json.loads((ROOT/'configs/figure_01_original_workflow.json').read_text())
                assert all(original_workflow[k] == v for k,v in spec.items())
                assert digest(ROOT/spec['source_file']) == spec['source_sha256']
                with Image.open(ROOT/spec['source_file']) as source:
                    expected = np.asarray(source.convert('RGB').crop(spec['crop_pixels']))
                assert hashlib.sha256(expected.tobytes()).hexdigest() == spec['crop_rgb_sha256']
                original = expected.copy()
                expected = expected.copy()
                allowed = np.zeros(expected.shape[:2],dtype=bool)
                left,top,_,_ = spec['crop_pixels']
                for region in spec['erase_regions']:
                    x0,y0,x1,y1 = region['rect_pixels']
                    expected[y0-top:y1-top,x0-left:x1-left] = region['fill_rgb']
                    allowed[y0-top:y1-top,x0-left:x1-left] = True
                assert hashlib.sha256(expected.tobytes()).hexdigest() == spec['cleaned_crop_rgb_sha256']
                embedded = fitz.Pixmap(doc,layer['xref'])
                actual = np.frombuffer(embedded.samples,dtype=np.uint8).reshape(layer['height'],layer['width'],3)
                if layer['transform'][3] < 0:
                    actual = actual[::-1]
                np.testing.assert_array_equal(actual,expected)
                np.testing.assert_array_equal(actual[~allowed],original[~allowed])
                # Check the replacement labels independently in the PDF's
                # native text layer, including their declared font sizes.
                workflow_text = Counter((s['text'],round(s['size'],2)) for s in spans
                                        if s['bbox'][1] < 31*72/25.4)
                required = Counter((line,label['font_pt']) for label in spec['labels']
                                   for line in label['text'].splitlines())
                assert not (required-workflow_text), required-workflow_text
                x,y,w,h = spec['rect_mm']
                np.testing.assert_allclose(list(box),np.array([x,y,x+w,y+h])*72/25.4,atol=.001,rtol=0)
                np.testing.assert_allclose(layer_dpi,original_workflow['effective_source_dpi'],atol=.001,rtol=0)
                original_workflow_count += 1
            else:
                assert min(layer_dpi) >= 600
        assert original_workflow_count == int(bool(original_workflow))
        svg = ET.parse(folder/(name+'.svg')).getroot()
        text_nodes = svg.findall('.//{http://www.w3.org/2000/svg}text')
        assert len(text_nodes) >= len(spans)*.7, f'Editable text missing: {name}'
        if render_qa:
            render_qa.mkdir(parents=True,exist_ok=True)
            page.get_pixmap(matrix=fitz.Matrix(1.7,1.7),alpha=False).save(render_qa/(name+'.png'))
        results.append({'figure':name,'minimum_font_pt':minimum,'panel_letters':PANELS[key],
                        'png_tiff_dpi':600,'minimum_pdf_image_dpi':min(image_dpi,default=None),
                        'editable_svg_text_nodes':len(text_nodes)})
    return results


def verify_docx(path, folder, image_suggestions_pending=False):
    results = []
    with zipfile.ZipFile(path) as archive:
        document = ET.fromstring(archive.read('word/document.xml'))
        relationships = {x.attrib['Id']:x.attrib['Target'] for x in
                         ET.fromstring(archive.read('word/_rels/document.xml.rels'))}
        drawings = document.findall('.//w:drawing',NS)
        assert len(drawings) == len(ORDER)
        for key,drawing in zip(ORDER,drawings):
            name = 'Figure_'+key
            receipt = json.loads((folder/(name+'_verification.json')).read_text())
            extent = drawing.find('.//wp:extent',NS)
            x,y = [int(extent.attrib[k])/36000 for k in ['cx','cy']]
            distortion = (x/y)/(receipt['width_mm']/receipt['height_mm'])-1
            # Google Docs rounds image heights to hundredths of an inch.
            assert abs(distortion) < .002, (name,distortion)
            font = receipt['minimum_font_pt']*min(x/receipt['width_mm'],y/receipt['height_mm'])
            assert font >= 5, (name,font)
            crop = drawing.find('.//a:srcRect',NS)
            assert crop is None or all(int(v)==0 for v in crop.attrib.values()), (name,'cropped')
            blip = drawing.find('.//a:blip',NS)
            target = relationships[blip.attrib['{'+NS['r']+'}embed']]
            preview = Image.open(BytesIO(archive.read('word/'+target))).convert('RGB')
            with Image.open(folder/(name+'.png')) as source:
                expected = source.convert('RGB').resize(preview.size,Image.Resampling.LANCZOS)
            error = float(np.abs(np.asarray(preview,dtype=float)-np.asarray(expected,dtype=float)).mean())
            # Google Docs exports the original image while a replacement is
            # pending, even though the live editor shows the proposed image.
            # A low whole-image error cannot prove a text-only replacement.
            if not image_suggestions_pending:
                assert error < 5, (name,'wrong artwork or severe resampling',error)
            results.append({'figure':name,'placed_width_mm':x,'placed_height_mm':y,
                            'aspect_ratio_error_percent':100*distortion,'minimum_font_pt':font,
                            'preview_mean_absolute_rgb_error':error,
                            'image_replacement_identity_verified':False if image_suggestions_pending else None,
                            'image_suggestions_pending':image_suggestions_pending,
                            'google_docs_preview_dpi':min(preview.width*25.4/x,preview.height*25.4/y)})
        text = '\n'.join(''.join(p.itertext()) for p in document.findall('.//w:p',NS))
        caption = next(p for p in text.splitlines() if p.startswith('Figure 3.'))
        # The live manuscript has a pending wording suggestion that adds
        # "output". Both readings retain the same reference-selected metric.
        assert re.search(r'\(E\) Cell-type-specific reference agreement after '
                         r'post-hoc reference-informed (?:output )?selection',caption)
        assert '(E) Cell-type-specific reference agreement as a percentage' not in caption
    return results


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--folder',type=Path,default=ROOT/'figures/publication')
    parser.add_argument('--docx',type=Path)
    parser.add_argument('--image-suggestions-pending',action='store_true',
                        help='Check exported placement without asserting that pending image replacements are exported.')
    parser.add_argument('--render-qa',type=Path)
    parser.add_argument('--receipt',type=Path)
    args = parser.parse_args()
    result = {'status':'pass','native_figures':verify_native(args.folder,args.render_qa),
              'independently_checked_figure_3e_rows':verify_selected_e(),
              'new_model_calls':0,'new_fits':0}
    if args.docx:
        result['manuscript_export_sha256'] = digest(args.docx)
        result['manuscript_placement'] = verify_docx(args.docx,args.folder,args.image_suggestions_pending)
        result['submission_files'] = 'Use original 600 dpi PNG/TIFF or editable PDF/SVG, not Google Docs previews.'
    if args.receipt:
        args.receipt.parent.mkdir(parents=True,exist_ok=True)
        args.receipt.write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result,indent=2))


if __name__ == '__main__':
    main()
