src = open('../incoming_files/58f67d030_volpam-quickswitch_8.html', encoding='utf-8').read()

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
    ('textContent = "0.0s / 5.0s"', 'textContent = "0.0s / 2.0s"'),
    ('textContent = "5.0s / 5.0s - TRIGGERED!"', 'textContent = "2.0s / 2.0s - TRIGGERED!"'),
]
for old, new in repls:
    assert src.count(old) > 0, old
    src = src.replace(old, new)

shim = '''
<script>
(function () {
  if (navigator.bluetooth) return;
  function b64ToBytes(b64) {
    var bin = atob(b64), u = new Uint8Array(bin.length);
    for (var i = 0; i < bin.length; i++) u[i] = bin.charCodeAt(i);
    return u;
  }
  function bytesToB64(u) {
    var s = '';
    for (var i = 0; i < u.length; i++) s += String.fromCharCode(u[i]);
    return btoa(s);
  }
  var lastReqTime = 0;
  var bt = {
    requestDevice: function (opts) {
      if (RileyBridge.ready()) {
        lastReqTime = Date.now();
        return Promise.resolve(makeDevice(RileyBridge.deviceName()));
      }
      if (Date.now() - lastReqTime < 5000) {
        return Promise.reject(new Error('Device selection cancelled'));
      }
      lastReqTime = Date.now();
      return new Promise(function (resolve, reject) {
        window.__rileyDeviceFound = function (name) { resolve(makeDevice(name)); };
        window.__rileyDeviceCancelled = function () { reject(new Error('No device selected')); };
        try { RileyBridge.requestDevice(); } catch (e) { reject(e); }
      });
    }
  };
  function makeDevice(nameArg) {
    var discListeners = [];
    var charObj = null;
    var charListeners = [];
    var device = {
      name: nameArg,
      addEventListener: function (t, f) { if (t === 'gattserverdisconnected') discListeners.push(f); },
      gatt: {
        connected: false,
        connect: function () {
          var self = this;
          return new Promise(function (res, rej) {
            RileyBridge.startConnect();
            var tries = 0;
            var iv = setInterval(function () {
              if (RileyBridge.ready()) { clearInterval(iv); self.connected = true; res(self); }
              else if (tries++ > 200) { clearInterval(iv); rej(new Error('Timed out connecting to scooter')); }
            }, 150);
          });
        },
        disconnect: function () { this.connected = false; RileyBridge.disconnect(); },
        getPrimaryService: function (uuid) {
          return new Promise(function (res, rej) {
            var attached = RileyBridge.serviceId();
            var want = (uuid || '').indexOf('fee0') >= 0 ? 'fee0' : 'fff0';
            if (attached === want) res({
              getCharacteristic: function () { return Promise.resolve(makeChar()); }
            });
            else rej(new Error('Service not found on this device'));
          });
        }
      }
    };
    function makeChar() {
      if (charObj) return charObj;
      charObj = {
        startNotifications: function () { return Promise.resolve(); },
        addEventListener: function (t, f) { if (t === 'characteristicvaluechanged') charListeners.push(f); },
        writeValue: function (b) { RileyBridge.write(bytesToB64(new Uint8Array(b))); return Promise.resolve(); },
        writeValueWithoutResponse: function (b) { RileyBridge.write(bytesToB64(new Uint8Array(b))); return Promise.resolve(); }
      };
      return charObj;
    }
    window.__rileyNotify = function (b64) {
      var bytes = b64ToBytes(b64);
      var dv = new DataView(bytes.buffer);
      charListeners.forEach(function (f) {
        try { f({ target: { value: dv } }); } catch (e) {}
      });
    };
    window.__rileyDisconnected = function () {
      device.gatt.connected = false;
      discListeners.forEach(function (f) { try { f({}); } catch (e) {} });
    };
    return device;
  }
  navigator.bluetooth = bt;
})();
</script>
'''
marker = '<meta name="theme-color" content="#07090e">'
assert marker in src
src = src.replace(marker, marker + shim, 1)
open('app/src/main/assets/index.html', 'w', encoding='utf-8').write(src)
print('asset rebuilt:', len(src))
