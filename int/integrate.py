import os, sys, re
import os.path
import xml.dom.minidom as md

def grabSectionPages():
    f = open('contents.html')
    doc = md.parse(f)
    all_links = doc.getElementsByTagName('a')
    topic_links = [l for l in all_links
                   if l.getAttribute('href').find("course/view.php?id=9&section")>-1]

    furls = open('sectionurls.txt', 'w')

    furls.writelines("\n".join([l.getAttribute('href') for l in topic_links]))

    f.close()
    furls.close()


def _cleanSectionName(thename):
    return re.sub("""[\s][\s]+""",
                  " ",
                  thename
    ).replace(":",",")

    
def makeLists():
    fnames = [n for n in os.listdir(".") if
              n.startswith("section") and n.endswith(".html")]
    for fname in fnames:
        doc = md.parse(fname)

        # try to find a section name
        h3s = doc.getElementsByTagName('h3')
        for h3 in h3s:
            if h3.getAttribute("class") == "sectionname":
                sname = _cleanSectionName(h3.firstChild.data)
                os.mkdir(sname)
                linksfile = open(os.path.join(sname, "pdflinks.txt"),'w')

                for anchorel in h3.parentNode.getElementsByTagName('a'):
                    if anchorel.getAttribute("href").find("/mod/resource/")>-1:
                        linksfile.write(anchorel.getAttribute("href"))
                        linksfile.write("&redirect=1")
                        linksfile.write("\n")
                linksfile.close()


                
def renameFiles():
    fnames = [n for n in os.listdir(".") if
              n.startswith("section") and n.endswith(".html")]
    for fname in fnames:
        doc = md.parse(fname)

        # try to find a section name
        h3s = doc.getElementsByTagName('h3')
        for h3 in h3s:
            if h3.getAttribute("class") == "sectionname":
                sname = _cleanSectionName(h3.firstChild.data)

                for anchorel in h3.parentNode.getElementsByTagName('a'):
                    if anchorel.getAttribute("href").find("/mod/resource/")>-1:
                        namespan = anchorel.getElementsByTagName('span')[0].firstChild.data
                        cleanname = re.sub("\\W", "",namespan) + ".pdf"

                        idstring = re.search("(id=[0-9]+)",
                                             anchorel.getAttribute("href")).group(1)
                        oldfname = "view.php?%s&redirect=1" % idstring
                        print "Trying to replace [%s] with [%s]" % (oldfname, cleanname)
                        os.rename(os.path.join(sname,oldfname),
                                  os.path.join(sname,cleanname)
                            )


    
