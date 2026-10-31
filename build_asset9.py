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


# ---- FIXES: centered speedometer, bigger trip range, only 3 modes ----
# 1) speedometer centering
css_fix = """
  /* ---- centered speedometer ---- */
  .speedo-card{display:flex;flex-direction:column;align-items:center;text-align:center}
  .speedo-wrap{position:relative;width:240px;max-width:100%;height:172px;margin:0 auto;overflow:hidden}
  .speedo-svg{position:absolute;left:50%;top:0;width:240px;height:240px;transform:translateX(-50%) rotate(-90deg);transform-origin:50% 50%}
  .speedo-display{position:absolute;left:0;right:0;top:66px;width:auto;text-align:center}
  .speedo-val{text-align:center}
  .speedo-unit-btn{margin:8px auto 0}
  .range-modes{grid-template-columns:repeat(3,1fr)}
"""
idx = src.find('</style>')
assert idx > 0
src = src[:idx] + css_fix + src[idx:]

# 2) trip range: 5 km cap -> 50 km
old = "const GPS_SESSION_CAP_KM = 5;"
assert old in src
src = src.replace(old, "const GPS_SESSION_CAP_KM = 50;", 1)
old = "<span>Session 5 km</span>"
assert old in src
src = src.replace(old, "<span>Session 50 km</span>", 1)

# 3) only ECO / DRIVE / SPORT - remove RACE
old = '      <div class="range-chip active" id="rcRace"><span>RACE</span><strong id="rngRace">-- km</strong></div>\n'
assert old in src, "race chip"
src = src.replace(old, "", 1)
src = src.replace("(varies by ECO / DRIVE / SPORT / RACE) -->", "(varies by ECO / DRIVE / SPORT) -->", 1)
src = src.replace("<!-- \uD83D\uDD2E ESTIMATED RANGE (varies by ECO / DRIVE / SPORT / RACE) -->",
                  "<!-- \uD83D\uDD2E ESTIMATED RANGE (varies by ECO / DRIVE / SPORT) -->", 1)
src = src.replace('>MODE: RACE</span>', '>MODE: &#8212;</span>', 1)
src = src.replace("\u2014 RACE drinks charge fastest, ECO sips it.", "\u2014 SPORT drinks charge fastest, ECO sips it.", 1)
old = """  SPORT: { nominalKmh: 32, baseW: 260, wPerKmh: 10.5 },
  RACE:  { nominalKmh: 47, baseW: 380, wPerKmh: 14.5 }
};"""
assert old in src
src = src.replace(old, """  SPORT: { nominalKmh: 32, baseW: 260, wPerKmh: 10.5 }
};""", 1)
old = "  if (scooterState.gear === 3 && (scooterState.activeLimit || 0) >= 45) return 'RACE';\n"
assert old in src
src = src.replace(old, "", 1)
old = "[['ECO','rcEco'],['DRIVE','rcDrive'],['SPORT','rcSport'],['RACE','rcRace']]"
assert old in src
src = src.replace(old, "[['ECO','rcEco'],['DRIVE','rcDrive'],['SPORT','rcSport']]", 1)
src = src.replace('"\u26A1 RACE \u2014 UNLIMITED (47 KM/H)"', '"\u26A1 SPORT \u2014 UNLIMITED (47 KM/H)"', 1)



# ---- GOOGLE MAPS integration ----
old_canvas = '<canvas id="gpsTrail" class="gps-trail" width="412" height="120"></canvas>'
assert old_canvas in src
map_html = """<div style="position:relative;margin:0 0 8px">
      <iframe id="gmapsFrame" style="width:100%;height:170px;border:1px solid rgba(168,85,247,.28);border-radius:12px;background:rgba(0,0,0,.45);display:block" referrerpolicy="no-referrer-when-downgrade"></iframe>
      <div id="gmapsPlaceholder" style="position:absolute;inset:0;display:flex;align-items:center;justify-content:center;border-radius:12px;background:rgba(10,6,18,.94);color:#c4b5d2;font-size:11px;font-weight:800;text-align:center;padding:12px;line-height:1.5">🗺️ Start GPS to load Google Maps</div>
    </div>
    <div style="display:flex;gap:8px;margin:0 0 9px">
      <button class="preset-pill" style="flex:1;font-size:10.5px;padding:7px 6px;font-weight:800" onclick="openInGoogleMaps()">🧭 Open in Google Maps</button>
    </div>
    <div style="font-size:9.5px;color:#c4b5d2;font-weight:800;margin:0 0 5px;letter-spacing:.3px">🛣️ Trip trail &amp; markers</div>
    """
src = src.replace(old_canvas, map_html + old_canvas, 1)

old = "function trackGpsEvents(f) {"
assert old in src
map_js = '''let gmapsLastLoadAt = 0, gmapsLastLat = null, gmapsLastLon = null;

function updateGoogleMap(f) {
  const frame = document.getElementById('gmapsFrame');
  const ph = document.getElementById('gmapsPlaceholder');
  if (!frame) return;
  const now = Date.now();
  const movedKm = (gmapsLastLat != null) ? haversineKm(gmapsLastLat, gmapsLastLon, f.lat, f.lon) : 999;
  if (movedKm < 0.02 && (now - gmapsLastLoadAt) < 15000) return;
  gmapsLastLat = f.lat; gmapsLastLon = f.lon; gmapsLastLoadAt = now;
  frame.src = 'https://maps.google.com/maps?q=' + f.lat.toFixed(6) + ',' + f.lon.toFixed(6) + '&z=17&t=m&output=embed';
  if (ph) ph.style.display = 'none';
}

function openInGoogleMaps() {
  if (gpsState.lat == null) { showToast('No GPS fix yet - start GPS first', '⚠️'); return; }
  const pair = gpsState.lat + ',' + gpsState.lon;
  try {
    if (window.RileyBridge && RileyBridge.openMaps) { RileyBridge.openMaps(pair); return; }
  } catch (e) {}
  window.open('https://www.google.com/maps?q=' + pair, '_blank');
}

function trackGpsEvents(f) {'''
src = src.replace(old, map_js, 1)

old = """  trackGpsEvents(f);
  updateGpsUI();"""
assert old in src
src = src.replace(old, """  trackGpsEvents(f);
  updateGoogleMap(f);
  updateGpsUI();""", 1)

old = "  gpsState.stopRecorded = false; gpsState.endPt = null;\n  updateGpsEventsLine();"
assert old in src
src = src.replace(old, "  gpsState.stopRecorded = false; gpsState.endPt = null;\n  gmapsLastLat = null; gmapsLastLon = null; gmapsLastLoadAt = 0;\n  updateGpsEventsLine();", 1)


shim = open('shim_block.html', encoding='utf-8').read()
marker = '<meta name="theme-color" content="#0a0514">'
assert marker in src
src = src.replace(marker, marker + shim, 1)

open('app/src/main/assets/index.html', 'w', encoding='utf-8').write(src)
print('asset OK:', len(src))
