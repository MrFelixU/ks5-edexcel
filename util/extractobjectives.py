# This program looks through a text file containing the Edexcel scheme of work
# and tries to pull out all the learning objectives

import sys

with open(sys.argv[1],"rt") as srcfile, open(sys.argv[2], "wt") as outfile:
    inob = False
    for line in srcfile.readlines():
        if (not inob) and line.count(", students should:"):
            inob = True
            continue
        if inob:
            if line.count("TEACHING POINTS"):
                inob = False
                outfile.write("\n")
            else:
                line = line.strip()
                if line.endswith(";") or line.endswith("."):
                    line = line[:-1]
                outfile.write(line.strip() + "\n")
