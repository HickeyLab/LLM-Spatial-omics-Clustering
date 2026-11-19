"""Protect dedicated donor admission and the legacy verifier dispatch."""
import copy
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest import mock

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
import verify_donor47_figures as donor


class DonorReceiptTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name);self.data=self.root/donor.DATA;self.data.mkdir(parents=True)
        self.folder=self.root/'figures/publication';self.folder.mkdir(parents=True)
        self.files={}
        for name in sorted(set.union(*donor.REQUIRED_SOURCES.values())):
            path=self.data/name;path.write_text('fixture\n')
            self.files[name]={'sha256':donor.digest(path)}
        for name in ['scripts/render_donor47_figures.py','scripts/publication_figure_design.py']:
            path=self.root/name;path.parent.mkdir(parents=True,exist_ok=True);path.write_text('fixture source\n')
        self.manifest={'clustering_ready':True,'publication_ready':False,'annotation_requests_terminal':False,'files':self.files}
        self.refresh('S12')
    def refresh(self,key):
        path=self.data/'manifest.json';path.write_text(json.dumps(self.manifest))
        self.receipt={'figure':'Figure_'+key,'inputs':{str(donor.DATA/'manifest.json'):donor.digest(path)},
            'files':{'Figure_'+key+ext:{} for ext in ['.svg','.pdf','.png','.tiff']}}
        for name in donor.REQUIRED_SOURCES[key]:self.receipt['inputs'][str(donor.DATA/name)]=self.files[name]['sha256']
        self.rendered={'source_manifest':str(donor.DATA/'manifest.json'),'source_manifest_sha256':donor.digest(path),'figures':{key:self.receipt},'new_calls_or_fits':0,
            'renderer_sha256':donor.digest(self.root/'scripts/render_donor47_figures.py'),
            'shared_style_sha256':donor.digest(self.root/'scripts/publication_figure_design.py')}
        self.write_rendered()
    def write_rendered(self):
        (self.folder/'donor47_figure_manifest.json').write_text(json.dumps(self.rendered))
    def test_clustering_only_bank_admits_S12_without_legacy_panel_map(self):
        result=donor.admit_donor_receipt('S12',self.folder,self.receipt,root=self.root)
        self.assertEqual(result['panel_letters'],'ABC')
        self.assertEqual(result['route'],'dedicated_donor47_receipt')
    def test_annotation_figures_reject_nonterminal_bank(self):
        for key in ['5','S13']:
            self.refresh(key)
            with self.assertRaises(ValueError):donor.admit_donor_receipt(key,self.folder,self.receipt,root=self.root)
    def test_all_annotation_panels_use_dedicated_terminal_receipts(self):
        self.manifest.update(publication_ready=True,annotation_requests_terminal=True)
        for key in ['5','S13']:
            self.refresh(key)
            self.assertEqual(donor.admit_donor_receipt(key,self.folder,self.receipt,root=self.root)['panel_letters'],'ABCD')
    def test_changed_source_or_receipt_is_rejected(self):
        original=copy.deepcopy(self.receipt);self.receipt['inputs']['extra.csv']='0'*64
        with self.assertRaises(ValueError):donor.admit_donor_receipt('S12',self.folder,self.receipt,root=self.root)
        self.receipt=original
        (self.data/'clustering_donor_metrics.csv').write_text('changed\n')
        with self.assertRaises(ValueError):donor.admit_donor_receipt('S12',self.folder,self.receipt,root=self.root)
    def test_changed_renderer_is_rejected(self):
        (self.root/'scripts/render_donor47_figures.py').write_text('changed source\n')
        with self.assertRaises(ValueError):donor.admit_donor_receipt('S12',self.folder,self.receipt,root=self.root)
    def test_private_absolute_source_manifest_is_rejected(self):
        self.rendered['source_manifest']=str(self.data/'manifest.json');self.write_rendered()
        with self.assertRaises(ValueError):donor.admit_donor_receipt('S12',self.folder,self.receipt,root=self.root)


class LegacyDispatchTests(unittest.TestCase):
    def test_actual_S12_routes_before_legacy_PANELS_lookup(self):
        import verify_publication_figures as legacy
        self.assertNotIn('S12',legacy.PANELS)
        with mock.patch.object(legacy,'ORDER',['S12']):
            result=legacy.verify_native(ROOT/'figures/publication',figure_ids=['S12'])
        self.assertEqual(result[0]['panel_letters'],'ABC')
        self.assertEqual(result[0]['donor_verification']['route'],'dedicated_donor47_receipt')


if __name__=='__main__':unittest.main()
