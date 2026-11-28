"""Keep private working files and accidental credentials out of source releases."""
from pathlib import Path
import re
import subprocess
import unittest

from build_bootstrap import SOURCE_FILES

ROOT=Path(__file__).resolve().parent


class RepositoryContents(unittest.TestCase):
    def test_runtime_payload_is_first_party_source_and_metadata(self):
        self.assertEqual(len(SOURCE_FILES),len(set(SOURCE_FILES)))
        for name in SOURCE_FILES:
            self.assertEqual(Path(name).name,name)
            self.assertIn(Path(name).suffix,('.py','.json','.txt','.md',''))
            self.assertTrue((ROOT/name).is_file(),name)

    def test_public_files_do_not_contain_private_material(self):
        try:
            names=subprocess.check_output(['git','ls-files','-z','--cached','--others','--exclude-standard'],cwd=ROOT).decode().split('\0')
        except (OSError,subprocess.CalledProcessError):
            self.skipTest('Git is needed to check the source distribution.')
        patterns={
            'personal home path':rb'(?i)[a-z]:[\\/]+Users[\\/]+(?!Public|Default|USERNAME|YOUR)[^\s"\x27<>]+',
            'private key':rb'-----BEGIN (?:RSA |EC |OPENSSH |DSA )?PRIVATE KEY-----',
            'GitHub credential':rb'\b(?:gh[pousr]_[A-Za-z0-9]{30,}|github_pat_[A-Za-z0-9_]{40,})\b',
            'cloud credential':rb'\b(?:AKIA[0-9A-Z]{16}|sk-(?:proj-)?[A-Za-z0-9_-]{30,}|AIza[0-9A-Za-z_-]{30,})\b',
            'credential URL':rb'https?://[^\s/"\x27:]+:[^\s/@"\x27]+@',
        }
        for name in filter(None,names):
            path=ROOT/name
            if not path.is_file():
                continue  # A deletion staged during local cleanup is allowed.
            self.assertFalse(name.startswith(('audit/','local-review/')),name)
            self.assertNotIn(path.suffix.lower(),('.pem','.key','.p12','.pfx','.db','.sqlite3','.log'),name)
            self.assertFalse(path.name=='.env' or (path.name.startswith('.env.') and path.name!='.env.example'),name)
            for label,pattern in patterns.items():
                self.assertIsNone(re.search(pattern,path.read_bytes()),f'{name}: {label}')


if __name__=='__main__':
    unittest.main()
