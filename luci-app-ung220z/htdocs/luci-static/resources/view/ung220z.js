// SPDX-License-Identifier: GPL-3.0-only
// UNG220Z: probe an ONT and extract its credentials from the router.

'use strict';
'require view';
'require ubus';
'require ui';

var POLL_INTERVAL = 2000;
var POLL_DEADLINE = 150000;

function field(label, control, help) {
	var cell = E('div', { 'class': 'cbi-value-field' }, [ control ]);
	if (help)
		cell.appendChild(E('div', { 'class': 'cbi-value-description' }, help));
	return E('div', { 'class': 'cbi-value' }, [
		E('label', { 'class': 'cbi-value-title' }, label),
		cell
	]);
}

function textInput(id, value, type) {
	return E('input', {
		'id': id,
		'class': 'cbi-input-text',
		'type': type || 'text',
		'value': value || ''
	});
}

function credRow(label, user, pass, note) {
	var passCell = E('code', { 'class': 'ung220z-pass' }, pass || '—');
	var copyBtn = E('button', {
		'class': 'cbi-button cbi-button-neutral ung220z-copy',
		'click': function(ev) {
			ev.preventDefault();
			if (!pass)
				return;
			var done = function() { ui.addNotification(null, E('p', _('Copied to clipboard')), 'info'); };
			if (navigator.clipboard && navigator.clipboard.writeText)
				navigator.clipboard.writeText(pass).then(done, done);
		}
	}, _('Copy'));
	return E('tr', {}, [
		E('td', {}, label),
		E('td', {}, user || '—'),
		E('td', {}, [ passCell ]),
		E('td', {}, [ copyBtn ]),
		E('td', { 'class': 'ung220z-note' }, note || '')
	]);
}

function renderCredentials(box, res) {
	var rows = [];
	var labels = {
		'telnet': _('Telnet / root shell'),
		'web_admin': _('Web admin'),
		'web_user': _('Web user'),
		'pppoe': _('PPPoE broadband'),
		'root': _('Linux root')
	};
	Object.keys(labels).forEach(function(key) {
		var c = res.credentials && res.credentials[key];
		if (!c)
			return;
		if (key === 'root') {
			if (c.cracked)
				rows.push(credRow(labels[key], c.user, c.password));
			else
				rows.push(credRow(labels[key], c.user, (c.hash || '').slice(0, 32) + '…',
					_('Not cracked (common passwords did not match)')));
			return;
		}
		rows.push(credRow(labels[key], c.user, c.password));
	});
	(res.wifi || []).forEach(function(w) {
		rows.push(credRow(_('WiFi %s').format(w.ssid), '', w.psk,
			w.factory_placeholder ? _('Factory placeholder') : ''));
	});
	(res.telnet_users || []).forEach(function(t) {
		rows.push(credRow(_('Telnet user %s').format(t.user || ''), t.user, t.password,
			t.type ? 'Type=' + t.type : ''));
	});

	var table = E('table', { 'class': 'table' }, [
		E('tr', { 'class': 'tr table-titles' }, [
			E('th', { 'class': 'th' }, _('Item')),
			E('th', { 'class': 'th' }, _('Username')),
			E('th', { 'class': 'th' }, _('Password')),
			E('th', { 'class': 'th' }, ''),
			E('th', { 'class': 'th' }, '')
		]),
		rows
	]);
	var toggle = E('button', {
		'class': 'cbi-button cbi-button-neutral',
		'click': function(ev) {
			ev.preventDefault();
			var hidden = box.classList.toggle('ung220z-masked');
			ev.target.textContent = hidden ? _('Show passwords') : _('Hide passwords');
		}
	}, _('Hide passwords'));

	box.appendChild(E('h3', {}, _('Credentials for %s').format(res.ip || '')));
	box.appendChild(E('p', {}, _('Passwords rotate about every 15 minutes (TR-069); re-run to fetch fresh ones.')));
	box.appendChild(toggle);
	box.appendChild(table);
	box.classList.add('ung220z-masked');
}

function renderProbe(box, res) {
	var hits = (res.hits || []).join(' / ') || _('Unrecognized');
	box.appendChild(E('h3', {}, _('Fingerprint')));
	box.appendChild(E('p', {}, _('Server: %s, Title: %s, Family: %s')
		.format(res.server || '-', res.title || '-', hits)));
	if (res.hits && res.hits.length) {
		var isGch = res.hits.some(function(h) { return h.indexOf('.gch') !== -1 || h.indexOf('GoAhead') !== -1; });
		box.appendChild(E('p', {}, isGch
			? _('Looks like a .gch device; UNG220Z extraction may work.')
			: _('Not a .gch device; UNG220Z extraction does not apply. Try ontkit (ZTE/Huawei/FiberHome) instead.')));
	}
}

return view.extend({
	load: function() {
		return null;
	},

	render: function() {
		var ipInput = textInput('ung220z-ip', '192.168.1.1');
		var userInput = textInput('ung220z-user', 'user');
		var passInput = textInput('ung220z-pass', '', 'password');
		var probeBox = E('div', { 'id': 'ung220z-probe' });
		var resultBox = E('div', { 'id': 'ung220z-result' });
		var statusBox = E('div', { 'id': 'ung220z-status' });
		var busy = false;

		function setBusy(v) {
			busy = v;
			probeBtn.disabled = v;
			extractBtn.disabled = v;
		}

		function showStatus(msg) {
			statusBox.textContent = '';
			if (msg)
				statusBox.appendChild(E('p', {}, msg));
		}

		var probeBtn = E('button', {
			'class': 'cbi-button cbi-button-action',
			'click': function(ev) {
				ev.preventDefault();
				if (busy)
					return;
				var ip = ipInput.value.trim();
				if (!ip) {
					ui.addNotification(null, E('p', _('Please enter the ONT address')), 'warning');
					return;
				}
				setBusy(true);
				showStatus(_('Probing…'));
				probeBox.textContent = '';
				ubus.call('ung220z', 'probe', { 'ip': ip }).then(function(res) {
					setBusy(false);
					showStatus('');
					if (!res || res.ok === false) {
						ui.addNotification(null, E('p', (res && res.error) || _('Probe failed')), 'warning');
						return;
					}
					renderProbe(probeBox, res);
				}, function(err) {
					setBusy(false);
					showStatus('');
					ui.addNotification(null, E('p', _('Probe failed: %s').format(err.message || err)), 'warning');
				});
			}
		}, _('Probe'));

		var extractBtn = E('button', {
			'class': 'cbi-button cbi-button-action important',
			'click': function(ev) {
				ev.preventDefault();
				if (busy)
					return;
				var ip = ipInput.value.trim();
				var user = userInput.value.trim();
				var pass = passInput.value;
				if (!ip || !user || !pass) {
					ui.addNotification(null, E('p', _('Please fill in the ONT address, username and password')), 'warning');
					return;
				}
				setBusy(true);
				showStatus(_('Extracting credentials, this may take up to a minute…'));
				resultBox.textContent = '';
				var deadline = Date.now() + POLL_DEADLINE;
				ubus.call('ung220z', 'extract', { 'ip': ip, 'user': user, 'password': pass }).then(function(res) {
					if (!res || res.ok === false || !res.job_id) {
						setBusy(false);
						showStatus('');
						ui.addNotification(null, E('p', (res && (res.message || res.error)) || _('Failed to start extraction')), 'warning');
						return;
					}
					var jobId = res.job_id;
					var poll = function() {
						ubus.call('ung220z', 'job_status', { 'job_id': jobId }).then(function(st) {
							if (st && st.running) {
								if (Date.now() > deadline) {
									setBusy(false);
									showStatus('');
									ui.addNotification(null, E('p', _('Timed out waiting for the extraction job')), 'warning');
									return;
								}
								setTimeout(poll, POLL_INTERVAL);
								return;
							}
							setBusy(false);
							showStatus('');
							if (!st || st.ok === false) {
								ui.addNotification(null, E('p', (st && (st.error || st.message)) || _('Extraction failed')), 'warning');
								return;
							}
							renderCredentials(resultBox, st);
						}, function(err) {
							setBusy(false);
							showStatus('');
							ui.addNotification(null, E('p', _('Job check failed: %s').format(err.message || err)), 'warning');
						});
					};
					setTimeout(poll, POLL_INTERVAL);
				}, function(err) {
					setBusy(false);
					showStatus('');
					ui.addNotification(null, E('p', _('Failed to start extraction: %s').format(err.message || err)), 'warning');
				});
			}
		}, _('Extract credentials'));

		return E('div', { 'class': 'cbi-map' }, [
			E('h2', {}, _('UNG220Z')),
			E('div', { 'class': 'cbi-map-descr' }, _('Extract credentials from your own ONT (UNG220Z and other .gch devices): Web admin, Telnet, PPPoE and WiFi passwords. The router must be able to reach the ONT address (usually 192.168.1.1 on the WAN side). Results are shown here only and are not stored on the router.')),
			E('div', { 'class': 'cbi-section' }, [
				field(_('ONT address'), ipInput, _('Usually 192.168.1.1. The ONT sits on the WAN side; the router needs a route to it.')),
				field(_('Username'), userInput, _('Printed on the sticker on the ONT, usually "user".')),
				field(_('Password'), passInput, _('Printed on the sticker on the ONT.')),
				E('div', { 'class': 'cbi-value' }, [
					E('div', { 'class': 'cbi-value-field' }, [ probeBtn, ' ', extractBtn ])
				]),
				statusBox,
				probeBox,
				resultBox
			])
		]);
	},

	handleSaveApply: null,
	handleSave: null,
	handleReset: null
});
