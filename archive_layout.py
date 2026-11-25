"""English names for new archives, compatible with existing German folders."""
from pathlib import Path

ALIASES={
    'originals':('_OriginalCuts','_Originalschnitte'),
    'deinterlaced':('_Deinterlaced',),
    'corrections':('_CutCorrections','_Schnittkorrektur'),
    'administration':('_Administration','_Verwaltung'),
}
EXCLUDED={name for names in ALIASES.values() for name in names}

def folder(root, role):
    root=Path(root)
    for name in ALIASES[role]:
        if (root/name).is_dir():
            return root/name
    return root/ALIASES[role][0]

def data_folder(root):
    root=Path(root)
    for name in ALIASES['administration']:
        if (root/name/'VHS-Studio/VHS-Studio.sqlite3').is_file():
            return root/name/'VHS-Studio'
    return folder(root,'administration')/'VHS-Studio'

def initialized(root):
    return any((Path(root)/name).is_dir() for name in ALIASES['originals'])

def initialize(root):
    root=Path(root)
    if not root.is_dir():
        raise ValueError('Archive source folder must already exist')
    paths=[folder(root,role) for role in ALIASES]
    for path in paths:
        path.mkdir(exist_ok=True)
    return paths

def original(root, relative, stem):
    choices=set()
    for name in ALIASES['originals']:
        parent=Path(root)/name/Path(relative).parent
        for candidate in parent.glob('*') if parent.is_dir() else []:
            if candidate.is_file() and candidate.stem.casefold() in (stem.casefold(),(stem+' - Original').casefold()):
                choices.add(candidate.resolve())
    if len(choices)>1:
        raise ValueError('Multiple originals match this recording; resolve the mapping before replacing it')
    return next(iter(choices),None)
