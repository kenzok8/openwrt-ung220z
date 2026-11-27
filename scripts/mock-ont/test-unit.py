#!/usr/bin/env python3
"""Unit test for the vendored ung220z.py -- no network, no servers.

Stubs the HTTP/Telnet layers and drives main() directly, so the
JSON-mode paths (probe 404 -> exit 3, full extract -> exit 0) can be
checked without binding privileged ports. The mock end-to-end test
(run-test.sh) covers the same paths against real sockets.
"""
import importlib.util
import io
import json
import subprocess
import sys

TOOL = sys.argv[1] if len(sys.argv) > 1 else "ung220z-tool/files/usr/bin/ung220z"

XML = """<Tbl name="DevAuthInfo"><Row No="0"><DM name="User" val="CMCCAdmin"/><DM name="Pass" val="superpass"/><DM name="Level" val="1"/></Row><Row No="1"><DM name="User" val="user"/><DM name="Pass" val="userpass"/><DM name="Level" val="0"/></Row></Tbl><Tbl name="TelnetUser"><Row No="0"><DM name="Username" val="CMCCAdmin"/><DM name="Password" val="telnetpass"/><DM name="Type" val="1"/></Row></Tbl><Tbl name="WANCPPP"><Row No="0"><DM name="UserName" val="pppoeuser"/><DM name="Password" val="pppoepass"/></Row></Tbl><Tbl name="WLANCfg"><Row No="0"><DM name="ESSID" val="MyWiFi"/><DM name="ViewName" val="wl0"/></Row></Tbl><Tbl name="WLANPSK"><Row No="0"><DM name="KeyPassphrase" val="wifipass123"/><DM name="ViewName" val="wl0.PSK"/></Row></Tbl><DM name="TS_UPwd" val="telnetpass"/>"""

ROOT_HASH = subprocess.run(
    ["openssl", "passwd", "-6", "-salt", "testsalt", "admin"],
    capture_output=True, text=True, check=True).stdout.strip()


def load_module():
    # The vendored file has no .py suffix, so give the loader explicitly.
    from importlib.machinery import SourceFileLoader
    spec = importlib.util.spec_from_loader("ung220z", SourceFileLoader("ung220z", TOOL))
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def run_main(m, argv):
    sys.argv = argv
    buf = io.StringIO()
    old = sys.stdout
    sys.stdout = buf
    try:
        code = m.main()
    finally:
        sys.stdout = old
    return code, buf.getvalue()


class FakeTelnet:
    def __init__(self, ip, port=23, timeout=8):
        pass

    def login(self, user, passwords):
        return True

    def run(self, cmd, timeout=15):
        if cmd.startswith("id"):
            return "uid=0(root) gid=0(root)"
        if cmd.startswith("uname -a"):
            return "Linux ung220z 4.9.0 #1 SMP mock"
        if cmd.startswith("sidbg 1 DB decry"):
            return ""
        if cmd.startswith("wc -c "):
            return str(len(XML))
        if cmd.startswith("cat "):
            return XML
        if cmd.startswith("test -s "):
            return "__OK__"
        if cmd.startswith("grep root /etc/shadow"):
            return "root:%s:18000:0:99999:7:::" % ROOT_HASH
        if cmd.startswith("rm -f "):
            return ""
        return ""

    def close(self):
        pass


def test_404():
    """telnet.gch answers 404 (body 'Not Found'), no telnet listener."""
    m = load_module()
    m.http_get = lambda url, timeout=8: "Not Found"
    m.http_post = lambda url, data, timeout=8: (200, "ok")
    m.probe_port = lambda ip, port, timeout=3: port == 80
    m.release_session = lambda ip: True
    code, out = run_main(m, ["ung220z", "--json", "--no-browser",
                             "-i", "127.0.0.3", "-u", "user", "-p", "x"])
    d = json.loads(out)
    assert code == 3, (code, out)
    assert d == {"ok": False, "code": 3, "error": "Telnet 端口未开放"}, d
    print("PASS: telnet.gch 404 -> exit 3")


def test_full_extract():
    """Full path with a fake telnet shell: all credential tables present."""
    m = load_module()
    m.http_get = lambda url, timeout=8: "TelnetSet Success!" if "telnet.gch" in url else "<html><title>UNG220Z</title></html>"
    m.http_post = lambda url, data, timeout=8: (200, "ok")
    m.probe_port = lambda ip, port, timeout=3: True
    m.release_session = lambda ip: True
    m.web_recon = lambda ip, user, pw: []
    m.Telnet = FakeTelnet
    code, out = run_main(m, ["ung220z", "--json", "--no-browser",
                             "-i", "127.0.0.1", "-u", "user", "-p", "userpass"])
    assert out.count("\n") == 1, "stdout must be exactly one JSON line"
    d = json.loads(out)
    assert code == 0, (code, out)
    assert d["ok"] is True
    assert d["credentials"]["telnet"] == {"user": "CMCCAdmin", "password": "telnetpass"}, d
    assert d["credentials"]["web_admin"] == {"user": "CMCCAdmin", "password": "superpass"}, d
    assert d["credentials"]["web_user"] == {"user": "user", "password": "userpass"}, d
    assert d["credentials"]["pppoe"] == {"user": "pppoeuser", "password": "pppoepass"}, d
    assert d["credentials"]["root"]["cracked"] is True
    assert d["credentials"]["root"]["password"] == "admin", d
    assert d["wifi"] == [{"ssid": "MyWiFi", "psk": "wifipass123", "factory_placeholder": False}], d
    assert d["telnet_users"] == [{"user": "CMCCAdmin", "password": "telnetpass", "type": "1"}], d
    print("PASS: full extract -> exit 0, all credential tables correct")


if __name__ == "__main__":
    test_404()
    test_full_extract()
    print("ALL UNIT TESTS PASSED")
