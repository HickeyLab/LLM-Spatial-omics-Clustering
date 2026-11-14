"""Cross-donor evaluation tables in editable IEEE style from frozen scores."""
from __future__ import annotations
import argparse
import csv
import hashlib
import html
import json
from pathlib import Path
import re
import sys

import numpy as np
import pandas as pd

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'scripts'));sys.path.insert(0,str(ROOT/'scripts/revision'))
import render_donor47_figures as donor
import render_ieee_tables as style
WEIGHTS=style.WEIGHTS;NUMERIC=style.NUMERIC


def number(value,*,percent=False,signed=False):
    if not np.isfinite(float(value)):raise ValueError('A publication cell cannot contain a pending/nonfinite score')
    return f'{float(value)*100:+.2f}' if signed else f'{float(value)*100:.2f}' if percent else f'{float(value):.4f}'


def unique_row(rows,**keys):
    selected=rows
    for key,value in keys.items():selected=selected[selected[key].eq(value)]
    if len(selected)!=1:raise ValueError('Missing/duplicate table condition: '+str(keys))
    return selected.iloc[0]


def count(row,*keys):
    for key in keys:
        if key in row and pd.notna(row[key]):
            value=float(row[key])
            if value!=int(value):raise ValueError('A count is not an integer: '+key)
            return f'{int(value):,}'
    raise ValueError('Missing count: '+str(keys))


def table_specs(scores):
    output={}
    def add(key,title,rows,weights,numeric,note,sources):
        if any(len(row)!=len(rows[0]) for row in rows) or len(weights)!=len(rows[0]):raise ValueError('Table shape differs')
        output[key]={'title':title,'rows':rows,'weights':weights,'numeric':numeric,'note':note,'sources':sources}
    annotations=scores.table('annotation_donor_metrics.csv');primary=donor.evaluation(annotations,donor.PRIMARY)
    donor.validate_coverage(primary)
    common=('Agreement, macro-F1 and cell coverage average each donor\'s eight regions equally. Cluster coverage uses whole-donor occupied clusters. The full native 28-label vocabulary includes Noise (code 21). '
        'Missing/invalid predictions remain errors in the fixed planned denominator and differ from valid Noise predictions. '
        'One planned annotation per cluster/condition; accepted outputs are scored where available. No repeated-generation uncertainty is estimated.')
    for d,key in zip(donor.DONORS,['S13a','S13b']):
        rows=[['Clustering','Model','Agreement (%)','Macro-F1','Cell coverage (%)','Cluster coverage (%)']]
        for method,label in zip(donor.METHODS,donor.METHOD_LABELS):
            for family,model in zip(donor.FAMILIES,donor.MODEL_LABELS):
                row=unique_row(primary,donor=d,method=method,family=family)
                rows.append([label,model,number(row.agreement,percent=True),number(row.macro_f1),
                    number(row.cell_delivery_coverage,percent=True),number(row.cluster_delivery_coverage,percent=True)])
        add(key,d+' donor annotation',rows,[19,17,17,13,17,17],[2,3,4,5],common,['annotation_donor_metrics.csv'])
    equal=donor.evaluation(scores.table('annotation_equal_donor_metrics.csv'),donor.PRIMARY)
    base=scores.table('baselines_donor_metrics.csv')
    base=donor.evaluation(base[base.arm.eq(donor.ARM)],donor.PRIMARY)
    rows=[['Clustering','Annotator','Agreement (%)','Macro-F1','Cell coverage (%)']]
    for method,label in zip(donor.METHODS,donor.METHOD_LABELS):
        for family,model in zip(donor.FAMILIES,donor.MODEL_LABELS):
            row=unique_row(equal,method=method,family=family)
            rows.append([label,model,number(row.agreement,percent=True),number(row.macro_f1),number(row.cell_delivery_coverage,percent=True)])
        for classifier,model in zip(donor.CLASSIFIERS,['Nearest centroid','Logistic regression']):
            selected=base[base.method.eq(method)&base.classifier.eq(classifier)]
            if len(selected)!=2 or set(selected.donor)!=set(donor.DONORS):raise ValueError('Frozen baseline donor pair differs')
            rows.append([label,model,number(selected.agreement.mean(),percent=True),number(selected.macro_f1.mean()),
                number(selected.cell_delivery_coverage.mean(),percent=True)])
    add('S13c','Equal-donor annotation and frozen classifiers',rows,[18,28,18,16,20],[2,3,4],
        'B005 and B006 receive equal weight after equal region weighting within donor. All models use the same 47 means plus 47 fractions, decoded from integer thousandths. '
        'Baselines retain B004 training-cell reference supervision and frozen weights; no donor fitting, class balancing or hyperparameter selection. '+common,
        ['annotation_equal_donor_metrics.csv','baselines_donor_metrics.csv'])
    output.update(clustering_table_specs(scores))
    native=donor.evaluation(annotations,donor.ELIGIBLE_NATIVE);coarse=donor.evaluation(annotations,donor.SHARED23)
    for d,key in zip(donor.DONORS,['S15a','S15b']):
        rows=[['Clustering','Model','Native 28 agreement (%)','Shared 23 agreement (%)','Change (pp)',
            'Native 28 macro-F1','Shared 23 macro-F1','23-label coverage (%)']]
        for method,label in zip(donor.METHODS,donor.METHOD_LABELS):
            for family,model in zip(donor.FAMILIES,donor.MODEL_LABELS):
                n=unique_row(native,donor=d,method=method,family=family);s=unique_row(coarse,donor=d,method=method,family=family)
                if int(n.n_cells)!=int(s.n_cells):raise ValueError('Ontology comparison changed its eligible-cell denominator')
                rows.append([label,model,number(n.agreement,percent=True),number(s.agreement,percent=True),
                    number(s.agreement-n.agreement,signed=True),number(n.macro_f1),number(s.macro_f1),
                    number(s.in_vocabulary_prediction_coverage,percent=True)])
        add(key,d+' evaluation vocabulary sensitivity',rows,[14,12,13,13,10,11,11,16],[2,3,4,5,6,7],
            'Both vocabularies use exactly the same reference-eligible cells. Shared-23 evaluation merges or renames the approved classes; reference ITLN+Epithelial, Noise and PDPN+Stromal are outside that eligibility set. '
            'Projected predictions outside the 23-label vocabulary remain errors and never remove cells. Vocabulary coverage is separate from native output delivery coverage. '
            'Macro-F1 uses its stated fixed vocabulary (28 or 23); class-count changes are part of the sensitivity, with no new model generation.',
            ['annotation_donor_metrics.csv'])
    return output


def clustering_table_specs(scores):
    output={}
    def add(key,title,rows,weights,numeric,note,sources):
        if any(len(row)!=len(rows[0]) for row in rows) or len(weights)!=len(rows[0]):raise ValueError('Table shape differs')
        output[key]={'title':title,'rows':rows,'weights':weights,'numeric':numeric,'note':note,'sources':sources}
    clust=scores.table('clustering_donor_metrics.csv')
    if 'evaluation' in clust:clust=donor.evaluation(clust,donor.PRIMARY)
    counts=scores.table('clustering_pooled_metrics.csv')
    counts=counts[counts.evaluation.eq(donor.PRIMARY)&counts.aggregation.eq('pooled_descriptive')]
    rows=[['Donor','Clustering','Cells','Clusters','Purity','ARI','NMI']]
    for d in donor.DONORS:
        for method,label in zip(donor.METHODS,donor.METHOD_LABELS):
            row=unique_row(clust,donor=d,method=method)
            whole=unique_row(counts,donor=d,method=method)
            if int(row.n_cells)!=int(whole.n_cells):raise ValueError('Whole-donor clustering count differs')
            rows.append([d,label,count(row,'n_cells'),count(whole,'occupied_clusters','n_clusters'),
                number(row.purity),number(row.ari),number(row.nmi)])
    add('S14a','Frozen donor clustering',rows,[11,19,15,13,14,14,14],[2,3,4,5,6],
        'Partitions use the frozen method-specific inputs; annotation profiles contain all 47 proteins. Clustering is evaluated against the native 28-label reference, including Noise. Purity, ARI and NMI average the eight regions equally; cells and occupied clusters are whole-donor counts. '
        'SpatialSort seed 42 is primary; each donor chain uses 50 sweeps and DMH = 5.',
        ['clustering_donor_metrics.csv','clustering_pooled_metrics.csv'])
    if scores.has('spatialsort_seed_sensitivity.csv'):
        seed=donor.seed_comparison(scores)
        rows=[['Donor','Cells','Seed 42 clusters','Seed 43 clusters','Partition ARI']]
        for d in donor.DONORS:
            row=unique_row(seed,donor=d)
            rows.append([d,count(row,'n_cells'),count(row,'seed42_clusters'),count(row,'seed43_clusters'),number(row.partition_ari)])
        add('S14b','SpatialSort seed sensitivity',rows,[14,20,22,22,22],[1,2,3,4],
            'Both seeds use the same donor cells, 47-marker source and 50-sweep/DMH = 5 budget. Partition ARI compares the two memberships on all common donor cells. '
            'Seed 43 is used only for clustering sensitivity, with no additional annotation calls or reference-guided seed selection.',
            ['spatialsort_seed_sensitivity.csv'])
    return output


def render(scores,output,selected=None):
    output=Path(output);output.mkdir(parents=True,exist_ok=True)
    if selected is not None and set(selected).issubset({'S14a','S14b'}):
        specs=clustering_table_specs(scores)
    else:
        if scores.scope!='annotation':raise ValueError('Annotation tables cannot use clustering-only admission')
        specs=table_specs(scores)
    if selected is not None:
        if not set(selected).issubset(specs):raise ValueError('Unknown selected table')
        specs={key:specs[key] for key in selected}
    manifest={'schema':'donor47.ieee_native_tables.v1','new_scientific_calls_or_fits':0,'scope':scores.scope,
        'source_manifest_sha256':sha(scores.directory/'manifest.json'),'renderer_sha256':sha(__file__),
        'shared_style_sha256':sha(ROOT/'scripts/revision/render_ieee_tables.py'),'tables':{}}
    cells={'schema':'donor47.ieee_table_cells.v1','tables':{}};fragments=[]
    for key,spec in specs.items():
        WEIGHTS[key]=spec['weights'];NUMERIC[key]=spec['numeric'];rows=spec['rows']
        label,title=style.caption(key,'Table '+key+'. '+spec['title']+'.')
        heading='<p style="font-family:Times New Roman,Times,serif;font-size:11pt;font-weight:bold;text-align:center;">'+html.escape(label)+'<br>'+html.escape(title)+'</p>'
        note='<p style="font-family:Times New Roman,Times,serif;font-size:10pt;">'+html.escape(spec['note'])+'</p>'
        fragment=heading+style.table_html(key,rows)+note
        fragments.append((key,fragment))
        (output/(key+'.html')).write_text('<html><body>'+fragment+'</body></html>\n')
        (output/(key+'.standalone.html')).write_text('<!doctype html><meta charset="utf-8"><body style="margin:24px;background:white;">'+fragment+'</body>\n')
        for ext,delimiter in [('csv',','),('tsv','\t')]:
            name=('Table_'+key if ext=='csv' else key)+'.'+ext
            with (output/name).open('w',newline='') as file:csv.writer(file,delimiter=delimiter,lineterminator='\n').writerows(rows)
        tex=style.table_tex(key,rows,label,title)
        tex=tex.replace(r'\fontsize{10}{12}\selectfont'+'\n'+style.tex_escape(label)+r'\\'+'\n'+style.tex_escape(title)+r'\par\smallskip',
            r'\fontsize{11}{13.2}\selectfont\bfseries'+'\n'+style.tex_escape(label)+r'\\'+'\n'+style.tex_escape(title)+r'\par\smallskip'+
            '\n'+r'\normalfont\fontsize{10}{12}\selectfont')
        tex=tex.replace(r'\end{tabularx}',r'\end{tabularx}'+'\n'+r'\par\smallskip\noindent '+style.tex_escape(spec['note'])+r'\par')
        (output/(key+'.tex')).write_text(tex)
        preview=render_preview(output/key,key,rows,label,title,note=spec['note'])
        cell_sha=hashlib.sha256(style.canonical_rows(rows)).hexdigest()
        sources={name:sha(scores.path(name)) for name in spec['sources']}
        cells['tables'][key]={'rows':rows,'caption':'Table '+key+'. '+spec['title']+'.','note':spec['note'],
            'cell_order_sha256':cell_sha,'sources':sources}
        files=[output/(key+ext) for ext in ['.html','.standalone.html','.tsv','.tex','.pdf','.png','.svg','.tiff','_preview.png']]
        files.append(output/('Table_'+key+'.csv'))
        manifest['tables'][key]={'caption_label':label,'caption_title':title,'rows_including_header':len(rows),
            'columns':len(rows[0]),'cell_order_sha256':cell_sha,'sources':sources,'render':preview,
            'files':{p.name:{'sha256':sha(p),'bytes':p.stat().st_size} for p in files}}
    combined='<!doctype html><meta charset="utf-8"><html><body>'+''.join(fragment for _,fragment in fragments)+'</body></html>\n'
    (output/'all_tables.html').write_text(combined)
    paginated='<!doctype html><meta charset="utf-8"><html><body>'+''.join(
        ('<div style="break-before:page;page-break-before:always;"></div>' if i else '')+fragment
        for i,(_,fragment) in enumerate(fragments))+'</body></html>\n'
    (output/'all_tables_paginated.html').write_text(paginated)
    paste_order={'schema':'donor47.ieee_table_paste_order.v1','order':[key for key,_ in fragments],
        'continuous_html':'all_tables.html','page_break_html':'all_tables_paginated.html',
        'page_break_before':[key for key,_ in fragments[1:]],
        'page_break_style':'break-before:page;page-break-before:always',
        'note':'The continuous file preserves native table flow; the paginated file requests one table per page. Confirm actual page breaks after native Google Docs paste.'}
    (output/'paste_order.json').write_text(json.dumps(paste_order,indent=2)+'\n')
    manifest['combined_files']={name:{'sha256':sha(output/name),'bytes':(output/name).stat().st_size}
        for name in ['all_tables.html','all_tables_paginated.html','paste_order.json']}
    (output/'source_tables.json').write_text(json.dumps(cells,indent=2)+'\n')
    (output/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    return manifest


sha=style.sha


def normalize_svg(path):
    """Strip generator-only line tails without changing SVG token geometry."""
    path=Path(path)
    path.write_text('\n'.join(line.rstrip() for line in path.read_text().splitlines())+'\n')


def render_preview(path, table_id, rows, label, title, note=None):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.font_manager import FontProperties, findfont
    from matplotlib import rc_context
    from PIL import ImageFont
    for family in ['Times New Roman','Liberation Serif','DejaVu Serif']:
        try:
            font=findfont(FontProperties(family=family),fallback_to_default=False)
            bold_font=findfont(FontProperties(family=family,weight='bold'),fallback_to_default=False)
            break
        except ValueError:pass
    else:raise ValueError('No printable serif font is installed')
    body_fp = FontProperties(fname=font, size=10)
    bold_fp = FontProperties(fname=bold_font, size=10)
    caption_fp = FontProperties(fname=bold_font, size=11)
    body_measure = ImageFont.truetype(font, size=100)
    bold_measure = ImageFont.truetype(bold_font, size=100)
    width_pt = 6.5 * 72
    pad = 4
    col_widths = [width_pt * w / 100 for w in WEIGHTS[table_id]]

    def measure(value, fp):
        if not value:
            return 0
        measuring_font = bold_measure if fp is bold_fp or fp is caption_fp else body_measure
        return measuring_font.getlength(value) / 10 * (fp.get_size_in_points()/10)

    def wrap(value, available, fp):
        if not value:
            return [""]
        lines, current = [], ""
        for token in re.findall(r"\S+\s*", value):
            candidate = current + token
            if measure(candidate.rstrip(), fp) <= available:
                current = candidate
                continue
            if current:
                lines.append(current.rstrip())
                current = ""
            # Identifiers may have no whitespace. Break visually, not in data.
            while measure(token.rstrip(), fp) > available:
                count = 1
                while count < len(token) and measure(token[:count + 1], fp) <= available:
                    count += 1
                delimiters = [m.end() for m in re.finditer(r"[/_-]", token[:count])]
                if delimiters and delimiters[-1] >= 5:
                    count = delimiters[-1]
                lines.append(token[:count])
                token = token[count:]
            current = token
        if current:
            lines.append(current.rstrip())
        return lines

    wrapped = [[wrap(v, col_widths[j] - 2 * pad, bold_fp if i == 0 else body_fp)
                for j, v in enumerate(row)] for i, row in enumerate(rows)]
    line_height = 12
    row_heights = [max(len(c) for c in row) * line_height + 2 * pad for row in wrapped]
    title_lines = wrap(title, width_pt - 8, caption_fp)
    caption_height = 16 + 13.2 * len(title_lines) + 12
    note_lines = wrap(note, width_pt - 8, body_fp) if note else []
    height_pt = caption_height + sum(row_heights) + 8
    if note_lines:
        height_pt += 10 + line_height * len(note_lines)
    with rc_context({"font.family": family, "font.size": 10,
                     "pdf.fonttype": 42, "ps.fonttype": 42, "svg.fonttype": "none"}):
        fig = plt.figure(figsize=(6.5, height_pt / 72), facecolor="white")
        ax = fig.add_axes([0, 0, 1, 1])
        ax.set_xlim(0, width_pt)
        ax.set_ylim(height_pt, 0)
        ax.axis("off")
        ax.text(width_pt / 2, 3, label, ha="center", va="top", fontproperties=caption_fp)
        ax.text(width_pt / 2, 19, "\n".join(title_lines), ha="center", va="top", fontproperties=caption_fp, linespacing=1.2)
        y = caption_height
        ax.plot([0, width_pt], [y, y], color="black", lw=0.8)
        for i, row in enumerate(wrapped):
            x = 0
            for j, lines in enumerate(row):
                numeric = j in NUMERIC[table_id]
                ax.text(x + col_widths[j] - pad if numeric else x + pad, y + pad,
                        "\n".join(lines), ha="right" if numeric else "left", va="top",
                        fontproperties=bold_fp if i == 0 else body_fp, linespacing=1.2)
                x += col_widths[j]
            y += row_heights[i]
            if i == 0:
                ax.plot([0, width_pt], [y, y], color="black", lw=0.6)
        ax.plot([0, width_pt], [y, y], color="black", lw=0.8)
        if note_lines:
            ax.text(4, y + 10, "\n".join(note_lines), ha="left", va="top",
                    fontproperties=body_fp, linespacing=1.2)
        fig.savefig(path.with_suffix(".pdf"), metadata={"Creator": "render_donor47_tables.py", "CreationDate": None, "ModDate": None})
        fig.savefig(path.with_suffix(".png"), dpi=600)
        fig.savefig(path.with_suffix('.svg'),metadata={'Date':None})
        normalize_svg(path.with_suffix('.svg'))
        fig.savefig(path.with_name(path.name+'_preview.png'),dpi=160)
        from PIL import Image
        with Image.open(path.with_suffix('.png')) as image:
            image.convert('RGB').save(path.with_suffix('.tiff'),dpi=(600,600),compression='tiff_lzw')
        plt.close(fig)
    return {"width_inches": 6.5, "height_inches": height_pt / 72,
            "font_points": 10, "font_file_basename": Path(font).name,
            "caption_font_points":11,"caption_bold":True,
            "horizontal_rules": 3, "vertical_rules": 0, "interior_body_rules": 0}

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--data',type=Path,default=donor.DATA)
    p.add_argument('--output',type=Path,default=ROOT/'docs/tables/ieee_donor47_20261114')
    p.add_argument('--tables',nargs='+')
    a=p.parse_args();scope='clustering' if a.tables and set(a.tables).issubset({'S14a','S14b'}) else 'annotation'
    print(json.dumps({'tables':list(render(donor.Scores(a.data,scope=scope),a.output,a.tables)['tables'])}))


if __name__=='__main__':main()
