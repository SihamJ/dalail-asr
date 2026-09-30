"""A static server that answers byte ranges (206), so a browser can jump
inside a long audio file. `python3 new/rangeserve.py PORT` serves the
current directory."""
import http.server, os, re, sys
class H(http.server.SimpleHTTPRequestHandler):
    def log_message(self,*a): pass
    def send_head(self):
        path=self.translate_path(self.path)
        if os.path.isdir(path) or not os.path.exists(path): return super().send_head()
        size=os.path.getsize(path); rng=self.headers.get('Range')
        f=open(path,'rb'); ctype=self.guess_type(path)
        m=re.match(r'bytes=(\d*)-(\d*)',rng or '')
        if not m:
            self.send_response(200); self.send_header('Content-Type',ctype); self.send_header('Content-Length',str(size)); self.send_header('Accept-Ranges','bytes'); self.end_headers(); return f
        a=int(m.group(1)) if m.group(1) else size-int(m.group(2)); b=int(m.group(2)) if m.group(1) and m.group(2) else size-1
        b=min(b,size-1); f.seek(a); self.send_response(206)
        self.send_header('Content-Type',ctype); self.send_header('Accept-Ranges','bytes')
        self.send_header('Content-Range',f'bytes {a}-{b}/{size}'); self.send_header('Content-Length',str(b-a+1)); self.end_headers()
        self._left=b-a+1; return f
    def copyfile(self, src, dst):
        left=getattr(self,'_left',None)
        while True:
            n=65536 if left is None else min(65536,left)
            if n<=0: break
            buf=src.read(n)
            if not buf: break
            try: dst.write(buf)
            except (BrokenPipeError, ConnectionResetError): break
            if left is not None: left-=len(buf)
http.server.ThreadingHTTPServer(('127.0.0.1',int(sys.argv[1])),H).serve_forever()
