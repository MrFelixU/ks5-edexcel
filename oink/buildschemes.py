import csv, sys, logging, os, os.path, re, datetime, configparser
from simpletal import simpleTALES, simpleTAL

logging.basicConfig(level = logging.DEBUG, filename="buildschemes.log")
loginfo = lambda x: logging.info(x)
textmatch = lambda x,y: str(x).lower()==str(y).lower()

class UnicodeDictReader(csv.DictReader, object):

    def next(self):
        row = super(UnicodeDictReader, self).next()
        return {unicode(key, 'utf-8'):
                unicode(value, 'utf-8') for key, value in row.iteritems()}

class SchemeLibrary:

    def __init__(self, config_ini_path='settings.ini'):
        config = configparser.ConfigParser()
        config.read(config_ini_path)

        # here's where the init file lives:
        base_path = os.path.dirname(config_ini_path)


        self.config_path = os.path.join(
            base_path,
            config['DEFAULT']['config_folder']
            )

        self.output_path = os.path.join(
            base_path,
            config['DEFAULT']['target_folder']
            )

        # we'll put the Scheme objects in here
        self.schemes = {}

        # which teaching group will use which scheme?
        self.allocated_schemes = []

        # what half-terms are we working with?
        self.half_terms = []

    def loadSchemes(self):
        # open up the file with all the units for each scheme
        _units_path = os.path.join(self.config_path, 'SchemeUnits.csv')
        with open(_units_path) as units_file:
            for unit_row in UnicodeDictReader(units_file):
                sid = str(unit_row['scheme_id']).lower()
                if not sid:
                    logging.warning("No scheme id found in this row: "+str(unit_row))
                    continue
                scheme = self.getScheme(sid)
                if not scheme:
                    scheme = Scheme(sid)
                    self.addScheme(scheme)
                    logging.info("Just added scheme [%s]" % sid)

                # let's check if such a file exists first
                fname = unit_row['file']
                if fname and not os.path.exists(os.path.join(self.output_path, fname)):
                    logging.warning("Could not find a file at %s" % fname)
                    fname = None
                scheme.addUnit(
                    unit_row['unit_id'],
                    half_term = int(unit_row['half_term']),
                    unit_type = unit_row['type'],
                    title = unit_row['unit_title'],
                    file_path = fname
                )
                logging.info("added unit [%s] to scheme [%s]" % (unit_row['unit_id'],sid))
        logging.info("After first part of loading, we have " + str(self.schemes) )

        _objectives_path = os.path.join(self.config_path, 'Objectives.csv')
        with open(_objectives_path) as objectives_file:
            for o_row in UnicodeDictReader(objectives_file):
                sid,uid,obj = [o_row[x] for x in ['scheme_id', 'unit_id', 'objective']]
                if not (sid and uid and obj):
                    continue
                # let's not bother if we're not actually building this scheme
                if not self.getScheme(sid):
                    continue
                s = self.getScheme(sid.lower())
                u = s.getUnit(uid.lower())
                u.appendObjective(obj)
                logging.debug("Adding objective [%s] to scheme [%s] and unit [%s]" % (obj,sid,uid))

        _groups_path = os.path.join(self.config_path, 'SetsSchemes.csv')
        with open(_groups_path) as groups_file:
            for entry in UnicodeDictReader(groups_file):
                grp,sid = entry['teaching_group'], entry['scheme_id']
                if not (grp and sid):
                    continue
                scheme = self.getScheme(sid)
                if not scheme:
                    raise ValueError("Scheme [%s] is not known" % sid)
                self.allocated_schemes.append( AllocatedScheme(grp,scheme) )

        _ht_path = os.path.join(self.config_path,'HalfTerms.csv')
        with open(_ht_path) as ht_file:
            for ht in UnicodeDictReader(ht_file):
                num = int(ht['half_term'])
                title = ht['title']
                long_title = ht['long_title']
                code = ht['code']
                weeks = int(ht['weeks'])
                self.half_terms.append( {
                    'num':num,
                    'long_title' : long_title,
                    'code' : code,
                    'weeks' : weeks
                })

    def addScheme(self, scheme):
        self.schemes[scheme.id] = scheme

    def getScheme(self, id):
        return self.schemes.get(id, None)

    def getSchemeIds(self):
        """Returns a list of all known scheme ids"""
        return self.schemes.keys()

    def getAllocatedSchemes(self):
        return self.allocated_schemes

    def writeHTML(self):
        context = simpleTALES.Context(allowPythonPath = 1)
        context.addGlobal('library', self)
        template_file = open("templates/index.html")
        template = simpleTAL.compileHTMLTemplate(template_file)
        template_file.close()
        out_file = open(os.path.join(self.output_path, "index.html"), 'w')
        template.expand(context, out_file, outputEncoding="utf-8")
        out_file.close()

        # make a separate details file for each allocated scheme
        for ascheme in self.getAllocatedSchemes():
            context.addGlobal('thisascheme', ascheme)
            template_file = open("templates/details.html")
            template = simpleTAL.compileHTMLTemplate(template_file)
            template_file.close()
            out_file = open(os.path.join(self.output_path, ascheme.getDetailsFileName()), 'w')
            template.expand(context, out_file, outputEncoding="utf-8")
            out_file.close()

class Scheme:

    def __init__(self, id):

        # how we refer to this scheme
        self.id = id

        # the actual units as a dictionary { id : unit object }
        self.units = []

    def getUnit(self, id):
        matches = [u for u in self.units if textmatch(u.id, id)]
        if len(matches)==1:
            return matches[0]
        elif len(matches)>1:
            raise ValueError("We have a duplicate unit with id %s!" % str(id))
        else:
            logging.error("Was looking for unit id [%s]" % str(id))
            for u in self.units:
                logging.error("I have %s" % u.id)
            raise ValueError("Could not find unit %s!" % str(id))

    def getUnitsForHT(self, htnum):
        matches = [u for u in self.units if u.half_term == htnum]
        return matches

    def addUnit(self, id, title, half_term, unit_type, file_path):
        # check first we don't already have one
        matches = [u for u in self.units if textmatch(u.id, id)]
        if len(matches) > 0:
            raise ValueError("We already have unit with the id '%s'" % str(id))
        self.units.append(SchemeUnit(id, title, half_term, unit_type, file_path))

class AllocatedScheme:

    def __init__(self, teaching_group = None, scheme = None):
        self.scheme = scheme
        self.teaching_group = teaching_group

    def getTitle(self):
        return self.teaching_group

    def getDetailsFileName(self):
        return "scheme-%s.html" % self.teaching_group.replace(" ","-").lower()

class SchemeUnit:

    def __init__(self, id, title='', half_term = 0, unit_type='', file_path='',
                 objectives=[]):
        self.id = id
        self.title = title
        self.half_term = half_term
        self.unit_type = unit_type
        self.file_path = file_path

        # the main thing
        self._objectives = objectives[:]

        # we'll try to look for resources related to each unit to list
        # on the scheme details page
        self.resource_links = []

    def appendObjective(self, obj):
        self._objectives.append(obj)
        logging.debug("Just added [%s] to %s.  Length is now %d" % (obj,self.id,len(self._objectives)))

    def getObjectives(self):
        logging.debug("reporting back [%s], [%d]" % (self.id, len(self._objectives)))
        return self._objectives[:]

if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise Exception("I was expecting just one argument with the path of the settings file")
    lib = SchemeLibrary(config_ini_path = sys.argv[1])
    lib.loadSchemes()
    lib.writeHTML()
