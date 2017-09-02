import csv, sys, logging, os, os.path, re, datetime
from simpletal import simpleTALES, simpleTAL

logging.basicConfig(level = logging.DEBUG, filename="buildschemes.log")
loginfo = lambda x: logging.info(x)
textmatch = lambda x,y: str(x).lower()==str(y).lower()

class SchemeLibrary:

    def __init__(self, config_path = "config", output_path = 'scheme'):
        self.config_path = config_path
        self.output_path = output_path

        # we'll put the Scheme objects in here
        self.schemes = {}

        # which teaching group will use which scheme?
        self.allocated_schemes = []

        # what half-terms are we working with?
        self.half_terms = []

    def loadSchemes(self):
        # open up the file with all the units for each scheme
        _units_path = os.path.join(self.config_path, 'SchemeUnits.csv')
        for unit_row in csv.DictReader(open(_units_path)):
            sid = str(unit_row['scheme_id']).lower()
            if not sid:
                logging.warn("No scheme id found in this row: "+str(unit_row))
                continue
            scheme = self.getScheme(sid)
            if not scheme:
                scheme = Scheme(sid)
                self.addScheme(scheme)

            # let's check if such a file exists first
            fname = unit_row['file']
            if fname and not os.path.exists(os.path.join(self.output_path, fname)):
                logging.warn("Could not find a file at %s" % fname)
                fname = None
            scheme.addUnit(
                unit_row['unit_id'],
                half_term = int(unit_row['half_term']),
                unit_type = unit_row['type'],
                title = unit_row['unit_title'],
                file_path = fname
            )
        logging.info("After first part of loading, we have " + str(self.schemes) )

        _objectives_path = os.path.join(self.config_path, 'Objectives.csv')
        for o_row in csv.DictReader(open(_objectives_path)):
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
        for entry in csv.DictReader(open(_groups_path)):
            grp,sid = entry['teaching_group'], entry['scheme_id']
            if not (grp and sid):
                continue
            scheme = self.getScheme(sid)
            if not scheme:
                raise "Scheme [%s] is not known" % sid
            self.allocated_schemes.append( AllocatedScheme(grp,scheme) )

        _ht_path = os.path.join(self.config_path,'HalfTerms.csv')
        for ht in csv.DictReader(open(_ht_path)):
            num = int(ht['half_term'])
            title = ht['title']
            long_title = ht['long_title']
            code = ht['code']
            (d,m,y) = [int(x) for x in ht['start_date'].split('/')]
            start_date = datetime.date(y,m,d)
            weeks = int(ht['weeks'])
            self.half_terms.append( {
                'num':num,
                'long_title' : long_title,
                'code' : code,
                'start_date' : start_date,
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
        template = simpleTAL.compileHTMLTemplate(template_file, inputEncoding="utf-8")
        template_file.close()
        out_file = open(os.path.join(self.output_path, "index.html"), 'w')
        template.expand(context, out_file, outputEncoding="utf-8")
        out_file.close()

        # make a separate details file for each allocated scheme
        for ascheme in self.getAllocatedSchemes():
            context.addGlobal('thisascheme', ascheme)
            template_file = open("templates/details.html")
            template = simpleTAL.compileHTMLTemplate(template_file, inputEncoding="utf-8")
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
        else:
            raise "We have a duplicate unit with id %s!" % str(id)

    def getUnitsForHT(self, htnum):
        matches = [u for u in self.units if u.half_term == htnum]
        return matches

    def addUnit(self, id, title, half_term, unit_type, file_path):
        # check first we don't already have one
        matches = [u for u in self.units if textmatch(u.id, id)]
        if len(matches) > 0:
            raise "We already have unit with the id '%s'" % str(id)
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
    lib = SchemeLibrary()
    lib.loadSchemes()
    lib.writeHTML()


"""
================= THE ORIGINAL CODE FOLLOWS =================
"""


def __oldmain__():
    # load each scheme, i.e. which units are to be taught in order
    schemes_by_year_tier = findUnitsForSchemes("config/SchemeUnits.csv",
                                               "config/Assessments.csv",
                                               "config/Objectives.csv",
                                               "config/Keywords.csv")
    loginfo(str(schemes_by_year_tier.keys()))

    # find out which scheme is needed by each teaching set
    sets_to_schemes = findSchemeForEachSet("config/SetsSchemes.csv")
    loginfo(str(sets_to_schemes))

    # for each teaching set, produce a separate file with teaching units
    writeSchemes(schemes = schemes_by_year_tier,
                 sets_to_schemes = sets_to_schemes,
                 )



# which units are we supposed to teach in which order?
def findUnitsForSchemes(units_file = None,
                        questions_file = None,
                        objectives_file = None,
                        kw_file = None):

    # look for files in the textbooks directoryand get them ready to
    # refer to later
    textbook_links = findTextbookLinks()

    # grab all the que by que detail for assessments
    ass_questions =  [i for i in
                      csv.DictReader(open(questions_file))
                      if i.get('q',False)]

    # pick up individual objectives and keywords for each unit
    all_los = [lo_row for lo_row in csv.DictReader(open(objectives_file))]
    all_kws = [kw_row for kw_row in csv.DictReader(open(kw_file))]

    schemes = {}
    for entry in csv.DictReader(open(units_file)):
        sid = str(entry['scheme_id']).lower()
        uid = entry['unit_id']


        tb = textbook_links.get(str(sid+uid).lower(),[])
        if tb:
            weblink = "http://essentials.cambridge.org/mathematics/%s/%s"

        testfile = textmatch(entry['type'],'assess') and entry.get('file',None)

        test_questions = []
        if textmatch(entry['type'],'assess'):
            test_questions = [dic for dic in ass_questions if
                              textmatch(dic['scheme_id'], sid) and
                              textmatch(dic['unit_id'],uid)]


        units = schemes.get(sid, [])
        units.append(
            {
                'id' : uid,
                'title' : entry['unit_title'],
                'ht' : entry['half_term'],
                'type' : entry['type'],
                'objectives' : [
                    o['objective'] for o in all_los
                    if textmatch(o['scheme_id'], sid) and
                    textmatch(o['unit_id'], uid) ],
                'keywords' : [
                    k['keyword'] for k in all_kws
                    if textmatch(k['scheme_id'], sid) and
                    textmatch(k['unit_id'], uid) ],
                'textbook_files' : tb,
                'testfile' : testfile,
                'testquestions' : test_questions,
                }
            )
        schemes[sid] = units
    return schemes


def findTextbookLinks(directory="scheme/textbooks"):
    """Search through folders for relevant textbook pages.

    Returns:
    [ (unit_and_section_code, path_to_file_from_txtbook_dir), ...... ]
    """
    tb_links_by_siduid = {}
    pat = re.compile(
        r"^cemks3_([a-z0-9]+)_tr_([a-z0-9]+)[_\.]([0-9]).*_it\.pdf$",
        re.IGNORECASE
        )
    urlbase = "http://essentials.cambridge.org/mathematics"
    for (path, dirnames, filenames) in os.walk(directory):
        filenames.sort()
        for fname in filenames:
            m = pat.match(fname)
            if m:
                loginfo("got a match in %s :-] %s" % (path, str(m.groups())))
                sid, uid, sect = m.group(1), m.group(2), m.group(3)
                key = str(sid+uid).lower()
                links = tb_links_by_siduid.get(key, [])
                tb_entry = {
                    'path' : os.path.relpath(os.path.join(path,m.group(0)),"scheme"),
                    'title' : "%s.%s" % (uid.upper(),m.group(3)),
                    'url' : "/".join([urlbase, m.group(1), m.group(2), m.group(3)]),
                    }
                links.append(tb_entry)
                tb_links_by_siduid[key] = links
    loginfo(str(tb_links_by_siduid))
    return tb_links_by_siduid



def findSchemeForEachSet(SetsSchemesFileName):
    """Look up the config file and produce a dictionary whose keys are
    teaching sets and whose values are scheme ids.

    output is like this:
    {
     "Year 7 Set 1" : '8c',
     }

     to mean that year 7 set 1 will be folliwng the "8c" scheme
    """
    sets_to_schemes = {}
    for entry in csv.DictReader(open(SetsSchemesFileName)):
        sets_to_schemes[ entry['teaching_group'] ] = entry['scheme_id']
    return sets_to_schemes



def writeSchemes(schemes = {},
                 sets_to_schemes = {},
                 questions = {}
                 ):
    """Produce a separate HTML file for each teaching set with details of
    units, objectives and links"""

    file_titles_names = [
        (schemetitle , "scheme-%s.html" % schemetitle.replace(" ","-").lower())
        for schemetitle in sets_to_schemes.keys()
        ]
    file_titles_names.sort()

    # step through each teaching class
    for (scheme_title, file_name) in file_titles_names:
        sid = sets_to_schemes[scheme_title]
        units = schemes.get(sid, None)
        if units:
            loginfo("Found scheme %s for %s" % (sid, scheme_title))
            writeScheme(
                units = units,
                scheme_title = scheme_title,
                out_file_name = os.path.join(".", "scheme", file_name),
                all_file_titles_names = file_titles_names,
                sid = sid
                )
        else:
            loginfo("No scheme found for %s" % scheme_title)
    writeIndex(all_file_titles_names = file_titles_names, sets_to_schemes = sets_to_schemes)


def writeIndex(all_file_titles_names = [], sets_to_schemes = {}):
    """Just make an index.html file which lists all the schemes available"""

    # all the variables for the template will go in here
    glob = {}

    glob['other_schemes'] = [ {'title' : t,
                               'filename' : f,
                               'cardsname' : f.replace("scheme-", "cards-"),
                               'bookletname' : f.replace("scheme-", "booklet-"),
                               'selected' : '',
                               'sid' : sets_to_schemes.get( t , "" ), }
                              for (t,f) in all_file_titles_names]

    context = simpleTALES.Context(allowPythonPath = 1)
    for (k, v) in glob.items():
        context.addGlobal(k,v)
    template_file = open("templates/index.html")
    template = simpleTAL.compileHTMLTemplate(template_file)
    template_file.close()
    out_file = open(os.path.join(".", "scheme", "index.html"), 'w')
    template.expand(context, out_file, outputEncoding="utf-8")
    out_file.close()




def writeScheme(units = [],
                scheme_title = None,
                out_file_name = None,
                all_file_titles_names = [],
                sid = None
                ):
    """Produce the actual HTML file for each set, using the template
    and units given"""

    # all the variables for the template will go in here
    glob = {}

    glob['scheme_title'] = scheme_title
    glob['other_schemes'] = [ {'title' : t,
                               'filename' : f,
                               'selected' : t==scheme_title and 'selected' or '' }
                              for (t,f) in all_file_titles_names]

    half_terms = []
    for ht in csv.DictReader(open("config/HalfTerms.csv")):
        half_terms.append(
            { 'number': ht['half_term'],
              'title' : ht['long_title'],
              'weeks' : ht['weeks'],
              'code' : ht['code'],
              'units' : [u for u in units if str(u['ht']) == ht['half_term'] ],
              }
            )

    glob['half_terms']= half_terms


    context = simpleTALES.Context(allowPythonPath = 1)
    for (k, v) in glob.items():
        context.addGlobal(k,v)

    template_file = open("templates/details.html")
    template = simpleTAL.compileHTMLTemplate(template_file)
    template_file.close()
    out_file = open(out_file_name, 'w')
    template.expand(context, out_file, outputEncoding="utf-8")
    out_file.close()

    template_file = open("templates/cards.html")
    template = simpleTAL.compileHTMLTemplate(template_file)
    template_file.close()
    cards_filename = out_file_name.replace("scheme-", "cards-")
    cards_file = open(cards_filename, 'w')
    template.expand(context, cards_file , outputEncoding="utf-8")
    cards_file.close()

    template_file = open("templates/booklet.html")
    template = simpleTAL.compileHTMLTemplate(template_file)
    template_file.close()
    cards_filename = out_file_name.replace("scheme-", "booklet-")
    cards_file = open(cards_filename, 'w')
    template.expand(context, cards_file , outputEncoding="utf-8")
    cards_file.close()


#__main__()
