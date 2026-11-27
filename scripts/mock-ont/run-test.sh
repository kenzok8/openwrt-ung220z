#!/bin/sh
# SPDX-License-Identifier: GPL-3.0-only
# End-to-end test of the vendored ung220z.py against mock ONTs.
# Usage: bash scripts/mock-ont/run-test.sh
# Spins up mock_ont.py on loopback addresses (needs root for :80/:23),
# runs probe/extract scenarios, asserts the JSON output. Exits non-zero
# on the first failure.
set -u
REPO_DIR=$(CDPATH= cd -- "$(dirname -- "$0")/../.." && pwd)
TOOL="$REPO_DIR/ung220z-tool/files/usr/bin/ung220z"
MOCK="$REPO_DIR/scripts/mock-ont/mock_ont.py"
WORK=$(mktemp -d)
trap 'kill $M1 $M3 2>/dev/null; rm -rf "$WORK"' EXIT INT TERM

pass() { echo "PASS: $1"; }
fail() { echo "FAIL: $1"; exit 1; }

check_json() { # $1=file $2=python-expr-on-d
	python3 -c "import json,sys; d=json.load(open('$1')); assert $2, d; sys.exit(0)" \
		|| fail "$3 (see $1)"
}

echo "--- starting mocks ---"
python3 "$MOCK" --ip 127.0.0.1 > "$WORK/m1.log" 2>&1 &
M1=$!
python3 "$MOCK" --ip 127.0.0.3 --404-telnet --no-telnet > "$WORK/m3.log" 2>&1 &
M3=$!
sleep 1
grep -q "mock ONT on 127.0.0.1" "$WORK/m1.log" || { cat "$WORK/m1.log"; fail "mock 127.0.0.1 did not start"; }
grep -q "mock ONT on 127.0.0.3" "$WORK/m3.log" || { cat "$WORK/m3.log"; fail "mock 127.0.0.3 did not start"; }

echo "--- 1. probe (reachable, .gch) ---"
"$TOOL" --json --probe -i 127.0.0.1 > "$WORK/p1.out" 2> "$WORK/p1.err"
[ $? -eq 0 ] || fail "probe exit code"
check_json "$WORK/p1.out" "d['ok'] and d['reachable'] and d['server']=='GoAhead' and d['title']=='UNG220Z' and any('GoAhead' in h for h in d['hits'])" "probe JSON"
# stdout must be exactly one JSON object (logs go to stderr)
[ "$(wc -l < "$WORK/p1.out")" -eq 1 ] || fail "probe stdout is not a single line"
pass "probe 127.0.0.1"

echo "--- 2. probe (unreachable) ---"
"$TOOL" --json --probe -i 127.0.0.2 > "$WORK/p2.out" 2> "$WORK/p2.err"
[ $? -eq 2 ] || fail "unreachable probe exit code (want 2)"
check_json "$WORK/p2.out" "d['ok'] is False and d['code']==2" "unreachable probe JSON"
pass "probe 127.0.0.2 -> code 2"

echo "--- 3. extract (telnet.gch 404, no telnet) ---"
printf 'x' > "$WORK/pw3"
"$TOOL" --json --no-browser -i 127.0.0.3 -u user --password-file "$WORK/pw3" > "$WORK/p3.out" 2> "$WORK/p3.err"
[ $? -eq 3 ] || fail "404 extract exit code (want 3)"
check_json "$WORK/p3.out" "d['ok'] is False and d['code']==3" "404 extract JSON"
pass "extract 127.0.0.3 -> code 3"

echo "--- 4. full extract (mock UNG220Z) ---"
printf 'userpass' > "$WORK/pw"
cd "$WORK" || exit 1
"$TOOL" --json --no-browser -i 127.0.0.1 -u user --password-file "$WORK/pw" > "$WORK/p4.out" 2> "$WORK/p4.err"
code=$?
[ $code -eq 0 ] || { echo "exit=$code"; cat "$WORK/p4.err"; fail "full extract exit code (want 0)"; }
[ "$(wc -l < "$WORK/p4.out")" -eq 1 ] || fail "extract stdout is not a single JSON line"
check_json "$WORK/p4.out" "d['ok'] and d['credentials']['telnet']=={'user':'CMCCAdmin','password':'telnetpass'}" "telnet creds"
check_json "$WORK/p4.out" "d['credentials']['web_admin']=={'user':'CMCCAdmin','password':'superpass'}" "web_admin creds"
check_json "$WORK/p4.out" "d['credentials']['web_user']=={'user':'user','password':'userpass'}" "web_user creds"
check_json "$WORK/p4.out" "d['credentials']['pppoe']=={'user':'pppoeuser','password':'pppoepass'}" "pppoe creds"
check_json "$WORK/p4.out" "d['credentials']['root']['cracked'] is True and d['credentials']['root']['password']=='admin'" "root cracked"
check_json "$WORK/p4.out" "d['wifi']==[{'ssid':'MyWiFi','psk':'wifipass123','factory_placeholder':False}]" "wifi creds"
check_json "$WORK/p4.out" "d['telnet_users']==[{'user':'CMCCAdmin','password':'telnetpass','type':'1'}]" "telnet_users"
# JSON mode must not write a log file, and the password file must be gone.
ls ung220z_*.log 2>/dev/null | grep -q . && fail "JSON mode wrote a log file"
[ -e "$WORK/pw" ] && fail "password file was not removed after reading"
pass "full extract 127.0.0.1"

echo "--- 5. JSON mode without password ---"
"$TOOL" --json --no-browser -i 127.0.0.1 -u user > "$WORK/p5.out" 2> "$WORK/p5.err"
[ $? -eq 1 ] || fail "missing-password exit code (want 1)"
check_json "$WORK/p5.out" "d['ok'] is False and d['code']==1" "missing-password JSON"
pass "missing password -> code 1"

echo "ALL TESTS PASSED"
