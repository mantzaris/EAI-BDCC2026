$ENV{'TEXINPUTS'} = 'template:' . ($ENV{'TEXINPUTS'} // '');
$ENV{'BSTINPUTS'} = 'template:' . ($ENV{'BSTINPUTS'} // '');
$pdf_mode = 1;
$pdflatex = 'pdflatex -interaction=nonstopmode -halt-on-error %O %S';
$out_dir = 'build';
