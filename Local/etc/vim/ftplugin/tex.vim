"Latex looks good with a bit of indentation
set sw=2

"Cycle through labels using <C-n>
set iskeyword+=:

" My own common shortcuts
" Document set up
map <C-b> i\documentclass[11pt]{article}<cr>\usepackage{amsmath, amsfonts, amsthm, amssymb}<cr>\usepackage{setspace}<cr>\usepackage{bm}<cr>\usepackage{fancyhdr}<cr>\usepackage{lastpage}<cr>\usepackage{extramarks}<cr>\usepackage{chngpage}<cr>\usepackage{soul, color}<cr>\usepackage{graphicx, float, wrapfig}<cr>\usepackage[all]{xy}<cr><cr><cr><cr>\begin{document}<cr> \title{<+Title+>}<cr>\author{<+Author+>}<cr>\date{<+Date+>}<cr>\maketitle<cr>\begin{abstract}<cr><+Abstract+><cr>\end{abstract}<cr><cr><+Document+><cr><cr>\end{document}<C-j><C-k>



imap pgsz \oddsidemargin=-.7in<cr>\evensidemargin=-.7in<cr>\textwidth=8in<cr>\headheight=-1.25in<cr>\textheight=10.5in<cr>\parindent = 0in<cr><cr><cr>

" Compile
map <C-o> \lv <CR>  
map <C-t> :w <cr> :!/usr/texbin/pdflatex --shell-escape --synctex=1 %<CR>

imap <C-o> <Esc> \lv <CR> 
imap <C-t> <Esc> :w <cr> :!/usr/texbin/pdflatex --shell-escape --synctex=1 %<CR>


"Common latex short cuts:


"Arrays
imap ,arr \begin{array}{<+size+>}<cr><+contents+><cr>\end{array}<cr><++><Esc>BBBB<C-j>


"Math display environments
imap ,dm <cr>\[<cr><++><cr>\]<cr><++><Esc>B<C-j>
imap ,im $<space><space><esc>i

"Paranthesis and braces
imap ,lp \left(
imap ,rp \right)

"Wrap word followed by ,, with \begin{...}    \end{...}
imap ,, <esc>bdwi\begin{<esc>pa}<cr><++><cr>\end{<esc>pa}<CR>%<CR><++><Esc>B<C-j>

"Figures and tables
imap fgr %%%%%<cr>% figure<cr>\begin{figure}[h!]<cr>\centering<cr>\includegraphics[width=3.5in]{<+file+>}<cr>\caption{\label{fig:<+lab+>}<+caption+>}<cr>\end{figure}<cr>%<cr><++><C-j>


imap tbl %%%%%<cr>% table<cr>\begin{table}[h!]<cr>\centering<cr>\caption{\label{tab:<+lab+>}<+caption+>}<cr>\begin{tabular}{<+size+>}<cr>\hline<cr><+contents+><cr>\end{tabular}<cr>\end{table}<cr>%<cr><++><C-j>

"Section headings
imap ,sec <cr>%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%<cr>%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%<cr>\section{<+Section+>}<cr>%<cr><++><C-j>
imap ,ssc <cr>%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%<cr>\subsection{<+Section+>}<cr>%<cr><++><C-j>
imap ,sssc <cr>%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%<cr>\subsubsection{<+Section+>}<cr>%<cr><++><C-j>

"Homework stuff
imap ,ex <cr>%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%<cr>%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%<cr>\newpage<cr>\noindent{\bf \Large Exercise <++>}\\<cr>%<cr><++><C-j>
imap ,sol %%%%%<cr>\noindent{\bf Solution:} \\ <cr>%<cr>

"Underlining and font styles
imap ,ul \underline{<++>}<space><++><Esc>B<C-j>
imap ,bm {\bm<++>}<++><Esc>B<C-j>
imap ,bf {\bf<space><++><space>}<space><++><Esc>B<C-j>  

"Greek letters and math symbols
imap ,sig \sigma
imap ,eps \epsilon
imap ,ups \upsilon
imap ,gam \gamma
imap ,pi \pi


"Math formulae
"misc.
imap ,fr \frac{<+num+>}{<+den+>}<space><++><Esc>BBb<C-j>


"scalar derivatives
imap ,der \frac{d<++>}{d<++>}<++><Esc>B<C-j>
imap ,sd \frac{d^2<++>}{d<++>^2}<++><Esc>B<C-j>


"labeling and referencing
imap ,leqn \label{eqn:<+lab+>}<++><Esc>B<C-j>
imap ,reqn (\ref{eqn:<++>})<++><Esc>B<C-j>

"Color scheme
"set bg light
"set bg dark
"set cs pablo
