#!/usr/bin/env python3
"""Mock ONT for end-to-end testing of the vendored ung220z.py.

Simulates a UNG220Z-like .gch device on a loopback address:
  HTTP :80  -- login page, telnet.gch, WebSession pages
  TCP  :23  -- Telnet root shell with sidbg / config decrypt

Usage:
  mock_ont.py --ip 127.0.0.1 [--404-telnet] [--no-telnet]
    --404-telnet : telnet.gch answers 404 (non-.gch firmware)
    --no-telnet  : do not listen on :23 (telnet.gch succeeds but no listener)

The canned config contains known credentials; run-test.sh asserts them.
"""
import argparse
import http.server
import socket
import socketserver
import subprocess
import threading

XML = """<Tbl name="DevAuthInfo"><Row No="0"><DM name="User" val="CMCCAdmin"/><DM name="Pass" val="superpass"/><DM name="Level" val="1"/></Row><Row No="1"><DM name="User" val="user"/><DM name="Pass" val="userpass"/><DM name="Level" val="0"/></Row></Tbl><Tbl name="TelnetUser"><Row No="0"><DM name="Username" val="CMCCAdmin"/><DM name="Password" val="telnetpass"/><DM name="Type" val="1"/></Row></Tbl><Tbl name="WANCPPP"><Row No="0"><DM name="UserName" val="pppoeuser"/><DM name="Password" val="pppoepass"/></Row></Tbl><Tbl name="WLANCfg"><Row No="0"><DM name="ESSID" val="MyWiFi"/><DM name="ViewName" val="wl0"/></Row></Tbl><Tbl name="WLANPSK"><Row No="0"><DM name="KeyPassphrase" val="wifipass123"/><DM name="ViewName" val="wl0.PSK"/></Row></Tbl><DM name="TS_UPwd" val="telnetpass"/>"""

LOGIN_PAGE = ('<html><head><title>UNG220Z</title></head><body>'
              '<form>boaform Frm_Logintoken").value = "12345"'
              '<input name="logincode"></form></body></html>')
LOGIN_OK = '<html><body>' + 'x' * 6000 + '</body></html>'

MANAGER_PAGE = ('<html><body>'
                "Transfer_meaning('Username','CMCCAdmin');"
                "Transfer_meaning('InitialPassword','superpass');"
                "Transfer_meaning('Right','1');"
                '</body></html>')
TELNET_PAGE = ('<html><body>'
               "Transfer_meaning('TS_UName','CMCCAdmin');"
               "Transfer_meaning('TS_UPwd','telnetpass');"
               '</body></html>')

ARGS = None
ROOT_HASH = None


class Handler(http.server.BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def version_string(self):
        # BaseHTTPRequestHandler would otherwise send its own Server header.
        return "GoAhead"

    def log_message(self, *a):
        pass

    def _send(self, body, code=200, ctype="text/html; charset=utf-8"):
        data = body.encode()
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        if "telnet.gch" in self.path:
            if ARGS.f404_telnet:
                self._send("Not Found", code=404)
            else:
                self._send("TelnetSet Success!")
            return
        if "tele_sec_tserver_t.gch" in self.path:
            self._send(TELNET_PAGE)
            return
        if "manager_aduser_conf_t.gch" in self.path:
            self._send(MANAGER_PAGE)
            return
        self._send(LOGIN_PAGE)

    def do_POST(self):
        length = int(self.headers.get("Content-Length") or 0)
        self.rfile.read(length)
        if "setlang.gch" in self.path:
            self._send("ok")
            return
        # Web login form post: a page without logincode, longer than 5000.
        self._send(LOGIN_OK)


def _readline(conn, buf):
    while b"\n" not in buf:
        chunk = conn.recv(4096)
        if not chunk:
            return None, buf
        buf += chunk
    line, buf = buf.split(b"\n", 1)
    return line.decode("utf-8", "replace").rstrip("\r"), buf


def telnet_session(conn):
    buf = b""
    try:
        conn.sendall(b"login: ")
        user, buf = _readline(conn, buf)
        if user is None:
            return
        conn.sendall(b"Password: ")
        pw, buf = _readline(conn, buf)
        if pw is None:
            return
        conn.sendall(b"/ # ")
        while True:
            line, buf = _readline(conn, buf)
            if line is None:
                return
            cmd = line.strip()
            if cmd.startswith("echo __X__"):
                conn.sendall(b"__X__\n/ # ")
            elif cmd.startswith("id"):
                conn.sendall(b"uid=0(root) gid=0(root)\n/ # ")
            elif cmd.startswith("uname -a"):
                conn.sendall(b"Linux ung220z 4.9.0 #1 SMP mock\n/ # ")
            elif cmd.startswith("sidbg 1 DB decry"):
                conn.sendall(b"/ # ")
            elif cmd.startswith("wc -c "):
                conn.sendall(("%d\n/ # " % len(XML)).encode())
            elif cmd.startswith("cat "):
                conn.sendall(XML.encode() + b"\n/ # ")
            elif cmd.startswith("test -s "):
                conn.sendall(b"__OK__\n/ # ")
            elif cmd.startswith("grep root /etc/shadow"):
                conn.sendall(("root:%s:18000:0:99999:7:::\n/ # " % ROOT_HASH).encode())
            elif cmd.startswith("rm -f "):
                conn.sendall(b"/ # ")
            elif cmd.startswith("ps"):
                conn.sendall(b"  123 root     httpd\n/ # ")
            else:
                conn.sendall(b"/ # ")
    except (BrokenPipeError, ConnectionResetError, OSError):
        pass
    finally:
        try:
            conn.close()
        except OSError:
            pass


def serve_telnet(ip):
    srv = socketserver.ThreadingTCPServer((ip, 23), socketserver.BaseRequestHandler)
    srv.daemon_threads = True

    class H(socketserver.BaseRequestHandler):
        def handle(self):
            telnet_session(self.request)

    srv.RequestHandlerClass = H
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv


def main():
    global ARGS, ROOT_HASH
    ap = argparse.ArgumentParser()
    ap.add_argument("--ip", default="127.0.0.1")
    ap.add_argument("--404-telnet", dest="f404_telnet", action="store_true")
    ap.add_argument("--no-telnet", action="store_true")
    ARGS = ap.parse_args()
    ROOT_HASH = subprocess.run(
        ["openssl", "passwd", "-6", "-salt", "testsalt", "admin"],
        capture_output=True, text=True, check=True).stdout.strip()
    print("mock ONT on %s (root hash for 'admin': %s)" % (ARGS.ip, ROOT_HASH[:20]), flush=True)
    httpd = http.server.ThreadingHTTPServer((ARGS.ip, 80), Handler)
    httpd.daemon_threads = True
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    if not ARGS.no_telnet:
        serve_telnet(ARGS.ip)
    try:
        import time
        while True:
            time.sleep(3600)
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
