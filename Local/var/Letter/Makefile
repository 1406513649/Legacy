all:
	@rst2latex.py letter.rst > letter.tex
	@gsed -i "s/%\\\/\\\/g" letter.tex
	@gsed -i "/documentclass/a \\\\\usepackage[margin=1in]{geometry}" letter.tex
	@pdflatex letter.tex >> /dev/null
	@$(RM) letter.aux letter.out letter.log 
