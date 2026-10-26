import tempfile

from django.test import SimpleTestCase

from shakespeare.legacy_sql import read_tables

DUMP = r"""
-- comment with INSERT-ish text
CREATE TABLE `Works` (`WorkID` varchar(50));
INSERT INTO `Works` (`WorkID`, `Title`, `Date`, `Notes`) VALUES
('hamlet', 'Hamlet''s; (tragedy)', 1600, NULL),
('allswell', 'Line one\n[p]line \'two\'\\', -3, '');
INSERT INTO `UserAccounts` (`UserID`, `EmailAddress`) VALUES
(1, 'someone@example.com');
INSERT INTO `Works` (`WorkID`, `Title`, `Date`, `Notes`) VALUES ('sonnets', 'Sonnets', 1609, 'x');
"""


class ReadTablesTests(SimpleTestCase):
    def test_parses_inserts_and_skips_other_tables(self):
        with tempfile.NamedTemporaryFile("w", suffix=".sql", encoding="latin-1") as f:
            f.write(DUMP)
            f.flush()
            data = read_tables(f.name, ["Works"])

        self.assertEqual(list(data), ["Works"])
        self.assertEqual(
            data["Works"],
            [
                {"WorkID": "hamlet", "Title": "Hamlet's; (tragedy)", "Date": 1600, "Notes": None},
                {"WorkID": "allswell", "Title": "Line one\n[p]line 'two'\\", "Date": -3, "Notes": ""},
                {"WorkID": "sonnets", "Title": "Sonnets", "Date": 1609, "Notes": "x"},
            ],
        )
