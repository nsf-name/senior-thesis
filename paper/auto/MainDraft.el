;; -*- lexical-binding: t; -*-

(TeX-add-style-hook
 "MainDraft"
 (lambda ()
   (TeX-add-to-alist 'LaTeX-provided-class-options
                     '(("book" "12pt" "oneside")))
   (TeX-add-to-alist 'LaTeX-provided-package-options
                     '(("amscd" "") ("amsmath" "") ("amssymb" "") ("amsthm" "") ("verbatim" "") ("inputenc" "utf8") ("geometry" "") ("setspace" "") ("physics" "") ("subcaption" "") ("natbib" "authoryear") ("pdfpages" "") ("siunitx" "") ("fancyhdr" "") ("float" "") ("graphicx" "pdftex" "") ("listings" "") ("bm" "") ("appendix" "") ("url" "") ("longtable" "") ("booktabs" "") ("multirow" "") ("wrapfig" "")))
   (add-to-list 'LaTeX-verbatim-environments-local "lstlisting")
   (add-to-list 'LaTeX-verbatim-macros-with-braces-local "url")
   (add-to-list 'LaTeX-verbatim-macros-with-braces-local "path")
   (add-to-list 'LaTeX-verbatim-macros-with-braces-local "lstinline")
   (add-to-list 'LaTeX-verbatim-macros-with-delims-local "url")
   (add-to-list 'LaTeX-verbatim-macros-with-delims-local "path")
   (add-to-list 'LaTeX-verbatim-macros-with-delims-local "lstinline")
   (TeX-run-style-hooks
    "latex2e"
    "Chapters/Abstract"
    "Chapters/Acknowledgments"
    "Chapters/Introduction"
    "Chapters/Data"
    "Chapters/Conclusions"
    "Chapters/FutureWork"
    "Chapters/zz_HowToLatex"
    "Chapters/AppendixA"
    "book"
    "bk12"
    "amscd"
    "amsmath"
    "amssymb"
    "amsthm"
    "verbatim"
    "inputenc"
    "geometry"
    "graphicx"
    "setspace"
    "physics"
    "subcaption"
    "natbib"
    "pdfpages"
    "siunitx"
    "fancyhdr"
    "float"
    "listings"
    "bm"
    "appendix"
    "url"
    "longtable"
    "booktabs"
    "multirow"
    "wrapfig")
   (LaTeX-add-labels
    "sec:appendix_a")
   (LaTeX-add-bibliographies
    "bibliography"))
 :latex)

