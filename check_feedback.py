"""Integration checks against synthetic footage only."""
import asyncio
import json
import os
from pathlib import Path
import subprocess
import sys
import time
ROOT=Path(__file__).resolve().parent
os.environ['VHS_STUDIO_STATE_DIR']=str(ROOT/f'feedback-state-{os.getpid()}')
os.chdir(ROOT)
os.environ['PYTHONPATH']=os.pathsep.join([str(ROOT/'builddeps'),str(ROOT/'vendor'),str(ROOT)])
sys.path[:0]=os.environ['PYTHONPATH'].split(os.pathsep)
import site
site.addsitedir(str(ROOT/'builddeps'))
os.environ['PYTHONPATH']=os.pathsep.join(sys.path)
from mcp_server import serve
opts=serve(request={'tool':'get_options'})
assert 'background' in opts['options_schema']['properties']['cpu_mode']['enum']
assert opts['options_schema']['properties']['cpu_cores']['default'] is None
request=ROOT/'feedback-request.json'; response=ROOT/'feedback-response.json'
request.write_text(json.dumps({'tool':'get_options'}))
subprocess.run([sys.executable,str(ROOT/'app.py'),'--api',str(request),str(response)],check=True)
assert json.loads(response.read_text('utf8'))['ok']
description=subprocess.check_output([sys.executable,str(ROOT/'app.py'),'--describe'])
assert json.loads(description)['capabilities']['options_schema']
job=serve(request={'tool':'scan_folder','arguments':dict(source=str(ROOT/'test-input'),output=str(ROOT/f'feedback-output-{os.getpid()}'),options=dict(deinterlace=True,method='BWDIF',cpu_mode='background',limit=1))})
for _ in range(100):
    status=serve(request={'tool':'get_job_status','arguments':{'job_id':job['id']}})
    if not status['running']: break
    time.sleep(.2)
assert status['completion']['event']=='plan',status
assert status['completion']['jobs'],status
render=serve(request={'tool':'start_processing','arguments':{'scan_id':job['id']}})
for _ in range(200):
    status=serve(request={'tool':'get_job_status','arguments':{'job_id':render['id']}})
    if not status['running']: break
    time.sleep(.2)
assert status['completion']['event']=='done',status
assert status['completion'].get('failed',0)==0,status
print('API describe, schema, scan, processing and background BWDIF: PASS')

async def check_mcp():
    from mcp import ClientSession, StdioServerParameters
    from mcp.client.stdio import stdio_client
    clean_env={key:value for key,value in os.environ.items() if key.upper()!='PYTHONPATH'}
    params=StdioServerParameters(command=str(Path(sys.executable).with_name('pythonw.exe')),args=[str(ROOT/'app.py'),'--mcp'],env=clean_env)
    async with stdio_client(params) as (read,write):
        async with ClientSession(read,write) as session:
            await session.initialize()
            tools=await session.list_tools()
            assert len(tools.tools)==9
            result=await session.call_tool('get_options',{})
            assert not result.isError
    print('Standard MCP handshake, nine tools and options without PYTHONPATH: PASS')
asyncio.run(check_mcp())

from app import Studio
ui=Studio()
ui.update()
ui.cpu.set(ui.t('Hintergrund / Spielen'))
ui.switch_language(); ui.update()
assert ui.cpu.get()=='Background / Gaming'
ui.switch_language(); ui.update()
assert ui.cpu.get()=='Hintergrund / Spielen'
ui.show_review(); ui.update()
ui.tabs.set(ui.t('Datumsfunde')); ui.update()
assert ui.copy_prompt_button.winfo_ismapped()
assert ui.language_button.winfo_height()==ui.mcp_button.winfo_height()
ui.destroy()
print('DE/EN/DE settings retained; result actions accessible; header: PASS')
