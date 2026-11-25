"""Test preferences, no-rebuild translation and login runner in isolation."""
import os
from pathlib import Path
import sys
import tempfile
ROOT=Path(__file__).resolve().parent
import site
site.addsitedir(str(ROOT/'builddeps'))
sys.path[:0]=[str(ROOT),str(ROOT/'vendor')]
os.environ['PYTHONPATH']=os.pathsep.join(sys.path)
with tempfile.TemporaryDirectory(prefix='VHS-Studio-check-') as directory:
    base=Path(directory)
    os.environ['VHS_STUDIO_STATE_DIR']=str(base/'state')
    import preferences
    config=dict(source=str(ROOT/'test-input'),output=str(base/'output'),deinterlace=True,
        method='BWDIF',replace=False,upscale=False,ocr=False,ocr_rate=1,recursive=True,
        cpu_mode='background',limit=1,archive=False,notifications=False)
    link=base/'test-only.lnk'
    preferences.configure_startup(config,enabled=True,link_path=link)
    assert link.exists()
    import win32com.client
    shortcut=win32com.client.Dispatch('WScript.Shell').CreateShortcut(str(link))
    assert '--autostart' in shortcut.Arguments
    preferences.run_startup()
    status=preferences.read_json(base/'state/autostart-status.json')
    assert status['state']=='finished',status
    assert status['completion']['failed']==0,status
    first=status['job_id']
    preferences.run_startup()
    status=preferences.read_json(base/'state/autostart-status.json')
    assert status['state']=='nothing_pending',status
    preferences.configure_startup(enabled=False,link_path=link)
    assert not link.exists()
    preferences.run_startup()  # disabled runner must do nothing
    assert preferences.read_json(base/'state/autostart-status.json')==status
    print('Isolated login shortcut, headless render, skip completed, disable: PASS')
    from app import Studio
    ui=Studio(); ui.update()
    assert ui.rate.cget('state')=='disabled'
    assert ui.start_button.cget('fg_color')!='#69d8bd'
    ui.source.insert(0,config['source']); ui.output.insert(0,config['output'])
    ui.cpu.set(ui.t('Hintergrund / Spielen'))
    ui.limit.delete(0,'end');ui.limit.insert(0,'7')
    ui.tree.insert('', 'end', iid='test',values=('example.mkv','0:02','Deinterlacing','Bereit'))
    ui.tree.selection_set('test')
    ui.plan=[dict(test=True)]
    old_widgets=(id(ui.tree),id(ui.tabs),id(ui.source),id(ui.start_button))
    old_geometry=ui.geometry()
    ui.switch_language(); ui.update()
    assert ui.start_button.cget('text')=='Start restoration'
    assert ui.cpu.get()=='Background / Gaming'
    assert ui.tree.heading('name','text')=='Recording'
    assert ui.tree.selection()==('test',)
    assert ui.plan==[dict(test=True)]
    ui.switch_language(); ui.update()
    assert ui.start_button.cget('text')=='Restaurierung starten'
    assert ui.tree.heading('name','text')=='Aufnahme'
    assert old_widgets==(id(ui.tree),id(ui.tabs),id(ui.source),id(ui.start_button))
    assert old_geometry==ui.geometry()
    assert ui.cpu.get()=='Hintergrund / Spielen'
    ui.save_settings()
    for token in ui.tk.call('after','info'):
        ui.tk.call('after','cancel',token)
    ui.destroy()
    other=Studio();other.update()
    assert other.source.get()==config['source']
    assert other.limit.get()=='7'
    assert other.cpu.get()=='Hintergrund / Spielen'
    other.destroy()
    print('In-place DE/EN preserves widgets, geometry, queue and selection; reload preferences: PASS')
