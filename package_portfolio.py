"""Build a portable review bundle without raw data, databases, venv or personal CV."""
from pathlib import Path
import zipfile

ROOT=Path(__file__).resolve().parent

def main():
    output=ROOT.parent/'数据分析项目作品集.zip'
    excluded={'.venv','__pycache__','raw','processed','.git'}
    allowed={'.py','.sql','.md','.html','.json','.txt','.png','.csv'}
    paths=sorted(p for p in ROOT.rglob('*') if p.is_file() and (p.suffix in allowed or p.name in {'.gitignore','.gitattributes'})
                 and p.name!='简历描述与面试准备.md'
                 and not any(x in excluded for x in p.relative_to(ROOT).parts))
    with zipfile.ZipFile(output,'w',compression=zipfile.ZIP_DEFLATED) as z:
        for p in paths: z.write(p,Path('data-analysis-portfolio')/p.relative_to(ROOT))
    print(f'{output}: {len(paths)} files, {output.stat().st_size:,} bytes')

if __name__=='__main__': main()
