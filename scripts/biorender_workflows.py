"""Preserve the author's BioRender artwork with editable, print-size labels.

The BioRender PDF is a native authoring export, not an article screenshot.
Original vectors and image pixels are reused without independent stretching.
Imported raster text is replaced by native Arial text in the figure renderer.
"""
from __future__ import annotations

from copy import deepcopy
import hashlib
import json
import re
from pathlib import Path
import xml.etree.ElementTree as ET

import fitz
import numpy as np
from matplotlib.patches import Rectangle

from publication_figure_design import ROOT, axes, text

CONFIG = ROOT/'configs/biorender_workflows.json'


def config():
    d = json.loads(CONFIG.read_text())
    source = ROOT/d['source_file']
    if hashlib.sha256(source.read_bytes()).hexdigest() != d['source_sha256']:
        raise ValueError('BioRender source checksum differs.')
    return d


def artwork_document():
    d = config()
    doc = fitz.open(ROOT/d['source_file'])
    page = doc[0]
    # Remove the tiny, unlabelled template color key. It is a native PDF
    # shading; MuPDF otherwise converts it to a low-resolution SVG bitmap.
    for xref in range(1,doc.xref_length()):
        if doc.xref_is_stream(xref) and '/Subtype /Form' in doc.xref_object(xref):
            stream=doc.xref_stream(xref)
            if b'/Sh1 scn' in stream:
                stream,count=re.subn(rb'q\s+[^qQ]*?/Pattern\s+cs\s+/Sh1\s+scn[^qQ]*?Q',b'',stream)
                if count != 1:
                    raise ValueError('Expected one BioRender template color key.')
                doc.update_stream(xref,stream)
    # Delete only imported raster text, keeping original icon/vector geometry.
    for image in page.get_image_info():
        if image['width'] in [742,1542,1184]:
            page.add_redact_annot(image['bbox'],fill=False)
    page.apply_redactions(images=1,graphics=0,text=1)
    spans = [s for b in page.get_text('dict')['blocks'] if 'lines' in b
             for line in b['lines'] for s in line['spans'] if s['text'].strip()]
    for span in spans:
        page.add_redact_annot(span['bbox'],fill=False)
    page.apply_redactions(images=0,graphics=0,text=0)
    # The small PIXIE icon contains generic template phase captions baked into
    # its bitmap. Remove those sub-print-size words while keeping the clusters.
    for image in page.get_image_info():
        if (image['width'],image['height']) == (192,180):
            box=fitz.Rect(image['bbox'])
            for x0,y0,x1,y1 in [(8,15,78,56),(88,4,178,47),(99,149,191,180)]:
                area=fitz.Rect(box.x0+box.width*x0/192,box.y0+box.height*y0/180,
                               box.x0+box.width*x1/192,box.y0+box.height*y1/180)
                page.add_redact_annot(area,fill=(1,1,1))
    page.apply_redactions(images=2,graphics=0,text=1)
    return doc


def feature_table(f,x,y,w,h,size=5.5):
    a = axes(f,x,y,w,h)
    a.set_axis_off()
    widths = np.array([.18,.065,.065,.265,.265,.16])
    edges = np.r_[0,np.cumsum(widths)]
    labels = [['','x','y','Marker 1','Marker 2','...'],
              ['Cell 1','','','','',''],['Cell 2','','','','',''],
              ['Cell 3','','','','',''],['...','','','','','']]
    for row,values in enumerate(labels):
        for col,value in enumerate(values):
            a.add_patch(Rectangle((edges[col],1-(row+1)/5),widths[col],1/5,
                                 transform=a.transAxes,fc='#606060' if row in [1,3] else 'black',
                                 ec='white',lw=.3))
            if value:
                a.text((edges[col]+edges[col+1])/2,1-(row+.5)/5,value,
                       transform=a.transAxes,ha='center',va='center',color='white',fontsize=size)


def add_workflow(f,key):
    d = config()
    spec = deepcopy(d['panels'][key])
    if not hasattr(f,'_biorender_overlays'):
        f._biorender_overlays = []
    f._biorender_overlays.append(spec)
    if key == '2A':
        for x,title in [(16.5,'CODEX images'),(43,'Cell-level features'),(74,'Clustering'),
                        (92,'UMAP'),(124,'Reference-majority\ncluster labels'),(151,'Evaluation')]:
            text(f,x,3,title,size=6.6,ha='center')
        feature_table(f,23.8,16.5,38.3,14,size=6.6)
        for x,label in zip([146.5,151.7,156.9],'ABC'):
            text(f,x,34.5,label,size=6.6,ha='center')
    elif key == '3A':
        for x,title in [(22,'CODEX features'),(49,'Clustering'),(74,'Cluster features'),
                        (107,'Optimization'),(130,'Annotation'),(150,'Evaluation')]:
            text(f,x,2.5,title,size=6.5,ha='center')
        feature_table(f,4.8,15,34.5,12.5)
        text(f,58.2,13.4,'{\n"cluster 1": ["marker 1",\n  "marker 2", ...],\n"cluster 2": ["marker 1",\n  "marker 2", ...],\n... }',size=5.5,linespacing=1.13)
        text(f,94.4,15.2,'1. Expression threshold\n2. Fraction threshold\n3. Mean expression threshold\n4. Maximum number of markers\n5. Minimum number of markers',size=5.5,linespacing=1.2)
    elif key == '4A':
        for x,title in [(15,'CODEX images'),(54,'Cell-level features'),(98,'Leiden clustering'),
                        (122,'Claude annotation'),(149,'Spatial visualization')]:
            text(f,x,3,title,size=6.5,ha='center')
        feature_table(f,32.9,10.5,42.5,14.8)
    else:
        raise ValueError(key)
    return {d['source_file']:d['source_sha256'],str(CONFIG.relative_to(ROOT)):hashlib.sha256(CONFIG.read_bytes()).hexdigest()}


def compose(f,output,name):
    """Keep vector artwork in PDF/SVG and rasterize only the final PNG export."""
    source = artwork_document()
    pdf = fitz.open(output/(name+'.pdf'))
    svg_path = output/(name+'.svg')
    svg = ET.parse(svg_path)
    ns = 'http://www.w3.org/2000/svg'
    ET.register_namespace('',ns)
    ET.register_namespace('xlink','http://www.w3.org/1999/xlink')
    source_svg = ET.fromstring(source[0].get_svg_image(text_as_path=False))
    for overlay in f._biorender_overlays:
        x,y,w,h = overlay['rect_mm']
        rect = fitz.Rect(x,y,x+w,y+h)*(72/25.4)
        pdf[0].show_pdf_page(rect,source,0,clip=fitz.Rect(overlay['clip_points']),keep_proportion=True,overlay=False)
        nested = deepcopy(source_svg)
        nested.attrib.update({'x':str(x*72/25.4),'y':str(y*72/25.4),
                              'width':str(w*72/25.4),'height':str(h*72/25.4),
                              'viewBox':' '.join(str(v) for v in [overlay['clip_points'][0],overlay['clip_points'][1],
                                        overlay['clip_points'][2]-overlay['clip_points'][0],
                                        overlay['clip_points'][3]-overlay['clip_points'][1]]),
                              'preserveAspectRatio':'xMidYMid meet','overflow':'hidden'})
        svg.getroot().insert(0,nested)
    # The cleaned source contains no remaining native text. All labels are
    # the explicitly authored Matplotlib text above and remain editable.
    temp = output/(name+'.composed.pdf')
    pdf.save(temp,garbage=4,deflate=True)
    pdf.close();temp.replace(output/(name+'.pdf'))
    svg.write(svg_path,encoding='utf-8',xml_declaration=True)
    with fitz.open(output/(name+'.pdf')) as final:
        pixmap=final[0].get_pixmap(dpi=600,alpha=False)
        pixmap.save(output/(name+'.png'))
        final[0].get_pixmap(matrix=fitz.Matrix(160/72,160/72),alpha=False).save(output/(name+'_preview.png'))
