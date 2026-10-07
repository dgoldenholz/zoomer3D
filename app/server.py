"""Local drawing studio and bounded training-job API. Run from any directory."""
from http.server import ThreadingHTTPServer,SimpleHTTPRequestHandler
from pathlib import Path
import argparse,json,os,re,signal,subprocess,sys,threading,uuid
from urllib.parse import urlparse
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'simulation'))
from drawing import validate_drawing
RUNS={};LOCK=threading.Lock();SAFE=re.compile(r'^[a-f0-9]{32}$')

class Handler(SimpleHTTPRequestHandler):
    def __init__(self,*a,**kw):super().__init__(*a,directory=str(ROOT/'app'),**kw)
    def response(self,data,status=200):
        body=json.dumps(data,allow_nan=False).encode();self.send_response(status)
        self.send_header('Content-Type','application/json');self.send_header('Content-Length',str(len(body)))
        self.send_header('Cache-Control','no-store');self.end_headers();self.wfile.write(body)
    def do_GET(self):
        path=urlparse(self.path).path
        if path.startswith('/api/run/'):
            run_id=path.split('/')[-1]
            if not SAFE.fullmatch(run_id):return self.response({'error':'Unknown run'},404)
            status=ROOT/'training'/run_id/'status.json'
            if run_id not in RUNS and not status.parent.exists():return self.response({'error':'Unknown run'},404)
            if not status.exists():return self.response({'status':'running','stage':'starting'})
            data=json.loads(status.read_text());process=RUNS.get(run_id)
            if process and process.poll() is not None and data.get('status')=='running':data.update(status='failed',error='Training process exited. See run.log.')
            return self.response(data)
        if path.startswith('/api/'):return self.response({'error':'Unknown endpoint'},404)
        return super().do_GET()
    def do_POST(self):
        try:
            # Only the locally served studio may launch a job. Do not accept a
            # cross-site form POST or a request with a foreign Host header.
            expected=f'127.0.0.1:{self.server.server_port}'
            if self.headers.get('Host') not in [expected,f'localhost:{self.server.server_port}']:return self.response({'error':'Invalid host'},403)
            origin=self.headers.get('Origin')
            if origin and origin not in ['http://'+expected,f'http://localhost:{self.server.server_port}']:return self.response({'error':'Invalid origin'},403)
            if self.headers.get_content_type()!='application/json':return self.response({'error':'JSON required'},415)
            length=int(self.headers.get('Content-Length','0'))
            if not 0<length<=2_000_000:return self.response({'error':'Request too large or empty'},413)
            value=json.loads(self.rfile.read(length));path=urlparse(self.path).path
            if path in ['/api/validate','/api/targets']:
                clean=validate_drawing(value)
                if path=='/api/validate':return self.response(clean)
                target_id=uuid.uuid4().hex;(ROOT/'targets'/f'{target_id}.json').write_text(json.dumps(clean,indent=2))
                return self.response(dict(id=target_id,drawing=clean),201)
            if path=='/api/train':
                target=value.get('target_id','');steps=value.get('steps')
                if not SAFE.fullmatch(target) or not (ROOT/'targets'/f'{target}.json').exists():raise ValueError('Save a target first.')
                if type(steps) is not int or steps not in [4096,100000,1000000]:raise ValueError('Invalid training budget.')
                with LOCK:
                    if any(p.poll() is None for p in RUNS.values()):return self.response({'error':'A training job is already running.'},409)
                    run_id=uuid.uuid4().hex;out=ROOT/'training'/run_id;out.mkdir()
                    (out/'status.json').write_text(json.dumps(dict(status='running',stage='starting')))
                    with (out/'run.log').open('w') as log:
                        RUNS[run_id]=subprocess.Popen([sys.executable,str(ROOT/'simulation/train.py'),'--drawing',str(ROOT/'targets'/f'{target}.json'),'--output',str(out),'--steps',str(steps)],cwd=ROOT,stdout=log,stderr=subprocess.STDOUT)
                return self.response(dict(id=run_id),202)
            if path=='/api/stop':
                run_id=value.get('id');process=RUNS.get(run_id)
                if process and process.poll() is None:
                    (ROOT/'training'/run_id/'stop_requested').touch()
                    if (ROOT/'training'/run_id/'checkpoint.zip').exists():process.send_signal(signal.SIGTERM)
                return self.response(dict(stopping=True))
            return self.response({'error':'Unknown endpoint'},404)
        except (ValueError,TypeError,KeyError) as error:return self.response({'error':str(error)},400)

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--port',type=int,default=8765);args=parser.parse_args()
    server=ThreadingHTTPServer(('127.0.0.1',args.port),Handler)
    print(f'Zoomer drawing studio: http://127.0.0.1:{args.port}',flush=True)
    try:server.serve_forever()
    except KeyboardInterrupt:pass
    finally:
        for p in RUNS.values():
            if p.poll() is None:p.send_signal(signal.SIGTERM)
        server.server_close()
