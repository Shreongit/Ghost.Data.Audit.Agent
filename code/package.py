from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

root = Path(__file__).resolve().parents[1]
include = [Path('README.md'), Path('code/main.py'), Path('code/smoke_xai.py'), Path('code/config.py'), Path('code/evidence_graph.py'), Path('code/llm.py'), Path('code/requirements.txt'), Path('code/package.py')]
include += sorted(p.relative_to(root) for p in (root / 'code/prompts').rglob('*.md'))
include += sorted(p.relative_to(root) for p in (root / 'code/tests').rglob('*.py'))
include += sorted(p.relative_to(root) for p in (root / 'code/evaluation').rglob('*.md'))
include += sorted(p.relative_to(root) for p in (root / 'code/evaluation').glob('*.py'))
include += sorted(p.relative_to(root) for p in (root / 'code/linking').glob('*.py'))
include += sorted(p.relative_to(root) for p in (root / 'code/linking').glob('*.json')
                  if p.name != 'out_of_fold_predictions.json')
include += sorted(p.relative_to(root) for p in (root / 'code/linking').glob('*.md'))
with ZipFile(root / 'code.zip', 'w', ZIP_DEFLATED) as archive:
    for rel in include:
        archive.write(root / rel, rel.as_posix())
print(f'Wrote code.zip with {len(include)} files')
