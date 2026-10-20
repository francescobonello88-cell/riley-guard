src = open('../incoming_files/acf8c1cf2_volpam-quickswitch-no-accel-ebrake202.html', encoding='utf-8').read()

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
marker = '<meta name="theme-color" content="#000000">'
assert marker in src, "theme marker missing"
src = src.replace(marker, marker + shim, 1)
open('app/src/main/assets/index.html', 'w', encoding='utf-8').write(src)
print('new asset written:', len(src))
