"""Check editable IEEE table exports against their frozen cells and styling."""
import csv
import json
from pathlib import Path
import re
import sys
import tempfile
import unittest
import xml.etree.ElementTree as ET

ROOT=Path(__file__).resolve().parents[1]
TABLES=ROOT/'docs/tables/ieee_donor47_20261114'


class TableExportTests(unittest.TestCase):
    def test_SVG_normalization_preserves_geometry_and_final_newline(self):
        sys.path.insert(0,str(ROOT/'scripts/revision'))
        from render_donor47_tables import normalize_svg
        text='<svg><path d="M 0 1  \nL 2 3 \t\n"/><text>A</text></svg>  \n'
        before=ET.fromstring(text)
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'fixture.svg';path.write_text(text);normalize_svg(path);actual=path.read_text()
        self.assertTrue(actual.endswith('\n'));self.assertFalse(actual.endswith('\n\n'))
        self.assertTrue(all(line==line.rstrip() for line in actual.splitlines()))
        after=ET.fromstring(actual)
        self.assertEqual(before.find('path').attrib['d'].split(),after.find('path').attrib['d'].split())
        self.assertEqual(before.find('text').text,after.find('text').text)
    def test_all_table_SVGs_are_whitespace_normalized(self):
        manifest=json.loads((TABLES/'manifest.json').read_text())
        for key in manifest['tables']:
            text=(TABLES/(key+'.svg')).read_text()
            self.assertTrue(text.endswith('\n'))
            self.assertTrue(all(line==line.rstrip() for line in text.splitlines()))
    def test_LaTeX_captions_and_notes_agree_with_editable_table_source(self):
        sys.path.insert(0,str(ROOT/'scripts/revision'))
        from render_ieee_tables import tex_escape
        source=json.loads((TABLES/'source_tables.json').read_text())
        for key,spec in source['tables'].items():
            tex=(TABLES/(key+'.tex')).read_text()
            self.assertIn(r'\fontsize{11}{13.2}\selectfont\bfseries',tex)
            self.assertIn(r'\normalfont\fontsize{10}{12}\selectfont',tex)
            self.assertIn(tex_escape(spec['note']),tex)
    def test_combined_HTML_retains_exact_table_order_and_explicit_page_breaks(self):
        manifest=json.loads((TABLES/'manifest.json').read_text())
        order=json.loads((TABLES/'paste_order.json').read_text())
        self.assertEqual(order['order'],list(manifest['tables']))
        self.assertEqual(order['page_break_before'],order['order'][1:])
        continuous=(TABLES/'all_tables.html').read_text()
        paginated=(TABLES/'all_tables_paginated.html').read_text()
        positions=[continuous.index('aria-label="Table '+key+'"') for key in order['order']]
        self.assertEqual(positions,sorted(positions))
        self.assertEqual(paginated.count('page-break-before:always'),len(order['order'])-1)
    def test_clustering_html_has_11pt_bold_centered_caption_and_10pt_cells(self):
        for key in ['S14a','S14b']:
            content=(TABLES/(key+'.html')).read_text()
            caption=re.search(r'<p style="([^"]+)">TABLE '+key,content).group(1)
            for field in ['font-size:11pt','font-weight:bold','text-align:center']:
                self.assertIn(field,caption)
            self.assertIn('font-size:10pt;font-weight:normal',content)
            self.assertNotIn('border-left:',content);self.assertNotIn('border-right:',content)
    def test_exported_clustering_cells_are_identical_to_source_table(self):
        source=json.loads((TABLES/'source_tables.json').read_text())
        for key in ['S14a','S14b']:
            with (TABLES/('Table_'+key+'.csv')).open() as f:rows=list(csv.reader(f))
            self.assertEqual(rows,source['tables'][key]['rows'])
        self.assertIn('frozen method-specific inputs',source['tables']['S14a']['note'])
        self.assertIn('all 47 proteins',source['tables']['S14a']['note'])
    def test_PDF_caption_matches_HTML_and_body_stays_regular(self):
        import fitz
        for key in ['S14a','S14b']:
            with fitz.open(TABLES/(key+'.pdf')) as doc:
                spans=[s for b in doc[0].get_text('dict')['blocks'] if 'lines' in b
                    for line in b['lines'] for s in line['spans'] if s['text'].strip()]
            caption=next(s for s in spans if s['text']=='TABLE '+key)
            self.assertAlmostEqual(caption['size'],11);self.assertIn('Bold',caption['font'])
            cell=next(s for s in spans if s['text']=='B005')
            self.assertAlmostEqual(cell['size'],10);self.assertNotIn('Bold',cell['font'])


if __name__=='__main__':unittest.main()
