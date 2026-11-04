"""Contributor names survive a real projection from both historical and current libraries."""
from pathlib import Path
import hashlib
import tempfile
import unittest

from brick_blueprint.project import project


class LibraryEncodingTests(unittest.TestCase):
    def test_credits_and_reference_names_use_library_encoding(self):
        # The UTF-8 encoding of this author's initial contains 0x85, which would
        # split an author comment into a spurious DAT geometry record in Latin-1.
        cases = [
            ("\u00c5. R\u00f6der", "utf-8", "fa\u00e7ade.dat"),
            ("O\u2019Neil", "cp1252", "fa\u00e7ade.dat"),
        ]
        for author, encoding, name in cases:
            with self.subTest(encoding=encoding), tempfile.TemporaryDirectory() as temp:
                root = Path(temp)
                parts = root / "parts"
                parts.mkdir()
                (root / "p").mkdir()
                header = f"0 Part header\n0 Author: {author}\n"
                config = header + "0 !COLOUR Red CODE 4 VALUE #ff0000 EDGE #333333\n"
                raw = (header + "0 BFC CERTIFY CCW\n3 16 0 0 0 20 0 0 0 0 20\n").encode(encoding)
                (parts / name).write_bytes(raw)
                (root / "LDConfig.ldr").write_bytes(config.encode(encoding))
                instance = "1 16 0 0 0 1 0 0 0 1 0 0 0 1 "
                (parts / "parent.dat").write_bytes((header + instance + name + "\n").encode(encoding))
                model = root / "demo.ldr"
                model.write_text(instance.replace("1 16 ", "1 4 ", 1) + "parent.dat\n")
                result = project(model, root, root / "scene")
                child = next(row for row in result["dependencies"] if row["file"] == "parts/" + name)
                self.assertEqual(child["authors"], ["Author: " + author])
                self.assertEqual(child["sha256"], hashlib.sha256(raw).hexdigest())
                self.assertEqual(result["library_config"]["authors"], ["Author: " + author])
