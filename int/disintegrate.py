import os, os.path, re, sys
import xml.dom.minidom as md
import logging
import requests
import tidylib

logging.basicConfig(filename='disintegrate.log',level=logging.DEBUG)

URLBASE = "https://2017.integralmaths.org"
BASEDIR = "./resources"
COURSES = (26, 27)


def cleanedHtml(messy_html):
    return tidylib.tidy_document(
        messy_html, options = {'output-xhtml':True}
    )[0]

def _cleanSectionName(thename):
    return re.sub("""[\s][\s]+""",
                  " ",
                  thename
    ).replace(":",",").strip()



def getIn():
    s = requests.Session()
    r = s.post(URLBASE+"/login/index.php",
               data = {'username' : "fmsp-Allerton959",
                       'password' : "Give101%",
               }
    )
    
    # now let's grab the "courses" we want

    for courseid in COURSES:
        # download the course overview page - this should have a nice
        # listing of all the sections in its menu
        course_url = URLBASE+"/course/view.php?id="+str(courseid)
        r = s.get(course_url)
        logging.debug("Tried to fetch course overview page: "+str(r.url))

        logging.debug("Trying to parse minidom")
        doc = md.parseString(cleanedHtml(r.text))

        logging.debug("Looking for sections")
        section_urls = []
        for el in doc.getElementsByTagName("a"):
            href = el.getAttribute("href")

            # check if this href points to a section, and don't
            # duplicate
            if href.startswith(course_url) and href.find("section=") >= 0:
                if href not in section_urls:
                    section_urls.append(href) 
        logging.debug(
            "The section urls we have are: " + "; ".join(section_urls)
        )
                    
        # now go to each section separately and look for "resource" links
        for sec_url in section_urls:
            logging.debug("Looking up section: "+sec_url)
            r = s.get(sec_url)
            doc = md.parseString(cleanedHtml(r.text))

            # let's grab the section name and make a directory with
            # that (cleaned up) name

            h3s = doc.getElementsByTagName('h3')
            for h3 in h3s:
                if h3.getAttribute("class") == "sectionname":
                    # clean up the name to make a directory
                    sname = _cleanSectionName(h3.firstChild.data)
                    os.makedirs(
                        os.path.join(BASEDIR,str(courseid),sname),
                        exist_ok = True)

                    # for each link that looks like a resource, attempt to
                    # follow a redirect link, but first work out what name the
                    # pdf file should have

                    for a in h3.parentNode.getElementsByTagName('a'):
                        href = a.getAttribute("href")
                        if href.find("/mod/resource/")>-1:
                            namespan = a.getElementsByTagName('span')[0].firstChild.data
                            cleanname = re.sub("\\W", "",namespan) + ".pdf"
                            outfile = open(
                                os.path.join(BASEDIR,str(courseid),sname,cleanname),
                                "wb"
                                )
                            logging.debug("Trying to get %s into %s" % (href, cleanname))
                            r = s.get(href+"&redirect=1")
                            outfile.write(r.content)
                            outfile.close()
                            

                            
                            



            
            



