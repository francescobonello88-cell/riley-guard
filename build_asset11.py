import sys

SRC = '../incoming_files/98e83d465_volpam.html'
src = open(SRC, encoding='utf-8').read()

fails = []


def rep(old, new, count=1):
    global src
    n = src.count(old)
    if n != count:
        fails.append('ANCHOR FAIL (%d!=%d): %r' % (n, count, old[:80]))
    else:
        src = src.replace(old, new)


# ---------- 1. only 3 modes: ECO / DRIVE / SPORT ----------
rep("  SPORT: { nominalKmh: 32, baseW: 260, wPerKmh: 10.5 },\n  RACE:  { nominalKmh: 47, baseW: 380, wPerKmh: 14.5 }",
    "  SPORT: { nominalKmh: 32, baseW: 260, wPerKmh: 10.5 }")
rep("  if (scooterState.gear === 3 && (scooterState.activeLimit || 0) >= 45) return 'RACE';\n", "")
rep("['SPORT','rcSport'],['RACE','rcRace']", "['SPORT','rcSport']")
rep("MODE: ${mode === 'RACE' ? 'UNLIMIT' : mode}", "MODE: ${mode}")
rep('      <div class="range-chip active" id="rcRace"><span>UNLIMIT</span><strong id="rngRace">-- km</strong></div>\n', '')
rep('MODE: RACE', 'MODE: \u2014')
rep('(varies by ECO / DRIVE / SPORT / RACE)', '(varies by ECO / DRIVE / SPORT)')
rep('.range-modes{display:grid;grid-template-columns:repeat(4,1fr);gap:6px}',
    '.range-modes{display:grid;grid-template-columns:repeat(3,1fr);gap:6px}')
rep('Unlimit drinks charge fastest', 'SPORT drinks charge fastest')

# ---------- 2. centered speedometer ----------
css = """  /* centered speedometer */
  .speedo-card{display:flex;flex-direction:column;align-items:center}
  .speedo-wrap{position:relative;width:240px;max-width:100%;height:172px;margin:0 auto;overflow:hidden}
  .speedo-svg{position:absolute;left:50%;top:0;width:240px;height:240px;transform:translateX(-50%) rotate(-90deg);transform-origin:50% 50%}
  .speedo-display{position:absolute;left:0;right:0;top:66px;width:auto;text-align:center}
  .speedo-val{text-align:center}
  .speedo-unit-btn{margin:8px auto 0}
</style>"""
rep('</style>', css)

# ---------- 3. trip range 5 km -> 50 km ----------
rep('const GPS_SESSION_CAP_KM = 5;', 'const GPS_SESSION_CAP_KM = 50;')
rep('<span>Session 5 km</span>', '<span>Session 50 km</span>')

# ---------- 4. GPS marker state ----------
rep("  sessionStartAt: null, lastGoodAt: null\n};",
    "  sessionStartAt: null, lastGoodAt: null,\n"
    "  stops: [], batteryMarks: [], batterySeen: {}, lastBattery: null,\n"
    "  stopStartAt: null, stopStartPt: null, stopRecorded: false, endPt: null,\n"
    "  nativePoll: null\n};")

# ---------- 5. session reset + start native tracking ----------
rep("  gpsState.trail = []; gpsState.distKm = 0;",
    "  gpsState.trail = []; gpsState.distKm = 0;\n"
    "  gpsState.stops = []; gpsState.batteryMarks = []; gpsState.batterySeen = {};\n"
    "  gpsState.lastBattery = null; gpsState.stopStartAt = null; gpsState.stopStartPt = null;\n"
    "  gpsState.stopRecorded = false; gpsState.endPt = null;\n"
    "  if (typeof updateGpsEventsLine === 'function') updateGpsEventsLine();")

rep("  gpsState.on = true;\n  gpsToggleBtn.textContent = '\u25a0 Stop GPS';",
    "  gpsState.on = true;\n  gpsToggleBtn.textContent = '\u25a0 Stop GPS';\n"
    "  try { if (window.RileyBridge && RileyBridge.setGpsTracking) { RileyBridge.clearTrack(); RileyBridge.setGpsTracking(true); } } catch (e) {}\n"
    "  if (gpsState.nativePoll) clearInterval(gpsState.nativePoll);\n"
    "  gpsState.nativePoll = setInterval(mergeNativeTrack, 3000);")

# ---------- 6. hooks on every good fix ----------
rep("  gpsState.lastFixAt = now; gpsState.lastGoodAt = now;\n  updateGpsUI();\n  drawGpsTrail();",
    "  gpsState.lastFixAt = now; gpsState.lastGoodAt = now;\n"
    "  trackGpsEvents(f);\n  updateGoogleMap(f);\n  updateGpsUI();\n  drawGpsTrail();")

# ---------- 7. speed from scooter, GPS only as fallback ----------
rep("  gpsState.speedKmh = f.spd != null ? f.spd * 3.6 : null;",
    "  gpsState.speedKmh = bestSpeedKmh(f.spd);", 2)
rep('<span>GPS Speed</span>', '<span>Scooter Speed</span>')

# ---------- 8. stopGps: END marker + stop native tracking ----------
rep("  if (gpsState.demoTimer) { clearInterval(gpsState.demoTimer); gpsState.demoTimer = null; }\n  setGpsPill('', 'GPS Off');",
    "  if (gpsState.demoTimer) { clearInterval(gpsState.demoTimer); gpsState.demoTimer = null; }\n"
    "  try { if (window.RileyBridge && RileyBridge.setGpsTracking) RileyBridge.setGpsTracking(false); } catch (e) {}\n"
    "  if (gpsState.nativePoll) { clearInterval(gpsState.nativePoll); gpsState.nativePoll = null; }\n"
    "  const endLat = gpsState.lat != null ? gpsState.lat : gpsState.fixLat;\n"
    "  const endLon = gpsState.lon != null ? gpsState.lon : gpsState.fixLon;\n"
    "  if (endLat != null) gpsState.endPt = [endLat, endLon];\n"
    "  updateGpsEventsLine();\n  drawGpsTrail();\n"
    "  setGpsPill('', 'GPS Off');")

# ---------- 9. draw markers on the trail ----------
markers = """  ctx.shadowBlur = 0;
  // ---- trip markers: stops >20s, battery drops, START/END ----
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
  ctx.fillStyle = 'rgba(163,230,53,.95)';
  ctx.font = '700 7px "JetBrains Mono", monospace';
  ctx.textAlign = 'center';
  ctx.fillText('START', px(t[0][1]), py(t[0][0]) - 8);"""
rep("  ctx.shadowBlur = 0;", markers)

# ---------- 10. HTML: map, open button, trail label, events line ----------
rep('    <canvas id="gpsTrail" class="gps-trail" width="412" height="120"></canvas>',
    '''    <div style="position:relative;margin:0 0 8px">
      <iframe id="gmapsFrame" style="width:100%;height:170px;border:1px solid rgba(255,255,255,.12);border-radius:12px;background:rgba(0,0,0,.45);display:block" loading="lazy" referrerpolicy="no-referrer-when-downgrade"></iframe>
      <div id="gmapsPlaceholder" style="position:absolute;inset:0;display:flex;align-items:center;justify-content:center;border-radius:12px;background:rgba(6,12,10,.92);color:#a7f3d0;font-size:11px;font-weight:700;text-align:center;padding:10px">\U0001F5FA\uFE0F Start GPS to load Google Maps</div>
    </div>
    <div style="display:flex;gap:8px;margin:0 0 9px">
      <button class="preset-pill" style="flex:1;font-size:10px;padding:7px" onclick="openInGoogleMaps()">\U0001F9ED Open in Google Maps</button>
    </div>
    <div style="font-size:9.5px;color:#a7f3d0;font-weight:800;margin:0 0 5px">\U0001F6E3\uFE0F Trip trail &amp; markers</div>
    <canvas id="gpsTrail" class="gps-trail" width="412" height="120"></canvas>
    <div id="gpsEventsLine" style="font-size:9.5px;color:#c4b5d2;margin:-2px 0 9px;line-height:1.5;font-weight:700">Markers: START/END points, stops over 20s, battery level drops</div>''')

# ---------- 11. JS support functions ----------
js = """function bestSpeedKmh(gpsSpd) {
  if (typeof isConnected !== 'undefined' && isConnected && scooterState.speed != null) return scooterState.speed;
  return gpsSpd != null ? gpsSpd * 3.6 : null;
}

function trackGpsEvents(f) {
  const now = Date.now();
  const spdKmh = bestSpeedKmh(f.spd) || 0;
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
    parts.push('\\u23F8 ' + gpsState.stops.length + ' stop' + (gpsState.stops.length > 1 ? 's' : '') + ' >20s \\u00B7 ' + gpsState.stops.map(function (s) { return s.dur + 's'; }).join(', '));
  }
  if (gpsState.batteryMarks.length) {
    parts.push('\\U0001F50B ' + gpsState.batteryMarks.map(function (b) { return b.pct + '%'; }).join(' \\u00B7 '));
  }
  const mode = (typeof isConnected !== 'undefined' && isConnected) ? '' : '\\U0001F6B6 GPS-only mode';
  el.textContent = parts.length ? (mode ? mode + '   \\u00B7   ' : '') + parts.join('   \\u00B7   ') : (mode || 'Markers: START/END points, stops over 20s, battery level drops');
}

let gmapsLastAt = 0, gmapsLat = null, gmapsLon = null;
function updateGoogleMap(f) {
  const frame = document.getElementById('gmapsFrame');
  const ph = document.getElementById('gmapsPlaceholder');
  if (!frame || f.lat == null) return;
  const now = Date.now();
  const moved = gmapsLat != null ? haversineKm(gmapsLat, gmapsLon, f.lat, f.lon) : 999;
  if (moved < 0.02 && now - gmapsLastAt < 15000) return;
  gmapsLat = f.lat; gmapsLon = f.lon; gmapsLastAt = now;
  frame.src = 'https://maps.google.com/maps?q=' + f.lat.toFixed(6) + ',' + f.lon.toFixed(6) + '&z=17&t=m&output=embed';
  if (ph) ph.style.display = 'none';
}

function openInGoogleMaps() {
  const lat = gpsState.lat != null ? gpsState.lat : gpsState.fixLat;
  const lon = gpsState.lon != null ? gpsState.lon : gpsState.fixLon;
  if (lat == null) return showToast('No GPS fix yet', '\\u26A0\\uFE0F');
  try { if (window.RileyBridge && RileyBridge.openMaps) { RileyBridge.openMaps(lat + ',' + lon); return; } } catch (e) {}
  window.open('https://www.google.com/maps?q=' + lat + ',' + lon, '_blank');
}

function mergeNativeTrack() {
  if (!window.RileyBridge || !RileyBridge.getTrackJson) return;
  let pts = [];
  try { pts = JSON.parse(RileyBridge.getTrackJson() || '[]'); } catch (e) { return; }
  if (!pts || !pts.length) return;
  let changed = false;
  pts.forEach(function (p) {
    if (p.lat == null || p.lon == null) return;
    const last = gpsState.trail.length ? gpsState.trail[gpsState.trail.length - 1] : null;
    if (!last || haversineKm(last[0], last[1], p.lat, p.lon) > 0.005) {
      if (last) gpsState.distKm += haversineKm(last[0], last[1], p.lat, p.lon);
      gpsState.trail.push([p.lat, p.lon]);
      changed = true;
    }
    if (p.bat != null && p.bat >= 0 && !isNaN(p.bat)) {
      if (gpsState.lastBattery == null) gpsState.lastBattery = p.bat;
      for (let pct = 100; pct >= 10; pct -= 10) {
        if (gpsState.lastBattery > pct && p.bat <= pct && !gpsState.batterySeen[pct]) {
          gpsState.batterySeen[pct] = true;
          gpsState.batteryMarks.push({ lat: p.lat, lon: p.lon, pct: pct });
          changed = true;
        }
      }
      gpsState.lastBattery = p.bat;
    }
  });
  if (gpsState.trail.length > 600) gpsState.trail.splice(0, gpsState.trail.length - 600);
  if (changed) { drawGpsTrail(); updateGpsUI(); updateGpsEventsLine(); }
}

function startGpsDemo() {"""
rep('function startGpsDemo() {', js)

# ---------- 12. Bluetooth bridge shim ----------
shim = open('shim_block.html', encoding='utf-8').read()
rep('  <meta name="theme-color" content="#04140e">',
    '  <meta name="theme-color" content="#04140e">\n' + shim)

# haversine must exist in this build (used by our merge/map code)
if 'function haversineKm' not in src:
    fails.append('haversineKm missing in source build')

if fails:
    print('FAILURES:')
    for f_ in fails:
        print(' -', f_)
    sys.exit(1)

open('app/src/main/assets/index.html', 'w', encoding='utf-8').write(src)
print('asset OK:', len(src))
print('RACE refs left:', src.count('RACE'))
print('ECO 2s constant:', src.count('ECO_GESTURE_SECONDS = 2.0'))
print('gmaps:', src.count('gmapsFrame'), '| mergeNative:', src.count('mergeNativeTrack'), '| shim:', src.count('__rileyNotify'))
