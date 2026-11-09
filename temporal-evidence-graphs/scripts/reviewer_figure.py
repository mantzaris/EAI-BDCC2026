"""Correct only Figure 1's displayed precision and unit, preserving frozen assets."""
from pathlib import Path
import inspect
from temporal_evidence.semantic import figures

out = Path('artifacts/figures/reviewer_revision')
out.mkdir(parents=True, exist_ok=True)
source = inspect.getsource(figures.ontology)
assert source.count(':.5f}') == 2 and source.count(':.6g}') == 1
source = source.replace(':.5f}', ':.4f}').replace(':.6g}', ':.4f}').replace(' uS', ' µS')

def save(figure, name):
    assert name == 'ontology_construction'
    figure.savefig(out/(name+'.pdf'), bbox_inches='tight')
    figures.plt.close(figure)

namespace = {**vars(figures), 'OUT': out, 'save': save, 'write_json': lambda *args: None}
exec(compile(source, 'reviewer_figure_display_only', 'exec'), namespace)
namespace['ontology']()
