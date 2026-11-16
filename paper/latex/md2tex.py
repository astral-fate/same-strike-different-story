"""Generate paper/latex/main.tex from paper/report.md, so the LaTeX paper never drifts from the source text.
Usage:  python paper/latex/md2tex.py   then   latexmk -pdf main.tex   (run inside paper/latex)."""
from __future__ import annotations

import re
from pathlib import Path

HERE = Path(__file__).resolve().parent
MD = (HERE.parent / "report.md").read_text(encoding="utf-8")

CITES = [  # (markdown text, latex) applied to body text before escaping
    ("Steinert and Kazenwadel's (2025)", r"\citeauthor{steinert2025user}'s \citeyearpar{steinert2025user}"),
    ("Steinert and Kazenwadel (2025)", r"\citet{steinert2025user}"),
    ("Steinert & Kazenwadel, 2025", r"\citealp{steinert2025user}"),
    ("Qi et al. (2023)", r"\citet{qi2023crosslingual}"),
    ("Li, Haider and Callison-Burch (2024)", r"\citet{li2024land}"),
    ("(Stray, sprint keynote, 2026)", r"\citep{stray2026keynote}"),
]

PRE = r"""\documentclass[11pt,a4paper]{article}
\input{glyphtounicode}
\pdfgentounicode=1
\usepackage[margin=1in]{geometry}
\usepackage[T1]{fontenc}
\usepackage[utf8]{inputenc}
\usepackage{newpxtext,newpxmath}
\usepackage{microtype}
\usepackage{booktabs,tabularx,array,longtable}
\usepackage{graphicx}
\usepackage{xcolor}
\usepackage{amsmath}
\usepackage{enumitem}
\usepackage{caption}
\usepackage{titlesec}
\usepackage{placeins}
\usepackage{float}
\usepackage[round,authoryear]{natbib}
\usepackage{hyperref}
\hypersetup{colorlinks=true,linkcolor=blue!50!black,citecolor=blue!50!black,urlcolor=blue!50!black}
\graphicspath{{../../figures/}}
\captionsetup{font=small,labelfont=bf,skip=4pt}
\titleformat{\section}{\large\bfseries}{\thesection.}{0.5em}{}
\titleformat{\subsection}{\normalsize\bfseries}{\thesubsection}{0.5em}{}
\titlespacing*{\section}{0pt}{9pt plus 2pt minus 2pt}{3pt plus 1pt}
\titlespacing*{\subsection}{0pt}{6pt plus 1pt minus 1pt}{2pt plus 1pt}
\setlist{itemsep=1pt,topsep=2pt,parsep=0pt}
\setlength{\emergencystretch}{3em}
\widowpenalty=10000 \clubpenalty=10000
\renewcommand{\topfraction}{0.9}\renewcommand{\textfraction}{0.08}\renewcommand{\floatpagefraction}{0.75}
\newcolumntype{Y}{>{\raggedright\arraybackslash}X}
\newcolumntype{C}{>{\centering\arraybackslash}X}
\newcolumntype{L}[1]{>{\raggedright\arraybackslash}p{#1}}
\DeclareUnicodeCharacter{2212}{\ensuremath{-}}
\DeclareUnicodeCharacter{2265}{\ensuremath{\geq}}
\DeclareUnicodeCharacter{2192}{\ensuremath{\rightarrow}}
\DeclareUnicodeCharacter{2080}{\ensuremath{_0}}
\DeclareUnicodeCharacter{2081}{\ensuremath{_1}}
\DeclareUnicodeCharacter{00D7}{\ensuremath{\times}}
\begin{document}
\thispagestyle{plain}
\begin{center}
\rule{\textwidth}{2.2pt}\\[10pt]
{\LARGE\bfseries %(t1)s\\[4pt]}
{\large\bfseries %(t2)s\footnote{Research conducted at the \href{https://apartresearch.com/sprints/ai-x-epistemics-research-sprint-2026-11-13-to-2026-11-15}{Apart Research AI x Epistemics Sprint 2026}, 13--15 November 2026. Code, data and all raw responses: \url{https://github.com/astral-fate/same-strike-different-story}.}}\\[8pt]
\rule{\textwidth}{0.6pt}\\[10pt]
{\large Fatimah Emad Eldin}\\
Cairo University\\
\texttt{12422024441586@pg.cu.edu.eg}\\[6pt]
\textbf{With} Apart Research\\
{\small Apart Research AI x Epistemics Sprint 2026\\ Track 1: Model Epistemics \& Decision-Making Evals; Track 4: Open Track}\\[10pt]
{\large\bfseries Abstract}
\end{center}
\vspace{-4pt}
"""

FIGW = {"architecture.png": 0.86, "fig3_attribution.png": 0.92, "fig1_event_fi.png": 0.62, "fig2_model_divergence.png": 0.8}


def esc(s: str) -> str:
    out, i = [], 0
    # protect citation commands
    keep = {}
    for k, (a, b) in enumerate(CITES):
        tok = f"@@C{k}@@"
        if a in s:
            s = s.replace(a, tok); keep[tok] = b
    s = s.replace("\\", r"\textbackslash{}")
    for a, b in [("&", r"\&"), ("%", r"\%"), ("$", r"\$"), ("#", r"\#"), ("_", r"\_"), ("{", r"\{"), ("}", r"\}"),
                 ("~", r"\textasciitilde{}"), ("^", r"\textasciicircum{}")]:
        s = s.replace(a, b)
    s = s.replace(r"\textbackslash\{\}", r"\textbackslash{}")
    s = re.sub(r"`([^`]+)`", r"\\texttt{\1}", s)
    s = re.sub(r"\*\*([^*]+)\*\*", r"\\textbf{\1}", s)
    s = re.sub(r"(?<![\w*])\*([^*]+)\*(?![\w*])", r"\\emph{\1}", s)
    s = re.sub(r'"([^"]*)"', r"``\1''", s)
    s = s.replace("e.g. ", r"e.g.\ ").replace("vs ", r"vs.\ ").replace("p < ", r"$p<$ ")
    s = re.sub("(?<=[a-z])–(?=[A-Z])", lambda m: r"–\allowbreak{}", s)
    for tok, b in keep.items():
        s = s.replace(tok, b)
    return s


def table(rows: list[str], caption: str | None, label: str, small=False, spec=None, pos="htbp") -> str:
    cells = [[c.strip() for c in r.strip().strip("|").split("|")] for r in rows if not re.match(r"^\|[-| ]+\|$", r.strip())]
    head, body = cells[0], cells[1:]
    n = len(head)
    spec = spec or ("l" + "r" * (n - 1))
    env = "tabularx" if ("Y" in spec or "C" in spec) else "tabular"
    w = "{\\linewidth}" if env == "tabularx" else ""
    lines = [rf"\begin{{table}}[{pos}]", r"\centering", r"\footnotesize\setlength{\tabcolsep}{4pt}\renewcommand{\arraystretch}{0.97}" if small else r"\small",
             rf"\begin{{{env}}}{w}{{{spec}}}", r"\toprule",
             " & ".join(rf"\textbf{{{esc(h)}}}" for h in head) + r" \\", r"\midrule"]
    lines += [" & ".join(esc(c) for c in r) + r" \\" for r in body]
    lines += [r"\bottomrule", rf"\end{{{env}}}"]
    if caption:
        lines.append(rf"\caption{{{esc(caption)}}}\label{{{label}}}")
    lines.append(r"\end{table}")
    return "\n".join(lines)


def main():
    title = MD.splitlines()[0].lstrip("# ").strip()
    t1, t2 = title.split(": ", 1)
    body = MD.split("## Abstract", 1)[1]
    abstract, rest = body.split("## 1. Introduction", 1)
    rest = "## 1. Introduction" + rest
    rest = re.sub(r"## References\n.*?(?=## Appendix A)", "", rest, flags=re.S)
    out = [PRE % {"t1": t1.upper(), "t2": t2}, r"\begin{quote}\small", esc(abstract.strip()), r"\end{quote}", ""]
    lines = rest.splitlines()
    i, para, appendix, ntab = 0, [], False, 0

    def flush():
        if para:
            out.append(esc(" ".join(para)) + "\n"); para.clear()
    while i < len(lines):
        ln = lines[i]
        if ln.startswith("## "):
            flush()
            h = ln[3:].strip()
            if h.startswith("Appendix"):
                if not appendix:
                    out += [r"\bibliographystyle{plainnat}", r"\bibliography{references}", r"\clearpage", r"\appendix"]
                    appendix = True
                out.append(rf"\section{{{esc(h.split('. ', 1)[1])}}}")
            else:
                out.append(rf"\section{{{esc(re.sub(r'^\d+\.\s*', '', h))}}}")
        elif ln.startswith("### "):
            flush(); out.append(rf"\subsection{{{esc(re.sub(r'^[\d.]+\s*', '', ln[4:].strip()))}}}")
        elif ln.startswith("!["):
            flush()
            m = re.match(r"!\[(.*)\]\(\.\./figures/(.+?)\)", ln)
            cap, f = m.group(1), m.group(2)
            cap = re.sub(r"^Figure \d+\.\s*", "", cap)
            out += [r"\begin{figure}[htbp]", r"\centering", rf"\includegraphics[width={FIGW[f]}\linewidth]{{{f}}}",
                    rf"\caption{{{esc(cap)}}}\label{{fig:{f.split('.')[0]}}}", r"\end{figure}"]
        elif ln.startswith("|"):
            flush()
            rows = []
            while i < len(lines) and lines[i].startswith("|"):
                rows.append(lines[i]); i += 1
            cap = None
            if i + 1 < len(lines) and lines[i + 1].startswith("*Table"):
                cap = re.sub(r"^\*Table \d+\.\s*|\*$", "", lines[i + 1].strip()); i += 2
            ntab += 1
            if appendix and len(rows[0].split("|")) > 6:
                out.append(table(rows, "Conflict events, reported attackers and baseline naming rates.", "tab:events",
                                 small=True, spec=r"L{2.45cm}YL{2.9cm}cc", pos="H"))
            elif appendix:
                out.append(table(rows, "Answers from Claude Haiku 5.5 to the prompt above.", "tab:example",
                                 spec="lccl", pos="H"))
            else:
                out.append(table(rows, cap or "", f"tab:{ntab}", spec="L{3.3cm}" + "C" * (rows[0].count("|") - 2)))
            continue
        elif ln.startswith("- "):
            flush(); out.append(r"\begin{itemize}[leftmargin=*]")
            while i < len(lines) and lines[i].startswith("- "):
                out.append(r"\item " + esc(lines[i][2:])); i += 1
            out.append(r"\end{itemize}"); continue
        elif ln.startswith("> "):
            flush()
            out += [r"\begin{quote}\small\ttfamily", esc(ln[2:]).replace("<", r"\textless{}").replace(">", r"\textgreater{}"),
                    r"\end{quote}"]
        elif not ln.strip():
            flush()
        else:
            para.append(ln.strip())
        i += 1
    flush()
    out.append(r"\end{document}")
    tex = "\n".join(out)
    tex = tex.replace(r"\section{Introduction}", r"\section{Introduction}", 1)
    (HERE / "main.tex").write_text(tex, encoding="utf-8")
    print("wrote", HERE / "main.tex")


if __name__ == "__main__":
    main()
