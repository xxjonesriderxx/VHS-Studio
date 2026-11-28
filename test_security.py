"""Offline checks for CSV injection and component-download trust boundaries."""
from pathlib import Path
import csv
import json
import os
import sqlite3
import subprocess
import tempfile
import unittest

from review_store import csv_value,export
from runtime_components import allowed_url,safe_relative


class SecurityBoundaries(unittest.TestCase):
    def test_csv_export_preserves_raw_database_and_json(self):
        with tempfile.TemporaryDirectory(prefix='vhs-export-test-') as folder,sqlite3.connect(':memory:') as db:
            db.executescript('''
                CREATE TABLE ocr_videos(id INTEGER,path TEXT,size INTEGER,mtime_ns INTEGER);
                CREATE TABLE ocr_stamps(video INTEGER,second REAL,date TEXT,raw TEXT);
                CREATE TABLE ocr_scans(video INTEGER,fps REAL,next_sample INTEGER,done INTEGER);
            ''')
            raw='=1+1'
            db.execute('INSERT INTO ocr_videos VALUES(1,?,10,20)',('fixture.mkv',))
            db.execute('INSERT INTO ocr_stamps VALUES(1,0,?,?)',('2000-01-01',raw))
            db.commit()
            export(db,folder)
            self.assertEqual(db.execute('SELECT raw FROM ocr_stamps').fetchone()[0],raw)
            data=json.loads((Path(folder)/'OCR-Fundstellen.json').read_text('utf8'))
            self.assertEqual(data['videos'][0]['hits'][0]['raw'],raw)
            with (Path(folder)/'OCR-Fundstellen.csv').open(encoding='utf-8-sig',newline='') as stream:
                row=next(csv.DictReader(stream,delimiter=';'))
            self.assertEqual(row['raw_text'],"'"+raw)

    def test_csv_text_cannot_become_a_formula(self):
        for text in ('=1+1','+SUM(1;2)','-2+3','@SUM(1;2)','  =1','\t=1','\r=1','\n=1'):
            self.assertEqual(csv_value(text),"'"+text)
        for value in ('A normal review','2000-01-01','',None,12,0.5):
            self.assertEqual(csv_value(value),value)

    def test_python_download_policy(self):
        allowed_url('https://github.com/owner/repo',{'github.com'})
        credentials='https://'+'user:password@github.com/file'
        for url in ('http://github.com/file','https://github.com.attacker.invalid/file',
                    credentials,'https://github.com:444/file'):
            with self.assertRaises(ValueError):
                allowed_url(url,{'github.com'})
        for path in ('../outside','/absolute','a/../../outside','C:/outside','a\\outside'):
            with self.assertRaises(ValueError):
                safe_relative(path)

    @unittest.skipUnless(os.name=='nt','Windows launcher compiler check')
    def test_launcher_downloads_and_archive_paths(self):
        compiler=Path(os.environ['SystemRoot'])/'Microsoft.NET/Framework64/v4.0.30319/csc.exe'
        if not compiler.is_file():
            self.skipTest('Windows C# compiler is unavailable.')
        harness=r'''
using System;
using System.IO;
using System.Reflection;
class BuildInfo { internal const string PayloadHash = "unused"; }
class LauncherSecurityTests {
 static int Main() {
  var flags=BindingFlags.Static|BindingFlags.NonPublic;
  var allowed=typeof(Launcher).GetMethod("AllowedRuntimeUri",flags);
  foreach(string url in new[]{"https://github.com/x","https://release-assets.githubusercontent.com/x"})
   if(!(bool)allowed.Invoke(null,new object[]{new Uri(url)})) return 1;
  foreach(string url in new[]{"http://github.com/x","https://github.com.attacker.invalid/x","https://"+"user:password@github.com/x","https://github.com:444/x"})
   if((bool)allowed.Invoke(null,new object[]{new Uri(url)})) return 2;
  var safe=typeof(Launcher).GetMethod("SafePath",flags);
  foreach(string value in new[]{"../outside","a/../../outside","/absolute","a:stream","NUL","a./b","a\\b"}) {
   try { safe.Invoke(null,new object[]{Path.GetTempPath(),value}); return 3; }
   catch(TargetInvocationException error) { if(!(error.InnerException is InvalidDataException)) return 4; }
  }
  return 0;
 }
}'''
        with tempfile.TemporaryDirectory(prefix='vhs-security-test-') as folder:
            root=Path(folder);source=root/'Tests.cs';exe=root/'Tests.exe'
            source.write_text(harness,encoding='utf8')
            command=[str(compiler),'/nologo','/target:exe','/main:LauncherSecurityTests','/out:'+str(exe)]
            for name in ('System','System.Core','System.Drawing','System.Windows.Forms','System.Web.Extensions','System.IO.Compression'):
                command.append('/reference:'+name+'.dll')
            command.extend([str(Path(__file__).with_name('bootstrap')/'Launcher.cs'),str(source)])
            subprocess.run(command,check=True,capture_output=True)
            subprocess.run([str(exe)],check=True,capture_output=True)


if __name__=='__main__':
    unittest.main()
