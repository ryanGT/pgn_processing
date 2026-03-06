#!/usr/bin/env python3
# coding: utf-8
import re, os, copy
from krauss_misc import txt_mixin
import glob

import argparse

parser = argparse.ArgumentParser()

parser.add_argument("file_in", type=str, default='',
                    help="input file name")

#parser.add_argument('dir', nargs=1, default=os.getcwd())

args = parser.parse_args()
print(args)
fn = args.file_in
#fn = "md_flash_card_test.md"


# # Parsing MD Flashcards to output to PDF

# ## Example Text:
#```chessboard
#fen: r1bq1rk1/p2pppbp/2p2np1/8/3BP3/2N2Q2/PPP2PPP/R3KB1R b KQ - 3 9
#orientation: black
#```
#Why is Re8 bad here?
#?
#It misses a chance to play d5 and it undefends f7, allowing Bc4 to pressure mate on f7

# ## Chop
# 
# Chop at ```chessboard
# 
# The last one will end at the EOF

# ## Latex Templates
old_header = r"""\documentclass[12pt]{article}
\usepackage[margin=0.5in,footskip=0.25in,letterpaper]{geometry}
\usepackage{skak}
\usepackage{chessboard}
\usepackage{graphicx}

\begin{document}"""

header = r"""\documentclass[12pt]{article}
\usepackage[margin=0.3in,papersize={3.0in,5.0in},footskip=0.15in]{geometry}%footskip=0.2in,
%\usepackage{skak}
\usepackage{chessboard}
\usepackage{graphicx}
\linespread{1.2}
\begin{document}"""

board_template = r"""{\Huge

%s

%s to move
\\
}

\scalebox{2.3}{
\chessboard[%s,
            showmover]
}

{\large \vspace{1EM} \begin{verbatim}
FEN: %s
\end{verbatim}
}
"""

old_q_template = r"""{\Huge
%s \\
\vspace{0.2in}

%s to move
\\
}

\newgame
\fenboard{%s}
\scalebox{3}{\showboard}

{\large \vspace{1EM} \begin{verbatim}
FEN: %s
\end{verbatim}
}
"""


q_template = r"""{\large
%s \\
\vspace{0.2in}

%s
\\
}

\chessboard[%s]

\pagebreak

"""


solution_template = r"""{\large
Solution
}

\vspace{1in}

{\large
%s
}
"""


old_solution_template = r"""\pagebreak

{\huge
Solution
}

\vspace{3in}

{\huge
\begin{verbatim}
%s
\end{verbatim}
}
"""

myfile = txt_mixin.txt_file_with_list(fn)
mylist = myfile.list

start_inds = mylist.findall("```chessboard")
start_inds

end_inds = start_inds[1:]
end_inds
end_inds.append(None)

fen_re = re.compile(r"\s*^(((?:[rnbqkpRNBQKP1-8]+\/){7})[rnbqkpRNBQKP1-8]+)\s([b|w])\s(-|[K|Q|k|q]{1,4})\s(-|[a-h][1-8])\s(\d+\s\d+)$")



def fenPass(fen):
    """
    """
    #regexMatch=re.match('\s*^(((?:[rnbqkpRNBQKP1-8]+\/){7})[rnbqkpRNBQKP1-8]+)\s([b|w])\s([K|Q|k|q]{1,4})\s(-|[a-h][1-8])\s(\d+\s\d+)$', fen)
    regexMatch = fen_re.match(fen)
    if  regexMatch:
        regexList = regexMatch.groups()
        fen = regexList[0].split("/")
        if len(fen) != 8:
            raise ValueError("expected 8 rows in position part of fen: {0}".format(repr(fen)))

        for fenPart in fen:
            field_sum = 0
            previous_was_digit, previous_was_piece = False,False

            for c in fenPart:
                if c in ["1", "2", "3", "4", "5", "6", "7", "8"]:
                    if previous_was_digit:
                        raise ValueError("two subsequent digits in position part of fen: {0}".format(repr(fen)))
                    field_sum += int(c)
                    previous_was_digit = True
                    previous_was_piece = False
                elif c == "~":
                    if not previous_was_piece:
                        raise ValueError("~ not after piece in position part of fen: {0}".format(repr(fen)))
                    previous_was_digit, previous_was_piece = False,False
                elif c.lower() in ["p", "n", "b", "r", "q", "k"]:
                    field_sum += 1
                    previous_was_digit = False
                    previous_was_piece = True
                else:
                    raise ValueError("invalid character in position part of fen: {0}".format(repr(fen)))

            if field_sum != 8:
                raise ValueError("expected 8 columns per row in position part of fen: {0}".format(repr(fen)))  

    else: raise ValueError("fen doesn`t match follow this example: rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1 ")  


class chess_chunk_parser(object):
    def __init__(self, raw_list):
        self.raw_list = txt_mixin.txt_list(raw_list)


    def parse(self):
        self.list = copy.copy(self.raw_list)
        # Assumptions: 
        # - chunk is a list of lines
        # - the first line is ```chessboard
        # - line 2 is fen: %s
        # - line 3 is orientation: %s
        # - line 4 is ```
        # - comments follow
        # - middle of comments may include '?' by itself
        #     - if it does, answer follow '?'
        line0 = self.list.pop(0)
        line0 = line0.strip()
        #print(line0)
        assert line0 == '```chessboard', "line 0 not valid: %s" % line0
        line1 = self.list.pop(0)
        line1 = line1.strip()
        assert line1.find("fen:") == 0, "problem with fen line: %s" % line1
        fen = line1[4:].strip()
        # check the fen
        fenPass(fen)
        self.fen = fen
        line2 = self.list.pop(0).strip()
        assert line2.find("orientation:") == 0, "problem with orientation line: %s" % line2
        olist = line2.split(":",1)
        myside = olist[1].strip()
        self.myside = myside
        end_md = self.list.pop(0).strip()
        assert end_md == "```", "problem with end of markdown template ```:%s." % end_md
        #what is left should be the comments:
        self.comments = copy.copy(self.list)
        self.break_comments()
        self.escape_pound()


    def escape_pound(self):
        self.question = self.question.replace("#","\\#")
        self.answer = self.answer.replace("#","\\#")


    def break_comments(self):
        # self.comments should be a list
        ind = None
        for i, line in enumerate(self.comments):
            if line.strip() == '?':
                ind = i
                question = '\n'.join(mylist[0:ind])
                answer = '\n'.join(mylist[ind+1:])
                break
        if ind is None:
            self.question = '\n'.join(self.comments)
            self.answer = None
        else:
            self.question = '\n'.join(self.comments[0:ind])
            self.answer = '\n'.join(self.comments[ind+1:])

        self.question = self.question.strip()
        self.answer = self.answer.strip()


    def move_color(self):
        q = fen_re.match(self.fen)
        move_part = q.group(3)
        move_str = move_part.lower().strip()
        if 'w' in move_str:
            return "white"
        else:
            return "black"


    def build_latex(self):
        move_str = self.move_color()
        #inverse,smallboard,setfen=r1bq1rk1/p2pppbp/2p2np1/8/3BP3/2N2Q2/PPP2PPP/R3KB1R b KQ - 3 9
        opt_str = "smallboard,setfen=" + self.fen
        if self.myside == "black":
            opt_str = "inverse," + opt_str
        part1 = q_template % (self.question, move_str, opt_str)
        if self.answer is None:
            part2 = solution_template % "No answer given"
        else:
            part2 = solution_template % self.answer
        self.out = part1 + '\n' + part2
        return self.out




list_of_chunks = []

for s, e in zip(start_inds,end_inds):
    cur_chunk = mylist[s:e]
    list_of_chunks.append(cur_chunk)




mychunks = []

for lines in list_of_chunks:
    mychunk = chess_chunk_parser(lines)
    print(mychunk)
    mychunk.parse()
    mychunks.append(mychunk)


myout = copy.copy(header)

first = 1
for chunk in mychunks:
    if first:
        first = 0
    else:
        myout += '\n\\pagebreak\n'
    new_str = chunk.build_latex()
    myout += new_str

myout += '\\end{document}'


fno, ext = os.path.splitext(fn)
tex_name = fno + '.tex'
txt_mixin.dump(tex_name, [myout])
latex_cmd = "pdflatex %s" % tex_name
os.system(latex_cmd)
print(latex_cmd)



