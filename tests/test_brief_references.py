"""Keep the brief linked to actual full-paper pages as pagination changes."""
import importlib.util
from pathlib import Path
import unittest

spec=importlib.util.spec_from_file_location('brief',Path(__file__).resolve().parents[1]/'tools/build_research_brief.py')
brief=importlib.util.module_from_spec(spec);spec.loader.exec_module(brief)

class BriefReferences(unittest.TestCase):
    def test_continuations_and_page_shift(self):
        q=dict(id='colors',preprint_sections=['4.1','4.4'],section_label='§ 4.1, 4.4')
        sections=dict(sections=[dict(number='4.1',page=27),dict(number='4.4',page=30),dict(number='4.4',page=31),dict(number='4.4',page=32)])
        self.assertEqual(brief.reference(q,sections),('§ 4.1, 4.4; pp. 27, 30–32',27))
        for entry in sections['sections']:entry['page']+=4
        self.assertEqual(brief.reference(q,sections),('§ 4.1, 4.4; pp. 31, 34–36',31))

    def test_missing_section_is_rejected(self):
        with self.assertRaisesRegex(ValueError,'missing full-preprint section'):
            brief.reference(dict(id='missing',preprint_sections=['4.9'],section_label='§ 4.9'),dict(sections=[]))

    def test_companion_pages_require_unique_evidence_text(self):
        rows = [{'number': 'camera', 'text_anchor': 'a fitted camera', 'page': 2}]
        sections = {'page_count': 2, 'sections': rows}
        self.assertEqual(brief.check_pagination(['Title', 'a fitted\ncamera'], sections), [])
        self.assertTrue(brief.check_pagination(['a fitted camera', 'Title'], sections))
        self.assertTrue(brief.check_pagination(['a fitted camera', 'a fitted camera'], sections))
        self.assertTrue(brief.check_pagination(['Title'], sections))

    def test_faq_only_reference(self):
        self.assertEqual(brief.reference(dict(reference='FAQ § 11')),('FAQ § 11',None))

if __name__=='__main__':unittest.main()
