use Cwd qw(abs_path);
my $template_path = abs_path('template');
$ENV{'TEXINPUTS'} = $template_path . ':' . ($ENV{'TEXINPUTS'} // '');
$ENV{'BSTINPUTS'} = $template_path . ':' . ($ENV{'BSTINPUTS'} // '');
$pdf_mode = 1;
$pdflatex = 'pdflatex -interaction=nonstopmode -halt-on-error %O %S';
$out_dir = 'build';
