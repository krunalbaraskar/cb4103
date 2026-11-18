"""Command line stages; complete cache provenance gates reuse."""
import argparse
from .trajectory import load_config,convert

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('stage',choices=['convert','analyze','figures','documents','validate','package','all'])
    p.add_argument('--config',default='config/analysis.json')
    a=p.parse_args(); c=load_config(a.config)
    if a.stage in ['convert','all']: convert(c)
    if a.stage in ['analyze','all']:
        from .analysis import analyze
        analyze(c)
    if a.stage in ['figures','all']:
        from .plotting import make_figures
        make_figures(c)
    if a.stage in ['documents','all']:
        from .documents import build_documents
        build_documents(c)
    if a.stage in ['validate','all']:
        from .validation import validate
        validate(c)
    if a.stage in ['package','all']:
        from .validation import package
        package(c)

if __name__=='__main__': main()
