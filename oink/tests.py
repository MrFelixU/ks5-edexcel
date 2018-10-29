import unittest
from buildschemes import SchemeLibrary, Scheme, SchemeUnit

class TestBuildSchemes(unittest.TestCase):

    def setUp(self):
        self.lib = SchemeLibrary(config_ini_path = 'test_config/settings.ini')
        self.lib.loadSchemes()

    def test_loadingSchemes(self):
        self.assertEqual(len(self.lib.getSchemeIds()), 2)
        self.assertEqual(len(self.lib.getAllocatedSchemes()), 4)
        self.assertEqual(len(self.lib.getScheme('y12m').getUnit('1pure5').getObjectives()),6)

    def test_addUnits(self):
        s = Scheme('bogus')
        u = s.addUnit('algebra1', "Algebra 1", 9, "learn", "fakename.doc")
        self.assertEqual(len(s.units),1)

    def test_schedulingOfUnits(self):
        sch = self.lib.getScheme('y12m')
        units = sch.getUnitsForHT(3)
        self.assertEqual(len(units),6)
        self.assertEqual(units[2].title, "Vectors (2D)")

    def test_outputHTML(self):
        self.lib.writeHTML()

if __name__ == '__main__':
    unittest.main()
