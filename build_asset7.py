src = open('../incoming_files/d06c59d92_volpam-quickswitch_UI-polished201.html', encoding='utf-8').read()

# ---- 2s gesture timer (this build ships 5s) ----
repls = [
    ("hold <strong>Full Throttle for 5 seconds</strong>", "hold <strong>Full Throttle for 2 seconds</strong>"),
    ('">0.0s / 5.0s</span>', '">0.0s / 2.0s</span>'),
    ("pin throttle for 5s to lock", "pin throttle for 2s to lock"),
    ("\u26a1 Test 5s Demo", "\u26a1 Test 2s Demo"),
    ("[Eco 5s Gesture]", "[Eco 2s Gesture]"),
    ("(elapsed / 5.0) * 100", "(elapsed / 2.0) * 100"),
    ("Math.min(5.0, elapsed).toFixed(1) + \"s / 5.0s\"", "Math.min(2.0, elapsed).toFixed(1) + \"s / 2.0s\""),
    ("(5.0 - elapsed).toFixed(1)}s remaining!", "(2.0 - elapsed).toFixed(1)}s remaining!"),
    ("elapsed >= 5.0", "elapsed >= 2.0"),
]
for old, new in repls:
    assert src.count(old) > 0, "missing: " + old
    src = src.replace(old, new)
src = src.replace('textContent = "0.0s / 5.0s"', 'textContent = "0.0s / 2.0s"')
src = src.replace('textContent = "5.0s / 5.0s - TRIGGERED!"', 'textContent = "2.0s / 2.0s - TRIGGERED!"')

# ---- GPS: state fields ----
old = """  trail: [], distKm: 0, lastFixAt: null
};"""
assert old in src
src = src.replace(old, """  trail: [], distKm: 0, lastFixAt: null,
  stops: [], batteryMarks: [], batterySeen: {}, lastBattery: null,
  stopStartAt: null, stopStartPt: null, stopRecorded: false, endPt: null
};""", 1)

# ---- GPS: reset session on start ----
old = """  gpsState.on = true;
  gpsToggleBtn.textContent = '■ Stop GPS';"""
assert old in src
src = src.replace(old, """  gpsState.on = true;
  gpsToggleBtn.textContent = '■ Stop GPS';
  gpsState.trail = []; gpsState.distKm = 0; gpsState.lat = null; gpsState.lon = null;
  gpsState.stops = []; gpsState.batteryMarks = []; gpsState.batterySeen = {};
  gpsState.lastBattery = null; gpsState.stopStartAt = null; gpsState.stopStartPt = null;
  gpsState.stopRecorded = false; gpsState.endPt = null;
  updateGpsEventsLine();""", 1)


# ---- GPS: use SCOOTER speed instead of GPS speed ----
old_speed = "gpsState.speedKmh = f.spd != null ? f.spd * 3.6 : null;"
assert old_speed in src
src = src.replace(old_speed, """const scooterKmh = (typeof isConnected !== 'undefined' && isConnected && scooterState.speed != null) ? scooterState.speed : null;
  gpsState.speedKmh = scooterKmh != null ? scooterKmh : (f.spd != null ? f.spd * 3.6 : null);""", 1)

old_lbl = "<span>GPS Speed</span>"
assert old_lbl in src
src = src.replace(old_lbl, "<span>Scooter Speed</span>", 1)

# ---- GPS: track events on each fix ----
old = """  gpsState.lastFixAt = Date.now();
  updateGpsUI();"""
assert old in src
src = src.replace(old, """  gpsState.lastFixAt = Date.now();
  trackGpsEvents(f);
  updateGpsUI();""", 1)

# ---- GPS: end point on stop ----
old = """  if (gpsState.demoTimer) { clearInterval(gpsState.demoTimer); gpsState.demoTimer = null; }
  setGpsPill('', 'GPS Off');"""
assert old in src
src = src.replace(old, """  if (gpsState.demoTimer) { clearInterval(gpsState.demoTimer); gpsState.demoTimer = null; }
  if (gpsState.lat !== null) { gpsState.endPt = [gpsState.lat, gpsState.lon]; drawGpsTrail(); }
  updateGpsEventsLine();
  setGpsPill('', 'GPS Off');""", 1)

# ---- GPS: events line under the canvas ----
old = '<canvas id="gpsTrail" class="gps-trail" width="412" height="120"></canvas>'
assert old in src
src = src.replace(old, old + """
    <div id="gpsEventsLine" style="font-size:9.5px;color:#c4b5d2;margin:-4px 0 9px;line-height:1.6;font-weight:700;letter-spacing:.2px"></div>""", 1)

# ---- GPS: marker drawing inside drawGpsTrail ----
old = """  // start dot (slime)
  ctx.fillStyle = '#a3e635';
  ctx.beginPath(); ctx.arc(px(t[0][1]), py(t[0][0]), 4.5, 0, Math.PI*2); ctx.fill();"""
assert old in src
src = src.replace(old, """  // ---- event markers: stops >20s, battery drops, end point ----
  (gpsState.stops || []).forEach(function (st) {
    const x = px(st.lon), y = py(st.lat);
    ctx.fillStyle = '#ef4444';
    ctx.beginPath(); ctx.arc(x, y, 4, 0, Math.PI * 2); ctx.fill();
    ctx.fillStyle = 'rgba(255,255,255,.95)';
    ctx.font = '700 7px "JetBrains Mono", monospace';
    ctx.textAlign = 'center';
    ctx.fillText(st.dur + 's', x, y - 6);
  });
  (gpsState.batteryMarks || []).forEach(function (bm) {
    const x = px(bm.lon), y = py(bm.lat);
    ctx.strokeStyle = '#38bdf8'; ctx.lineWidth = 1.5;
    ctx.beginPath(); ctx.arc(x, y, 3.5, 0, Math.PI * 2); ctx.stroke();
    ctx.fillStyle = 'rgba(186,230,253,.95)';
    ctx.font = '700 7px "JetBrains Mono", monospace';
    ctx.textAlign = 'center';
    ctx.fillText(bm.pct + '%', x, y + 12);
  });
  if (gpsState.endPt) {
    const ex = px(gpsState.endPt[1]), ey = py(gpsState.endPt[0]);
    ctx.strokeStyle = '#e2e8f0'; ctx.lineWidth = 1.5;
    ctx.strokeRect(ex - 3.5, ey - 3.5, 7, 7);
    ctx.fillStyle = 'rgba(226,232,240,.95)';
    ctx.font = '700 7px "JetBrains Mono", monospace';
    ctx.textAlign = 'center';
    ctx.fillText('END', ex, ey + 14);
  }
  // start dot (slime)
  ctx.fillStyle = '#a3e635';
  ctx.beginPath(); ctx.arc(px(t[0][1]), py(t[0][0]), 4.5, 0, Math.PI*2); ctx.fill();
  ctx.fillStyle = 'rgba(163,230,53,.95)';
  ctx.font = '700 7px "JetBrains Mono", monospace';
  ctx.textAlign = 'center';
  ctx.fillText('START', px(t[0][1]), py(t[0][0]) - 8);""", 1)

# ---- GPS: tracker functions ----
old = "function startGpsDemo() {"
assert old in src
tracker = '''function trackGpsEvents(f) {
  const now = Date.now();
  const hasScooterSpd = (typeof isConnected !== 'undefined' && isConnected && scooterState.speed != null);
  const spdKmh = hasScooterSpd ? scooterState.speed : ((f.spd != null && !isNaN(f.spd)) ? f.spd * 3.6 : 0);

  // ---- stops longer than 20 s ----
  if (spdKmh < 1.5) {
    if (gpsState.stopStartAt == null) {
      gpsState.stopStartAt = now;
      gpsState.stopStartPt = [f.lat, f.lon];
      gpsState.stopRecorded = false;
    } else if (!gpsState.stopRecorded && (now - gpsState.stopStartAt) >= 20000) {
      gpsState.stops.push({ lat: gpsState.stopStartPt[0], lon: gpsState.stopStartPt[1], dur: Math.round((now - gpsState.stopStartAt) / 1000) });
      gpsState.stopRecorded = true;
      updateGpsEventsLine();
    }
  } else {
    if (gpsState.stopStartAt != null && gpsState.stopRecorded && gpsState.stops.length) {
      gpsState.stops[gpsState.stops.length - 1].dur = Math.round((now - gpsState.stopStartAt) / 1000);
      updateGpsEventsLine();
    }
    gpsState.stopStartAt = null;
    gpsState.stopStartPt = null;
    gpsState.stopRecorded = false;
  }

  // ---- battery milestones (100, 90, 80, ...) ----
  const bat = scooterState.battery;
  if (bat != null && !isNaN(bat)) {
    if (gpsState.lastBattery == null) gpsState.lastBattery = bat;
    for (let pct = 100; pct >= 10; pct -= 10) {
      if (gpsState.lastBattery > pct && bat <= pct && !gpsState.batterySeen[pct]) {
        gpsState.batterySeen[pct] = true;
        gpsState.batteryMarks.push({ lat: f.lat, lon: f.lon, pct: pct });
        updateGpsEventsLine();
      }
    }
    gpsState.lastBattery = bat;
  }
}

function updateGpsEventsLine() {
  const el = document.getElementById('gpsEventsLine');
  if (!el) return;
  const parts = [];
  if (gpsState.stops.length) {
    parts.push('\\u23F8 ' + gpsState.stops.length + ' stop' + (gpsState.stops.length > 1 ? 's' : '') + ' over 20s \\u00B7 ' + gpsState.stops.map(function (s) { return s.dur + 's'; }).join(', '));
  }
  if (gpsState.batteryMarks.length) {
    parts.push('\\uD83D\\uDD0B ' + gpsState.batteryMarks.map(function (b) { return b.pct + '%'; }).join(' \\u00B7 '));
  }
  el.textContent = parts.length ? parts.join('   \\u2022   ') : 'Markers: START / END points, stops over 20s, battery drop levels';
}

function startGpsDemo() {'''
src = src.replace(old, tracker, 1)

shim = open('shim_block.html', encoding='utf-8').read()
marker = '<meta name="theme-color" content="#0a0514">'
assert marker in src
src = src.replace(marker, marker + shim, 1)

open('app/src/main/assets/index.html', 'w', encoding='utf-8').write(src)
print('asset OK:', len(src))
