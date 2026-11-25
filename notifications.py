"""Windows 10/11 toast notifications using a per-user AppUserModelID shortcut."""
import base64
import os
from pathlib import Path
import subprocess
import sys
import xml.etree.ElementTree as ET

APP_ID='VHSStudio.Portable'

def register():
    import pythoncom
    import win32com.client
    from win32com.shell import shell
    from win32com.propsys import propsys,pscon
    programs=Path(win32com.client.Dispatch('WScript.Shell').SpecialFolders('Programs'))
    path=programs/'VHS Studio.lnk'
    shortcut=pythoncom.CoCreateInstance(shell.CLSID_ShellLink,None,pythoncom.CLSCTX_INPROC_SERVER,shell.IID_IShellLink)
    shortcut.SetPath(sys.executable)
    args=[] if getattr(sys,'frozen',False) else [str(Path(__file__).with_name('app.py'))]
    shortcut.SetArguments(subprocess.list2cmdline(args))
    shortcut.SetWorkingDirectory(str(Path(sys.executable).parent))
    shortcut.SetDescription('VHS Studio restoration notifications')
    store=shortcut.QueryInterface(propsys.IID_IPropertyStore)
    store.SetValue(pscon.PKEY_AppUserModel_ID,propsys.PROPVARIANTType(APP_ID,pythoncom.VT_LPWSTR))
    store.Commit()
    shortcut.QueryInterface(pythoncom.IID_IPersistFile).Save(str(path),True)
    return path

def xml(title,body):
    root=ET.Element('toast',duration='short')
    binding=ET.SubElement(ET.SubElement(root,'visual'),'binding',template='ToastGeneric')
    ET.SubElement(binding,'text').text=str(title)[:200]
    ET.SubElement(binding,'text').text=str(body)[:1000]
    return ET.tostring(root,encoding='utf8')

def send(title,body,wait=False):
    """Best effort. Notification failures never fail a restoration run."""
    try:
        register()
        data=base64.b64encode(xml(title,body)).decode('ascii')
        script=("$ErrorActionPreference='Stop';$ProgressPreference='SilentlyContinue';"
            "[Windows.UI.Notifications.ToastNotificationManager,Windows.UI.Notifications,ContentType=WindowsRuntime]>$null;"
            "[Windows.Data.Xml.Dom.XmlDocument,Windows.Data.Xml.Dom.XmlDocument,ContentType=WindowsRuntime]>$null;"
            "$doc=New-Object Windows.Data.Xml.Dom.XmlDocument;"
            f"$doc.LoadXml([Text.Encoding]::UTF8.GetString([Convert]::FromBase64String('{data}')));"
            "$toast=[Windows.UI.Notifications.ToastNotification]::new($doc);"
            f"$notifier=[Windows.UI.Notifications.ToastNotificationManager]::CreateToastNotifier('{APP_ID}');"
            "$notifier.Show($toast);$notifier.Setting.ToString()")
        encoded=base64.b64encode(script.encode('utf-16-le')).decode('ascii')
        powershell=Path(os.environ.get('SystemRoot',r'C:\Windows'))/'System32/WindowsPowerShell/v1.0/powershell.exe'
        args=[str(powershell),'-NoProfile','-NonInteractive','-EncodedCommand',encoded]
        if wait:
            result=subprocess.run(args,capture_output=True,timeout=20,creationflags=subprocess.CREATE_NO_WINDOW)
            return dict(ok=result.returncode==0,setting=result.stdout.decode(errors='replace').strip(),
                        error=result.stderr.decode(errors='replace')[-500:] if result.returncode else '')
        subprocess.Popen(args,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,creationflags=subprocess.CREATE_NO_WINDOW)
        return dict(ok=True,submitted=True)
    except Exception as error:
        return dict(ok=False,error=str(error))
