.PHONY: all clean
all:
	mkdir -p build
	TEXINPUTS=template//: BIBINPUTS=.: BSTINPUTS=template//: pdflatex -halt-on-error -interaction=nonstopmode -output-directory=build main.tex
	BIBINPUTS=.: BSTINPUTS=template//: bibtex build/main
	TEXINPUTS=template//: pdflatex -halt-on-error -interaction=nonstopmode -output-directory=build main.tex
	TEXINPUTS=template//: pdflatex -halt-on-error -interaction=nonstopmode -output-directory=build main.tex
	cp build/main.pdf graph_representations_draft.pdf
clean:
	rm -f build/main.aux build/main.bbl build/main.blg build/main.log build/main.out build/main.pdf
