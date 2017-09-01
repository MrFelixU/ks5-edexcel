import unittest
from buildschemes import SchemeLibrary, Scheme, SchemeUnit

class TestBuildSchemes(unittest.TestCase):

    def setUp(self):
        pass

    def test_loadingSchemes(self):
        lib = SchemeLibrary(config_path = 'test_config')
        lib.loadSchemes()
        self.assertEqual(len(lib.getSchemeIds()), 2)

    def test_addUnits(self):
        s = Scheme('bogus')
        u = s.addUnit('algebra1', "Algebra 1", 9, "learn", "fakename.doc")
        self.assertEqual(len(s.units),1)

if __name__ == '__main__':
    unittest.main()
