# This script aims to create Anki cards for all the SAQ questions / answers in my textbook

# There will be multiple stages

import pdftotext
import sys, re
from pathlib import Path
from typing import List, Tuple

if len(sys.argv) < 2:
    sys.exit(f"Usage: {sys.argv[1]} file.pdf -debug")

pdfPath = Path(sys.argv[1])
debug = False
if sys.argv[2] == "-debug":
    debug = True

# Combine all pages into one string
# Add entries to our pageNo list for each instance of "SAQ "
# Note: had to make this far more resource intensive due to duplicate instances
# of "\nSAQ $SAQ_no". New method uses set() to determine number of unique instances.
# it's hacky, and there's probably a better way.

def combine_pages(pdf: pdftotext.PDF) -> Tuple[str, List[int]]:
    wholebook = ""
    pageNos = []
    SAQregex = r"\nSAQ\s\d+"
    for pageNo, page in enumerate(pdf):

        wholebook += page
        matches = re.finditer(SAQregex, page, re.MULTILINE)
        SAQmatches = [match.group() for match in matches]
        if len(SAQmatches) == 0:
            continue
        unique_SAQs = set(SAQmatches)
        [pageNos.append(pageNo - 3) for SAQ in unique_SAQs]
        if debug:
            print(f"found {len(unique_SAQs)} SAQ(s) on page {pageNo - 3} (total: {len(pageNos)})")

    if debug:
        with open(f"{pdfPath.stem} raw.txt", "w") as f:
            f.write(wholebook)
    return wholebook, pageNos

# We're going clean up page boundaries using regexes that match to the surroundings of the end of page character \x0c

# These end of page blocks have come in two forms:
# `\n\n{$page_no}\n\n\x0c${unit_name}\n`
# `\n\n{$page_no}\n\n\x0c{$section_no}\n\n{$section_name}`

# We attempted to use a single regex (r"\n+\d+\n\n[\s\S]*?(\n(?=SAQ)|(?=\n\n))") to find both cases, however
# the formatting is such that if an SAQ began immediately on a new page, it would have been included in the match
# We are using instances of "SAQ" to extract the questions, so we need to leave these intact
# Previous single pass attempt regex = r"\n+\d+\n\n[\s\S]*?(\n(?=SAQ)|(?=\n\n))"
# Finding a series of match + substitutions that results in perfectly formatted Question + Answer blocks was very difficult
# What I have is an incomplete solution

def remove_page_boundaries(wholebook: str) -> str:

    # I couldn't find a single regex that satisfied this edge case, so we went with two passes.

    # First use a regex which makes sure not to include "SAQ" in the match, and substitutes with an empty string:
    regex1 = r"$\n+\d{1,3}$\n^$\n(?=\x0c)\x0c(?:.*\n)(?=SAQ)"
    wholebook = re.sub(regex1, '', wholebook, 0, re.MULTILINE)

    # Next pass we are comfortable the match won't interfere with Q + A extract, and we substitute with a newline:
    regex2 = r"$\n+\d{1,3}$\n^$\n(?=\x0c)\x0c(?:.*\n)\n"
    wholebook = re.sub(regex2, "\n", wholebook, 0, re.MULTILINE)

    if debug:
        with open(f"{pdfPath.stem} filtered.txt", "w") as f:
            f.write(wholebook)
    
    return wholebook

def remove_interfering_portions(wholebook: str) -> str:
    # This pass is necessary to replace any notes in the margin that are incident on the same line as an SAQ header.
    # These interfere with question parsing in later passes. We substitute these interfering notes with a new line

    regex3 = r"(SAQ \d{1,2}\n)(\w[\s\S]*?\n\n)"
    wholebook = re.sub(regex3, r"\1\n", wholebook, 0, re.MULTILINE)

    # This pass is necessary to replace "Table $no Answer to SAQ $no", which was interfering with cards.
    # right now answers in the form of a table are not supported, but this pass removes interfering table headings

    regex4 = r"Table \d{1,2} Answer to SAQ \d{1,2}\n"
    wholebook = re.sub(regex4, "", wholebook, 0, re.MULTILINE)

    return wholebook

# helper class used to properly format anki cards
class Card:
    def __init__(self, page, SAQ, prefix, question, answer):
        self.page = page
        #self.unit = unit.replace(" ", "_") - omitted due to complexity
        self.SAQ = SAQ.replace(" ", "_")
        self.prefix = prefix
        self.question = question.replace('"', '""')
        self.answer = answer.replace('"', '""')

    def __str__(self):
    
        return f""""SAQ {self.SAQ[4:]} (Page {self.page}) {self.prefix}\n{self.question}";"{self.answer}";Page_{self.page}_{self.SAQ}\n"""

# Load your PDF
with open(pdfPath, "rb") as f:
    pdf = pdftotext.PDF(f)

wholebook, pageNos = combine_pages(pdf)
wholebook = remove_page_boundaries(wholebook)
wholebook = remove_interfering_portions(wholebook)


# Two regexex that match to the Question block and Answer block respectively
SAQregex = r"(SAQ\s\d{1,2})\n[\.\n]+([\s\S]*?)((\n\n\d)|(?=Answer))"
answerRegex = r"(Answer\n[\.\n]+)([\s\S]*?)((?=SAQ)|(?=Exercise)|(?=\nIn Exercise)|(?=\n\n))"

# Finding matches within the whole book
SAQmatches = re.finditer(SAQregex, wholebook, re.MULTILINE)
answerMatches = re.finditer(answerRegex, wholebook, re.MULTILINE)

# defining and populating our list of SAQs, questions & answers:

SAQs = []
questions = []
answers = []

for matchNum, match in enumerate(SAQmatches, start=1):
    SAQs.append(match.group(1))
    questions.append(match.group(2))    

for matchNum, match in enumerate(answerMatches, start=1):
    answers.append(match.group(2))
    
#TODO: some kind of exception here if these arrays don't have matching sizes

if len(SAQs) != len(pageNos) != len(questions) != len(answers):
    print("WARNING - your constituent lists are not of equal size")
    print("This means there are probably some invalid cards. Sorry!")
    print(f"SAQs:      {len(SAQs)}")
    print(f"pageNos:   {len(pageNos)}")
    print(f"questions: {len(questions)}")
    print(f"answers:   {len(answers)}")

# combine our four lists into one list of lists
QandAs = list(zip(SAQs, pageNos, questions, answers))

# list of all subquestion prefixs
prefixList = [
    "(a)",
    "(b)",
    "(c)",
    "(d)",
    "(e)",
    "(f)",
    "(g)",
    "(h)",
    "(i)",
    "(j)",
    "(k)",
    "(l)",
    "(m)"
]    

# poulate a list of cards
cards = []
for SAQ, pageNo, question, answer in QandAs:
    prefixsInBlock = [x for x in prefixList if x in question]

    # if the SAQ has subquestion prefixs, then create a card for each subquestion
    # TODO: put this behind a flag
    if len(prefixsInBlock) > 1:
        for index in range(len(prefixsInBlock)):

            qStart = question.find(prefixsInBlock[index])
            aStart = answer.find(prefixsInBlock[index])
            
            if index == (len(prefixsInBlock) - 1):
                qEnd = len(question)
                aEnd = len(answer)
            else:
                qEnd = question.find(prefixsInBlock[index + 1])
                aEnd = answer.find(prefixsInBlock[index + 1])
            
            subquestion = question[qStart:qEnd - 1]
            subanswer = answer[aStart:aEnd - 1]
            card = Card(
                pageNo,
                SAQ,
                prefixsInBlock[index],
                subquestion[4:],
                subanswer[4:],
            )
            if debug:
                print(f"{SAQ}{prefixsInBlock[index]}, (Page {pageNo})\n{subquestion[4:]}\n=============\n{subanswer[4:]}\n")

            # if we have an empty subanswer, then something has gone wrong
            # TODO: put this behind an exception, or at least notify the user that their cards won't be perfect.
            if len(subanswer) == 0:
                print(f"WARNING - {SAQ}{prefixsInBlock[index]} (Page {pageNo}) has an empty answer")
            cards.append(card)
    
    # otherwise just create a card with the question and answer
    else:
        if debug:
            print(f"{SAQ}, (Page {pageNo})\n{question}\n=============\n{answer}\n")
        card = Card(
            pageNo,
            SAQ,
            "",
            question,
            answer
        )
        cards.append(card)

# write list of cards to file:
tagname = pdfPath.stem.replace(" ", "_")
filename = pdfPath.stem + " cards.txt"

#TODO: add guards
#TODO: add option to define filename
#TODO: add SAQ number to debug
#TODO: prompt for debug mode
#TODO: some method of automatically highlighting missing SAQ in the series
with open(filename, "w") as f:
    f.write(f"tags:{tagname}\n")
    for card in cards:
        f.writelines(str(card))

print(f"{len(cards)} cards written to {filename}")