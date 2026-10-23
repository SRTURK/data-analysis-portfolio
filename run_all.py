"""One command rebuilds either or both projects without network access."""
from pathlib import Path
import argparse
import subprocess
import sys

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--project',choices=['all','olist','experiment'],default='all')
    args=parser.parse_args()
    root=Path(__file__).resolve().parent
    for key,folder in [('olist','01-olist-operations'),('experiment','02-marketing-experiment')]:
        if args.project in ['all',key]:
            subprocess.run([sys.executable,str(root/folder/'run.py')],check=True)

if __name__=='__main__': main()
