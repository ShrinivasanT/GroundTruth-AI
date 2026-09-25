"""Tests for DoclingParser._extract_references and Phase 2 changes."""

import unittest

from app.parsers.docling_parser import DoclingParser


class TestExtractReferences(unittest.TestCase):
    """Verify the regex-based text-reference extraction."""

    def test_figure_references(self):
        text = "As shown in Fig. 1 and Figure 3, the results are significant."
        refs = DoclingParser._extract_references(text)
        self.assertIn("Fig. 1", refs)
        self.assertIn("Fig. 3", refs)

    def test_table_references(self):
        text = "Table 2 summarizes the findings. See also Tab. 5 for details."
        refs = DoclingParser._extract_references(text)
        self.assertIn("Table 2", refs)
        self.assertIn("Table 5", refs)

    def test_mixed_references(self):
        text = "Fig. 2 and Table 1 illustrate the relationship between variables."
        refs = DoclingParser._extract_references(text)
        self.assertEqual(refs, ["Fig. 2", "Table 1"])

    def test_no_references(self):
        text = "This paragraph contains no figure or table references."
        refs = DoclingParser._extract_references(text)
        self.assertEqual(refs, [])

    def test_case_insensitive(self):
        text = "fig. 4 and TABLE 6 are referenced."
        refs = DoclingParser._extract_references(text)
        self.assertIn("Fig. 4", refs)
        self.assertIn("Table 6", refs)

    def test_deduplication(self):
        text = "Fig. 1 is important. As seen in Fig. 1 again."
        refs = DoclingParser._extract_references(text)
        self.assertEqual(refs.count("Fig. 1"), 1)

    def test_figure_no_dot(self):
        text = "Figure 7 shows the architecture."
        refs = DoclingParser._extract_references(text)
        self.assertIn("Fig. 7", refs)


if __name__ == "__main__":
    unittest.main()
