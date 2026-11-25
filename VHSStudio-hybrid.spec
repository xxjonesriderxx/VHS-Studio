# -*- mode: python ; coding: utf-8 -*-
from pathlib import Path
import sysconfig
import site as site_module
from PyInstaller.utils.hooks import collect_all, collect_submodules, collect_data_files, copy_metadata
here=Path(SPECPATH)
site_module.addsitedir(str(here/'builddeps'))
site=Path(sysconfig.get_path('purelib'))
hidden=['engine','qtgmc_limit','automation','mcp_server','review','review_store','i18n','preferences','ui_icons','runtime_components','app_updates','app_version','archive_layout','notifications','win32com.client','win32com.shell.shell','win32com.propsys.propsys','win32com.propsys.pscon']
datas=[(str(here/'model'),'model'),(str(here/'assets/licenses'),'licenses'),(str(here/'runtime-manifest.json'),'.')]
binaries=[]
for prefix in ('mcp.server','mcp.shared','mcp.types','mcp.os'):
 hidden += collect_submodules(prefix)
datas += copy_metadata('mcp')
datas.append((str(here/'AI-CONTROL.md'),'.'))
for name in ['customtkinter','vsdeinterlace','vsaa','vsdeband','vsdenoise','vsexprtools','vskernels','vsmasktools','vsrgtools','vstools','vsjetpack','jetpytools','vsutil','vsscale','vsadjust','vsdehalo','vsfft','vsgrain','vsmuxtools','vssource','vstools']:
 try:
  d,b,h=collect_all(name)
  datas += [(src,dst) for src,dst in d if not (name=="vapoursynth" and "plugins" in Path(src).parts)]
  binaries += [(src,dst) for src,dst in b if not (name=="vapoursynth" and "plugins" in Path(src).parts)]
  hidden+=h
 except Exception:
  pass
hidden+=collect_submodules('winrt')
for package in (here/'vendor/winrt').rglob('__init__.py'):
 hidden.append('.'.join(package.parent.relative_to(here/'vendor').parts))
datas.append((str(here/'vendor/winrt'),'winrt'))
for table in (here/'vendor/winrt').rglob('*.pywinrt'):
 datas.append((str(table),str(Path('winrt')/table.relative_to(here/'vendor/winrt').parent)))
hidden+=['upscale_ncnn_py.upscale_ncnn_vulkan_wrapper']
datas+=collect_data_files('darkdetect')
binaries += [(str(p),'upscale_ncnn_py') for p in (here/'vendor/upscale_ncnn_py').glob('*.dll')]
for metadata in site.glob('*.dist-info'):
 name=metadata.name.split('-')[0]
 if name.lower().startswith(('vs','vapoursynth','jetpytools','dfttest')):
  datas.append((str(metadata),metadata.name))
a=Analysis([str(here/'app.py')],pathex=[str(here),str(here/'vendor'),str(here/'builddeps')],binaries=binaries,datas=datas,
 hiddenimports=hidden,hookspath=[],runtime_hooks=[],excludes=['vapoursynth','torch','torchvision','cv2','matplotlib','IPython','pytest','notebook','sympy'],noarchive=False)
pyz=PYZ(a.pure)
exe=EXE(pyz,a.scripts,a.binaries,a.datas,[],name='VHS Studio',debug=False,bootloader_ignore_signals=False,strip=False,upx=False,
 console=False,uac_admin=False,disable_windowed_traceback=False,icon=str(here/'app.ico') if (here/'app.ico').exists() else None,
 version=str(here/'version.txt'))
