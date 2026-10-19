package mt.riley.app;

import android.Manifest;
import android.annotation.SuppressLint;
import android.app.Activity;
import android.app.AlertDialog;
import android.bluetooth.BluetoothAdapter;
import android.bluetooth.BluetoothDevice;
import android.bluetooth.BluetoothManager;
import android.bluetooth.le.BluetoothLeScanner;
import android.bluetooth.le.ScanCallback;
import android.bluetooth.le.ScanResult;
import android.bluetooth.le.ScanSettings;
import android.content.Context;
import android.content.Intent;
import android.content.pm.PackageManager;
import android.os.Build;
import android.os.Bundle;
import android.os.Handler;
import android.os.Looper;
import android.util.Base64;
import android.webkit.JavascriptInterface;
import android.webkit.WebSettings;
import android.webkit.WebView;
import android.webkit.WebViewClient;

import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

public class InterfaceActivity extends Activity implements ScooterBleService.WebListener {

    private WebView webView;
    private final Handler uiHandler = new Handler(Looper.getMainLooper());
    private BluetoothLeScanner scanner;
    private final Map<String, String> found = new LinkedHashMap<>(); // name -> address
    private AlertDialog scanDialog;
    private AlertDialog pickDialog;

    private final ScanCallback pickerScan = new ScanCallback() {
        @Override
        public void onScanResult(int callbackType, ScanResult result) {
            BluetoothDevice d = result.getDevice();
            String n;
            try { n = d.getName(); } catch (SecurityException e) { return; }
            if (n == null || n.trim().isEmpty()) return;
            final String name = n.trim();
            final String addr = d.getAddress();
            uiHandler.post(() -> found.put(name, addr));
        }
    };

    @SuppressLint("SetJavaScriptEnabled")
    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        webView = new WebView(this);
        WebSettings s = webView.getSettings();
        s.setJavaScriptEnabled(true);
        s.setDomStorageEnabled(true);
        webView.setBackgroundColor(0xFF07090E);
        webView.setWebViewClient(new WebViewClient());
        webView.addJavascriptInterface(new Bridge(), "RileyBridge");
        webView.loadUrl("file:///android_asset/index.html");
        setContentView(webView);
    }

    @Override
    protected void onStart() {
        super.onStart();
        ScooterBleService.webListener = this;
        ensureGuardRunning();
    }

    @Override
    protected void onStop() {
        super.onStop();
        stopPickerScan();
        dismissDialogs();
        if (ScooterBleService.webListener == this) ScooterBleService.webListener = null;
    }

    private void ensureGuardRunning() {
        Intent i = new Intent(this, ScooterBleService.class);
        i.setAction(ScooterBleService.ACTION_CONNECT);
        if (Build.VERSION.SDK_INT >= 26) startForegroundService(i); else startService(i);
    }

    // ---------------- device picker ----------------

    private void beginPickerFlow() {
        if (Build.VERSION.SDK_INT >= 31
                && (checkSelfPermission(Manifest.permission.BLUETOOTH_SCAN) != PackageManager.PERMISSION_GRANTED
                || checkSelfPermission(Manifest.permission.BLUETOOTH_CONNECT) != PackageManager.PERMISSION_GRANTED)) {
            requestPermissions(new String[]{
                    Manifest.permission.BLUETOOTH_SCAN,
                    Manifest.permission.BLUETOOTH_CONNECT,
                    Manifest.permission.POST_NOTIFICATIONS}, 9);
            return;
        }
        startPickerScan();
    }

    @Override
    public void onRequestPermissionsResult(int requestCode, String[] permissions, int[] grantResults) {
        super.onRequestPermissionsResult(requestCode, permissions, grantResults);
        if (requestCode == 9 && Build.VERSION.SDK_INT >= 31
                && checkSelfPermission(Manifest.permission.BLUETOOTH_SCAN) == PackageManager.PERMISSION_GRANTED
                && checkSelfPermission(Manifest.permission.BLUETOOTH_CONNECT) == PackageManager.PERMISSION_GRANTED) {
            startPickerScan();
        }
    }

    private BluetoothLeScanner getScanner() {
        if (scanner != null) return scanner;
        BluetoothManager bm = (BluetoothManager) getSystemService(Context.BLUETOOTH_SERVICE);
        BluetoothAdapter adapter = bm != null ? bm.getAdapter() : null;
        if (adapter == null || !adapter.isEnabled()) return null;
        scanner = adapter.getBluetoothLeScanner();
        return scanner;
    }

    private void startPickerScan() {
        BluetoothLeScanner s = getScanner();
        if (s == null) {
            new AlertDialog.Builder(this)
                    .setTitle("Bluetooth is off")
                    .setMessage("Turn on Bluetooth, then tap Connect again.")
                    .setPositiveButton("OK", null)
                    .show();
            cancelDevice();
            return;
        }
        found.clear();
        try { s.startScan(null, new ScanSettings.Builder().setScanMode(ScanSettings.SCAN_MODE_LOW_LATENCY).build(), pickerScan); }
        catch (Exception e) { cancelDevice(); return; }

        scanDialog = new AlertDialog.Builder(this)
                .setTitle("Scanning for scooters...")
                .setMessage("Make sure the scooter is powered on and nearby.")
                .setCancelable(true)
                .setOnCancelListener(d -> { stopPickerScan(); cancelDevice(); })
                .setNegativeButton("Cancel", (d, w) -> { stopPickerScan(); cancelDevice(); })
                .show();

        uiHandler.postDelayed(() -> { stopPickerScan(); showPickList(); }, 8000);
    }

    private void stopPickerScan() {
        try { if (scanner != null) scanner.stopScan(pickerScan); } catch (Exception ignored) {}
    }

    private void showPickList() {
        if (scanDialog != null && scanDialog.isShowing()) scanDialog.dismiss();
        if (found.isEmpty()) {
            String last = ScooterBleService.chosenDeviceAddress;
            if (last != null) {
                new AlertDialog.Builder(this)
                        .setTitle("No new devices found")
                        .setMessage("Reconnect to your last scooter?")
                        .setPositiveButton("Reconnect", (d, w) -> resolveDevice(ScooterBleService.getDeviceNameStatic(), last))
                        .setNeutralButton("Scan again", (d, w) -> startPickerScan())
                        .setNegativeButton("Cancel", (d, w) -> cancelDevice())
                        .show();
            } else {
                new AlertDialog.Builder(this)
                        .setTitle("No devices found")
                        .setMessage("Make sure the scooter is powered on, then try again.")
                        .setPositiveButton("Scan again", (d, w) -> startPickerScan())
                        .setNegativeButton("Cancel", (d, w) -> cancelDevice())
                        .show();
            }
            return;
        }
        pickDialog = new AlertDialog.Builder(this)
                .setTitle("Choose your scooter")
                .setCancelable(true)
                .setOnCancelListener(d -> cancelDevice())
                .setNegativeButton("Cancel", (d, w) -> cancelDevice())
                .setItems(buildLabels(), (d, which) -> {
                    String label = buildLabels()[which];
                    if (label.startsWith("Reconnect: ")) {
                        resolveDevice(ScooterBleService.getDeviceNameStatic(), ScooterBleService.chosenDeviceAddress);
                    } else {
                        String name = label;
                        String addr = found.get(name);
                        if (addr != null) resolveDevice(name, addr);
                        else cancelDevice();
                    }
                })
                .show();
    }

    private String[] buildLabels() {
        List<String> labels = new ArrayList<>();
        String last = ScooterBleService.chosenDeviceAddress;
        if (last != null) labels.add("Reconnect: " + ScooterBleService.getDeviceNameStatic());
        labels.addAll(found.keySet());
        return labels.toArray(new String[0]);
    }

    private void dismissDialogs() {
        if (scanDialog != null && scanDialog.isShowing()) scanDialog.dismiss();
        if (pickDialog != null && pickDialog.isShowing()) pickDialog.dismiss();
    }

    private void resolveDevice(String name, String address) {
        dismissDialogs();
        ScooterBleService.chosenDeviceAddress = address;
        if (webView != null) {
            webView.evaluateJavascript("window.__rileyDeviceFound(" + jsStr(name) + ",'" + address + "')", null);
        }
    }

    private void cancelDevice() {
        dismissDialogs();
        if (webView != null) webView.evaluateJavascript("window.__rileyDeviceCancelled()", null);
    }

    private static String jsStr(String s) {
        if (s == null) s = "";
        return "'" + s.replace("\\", "\\\\").replace("'", "\\'") + "'";
    }

    // ---------------- BLE events from the guard service ----------------

    @Override
    public void onBleNotify(final byte[] data) {
        runOnUiThread(() -> {
            if (webView == null || data == null) return;
            String b64 = Base64.encodeToString(data, Base64.NO_WRAP);
            webView.evaluateJavascript("window.__rileyNotify('" + b64 + "')", null);
        });
    }

    @Override
    public void onBleDisconnected() {
        runOnUiThread(() -> {
            if (webView == null) return;
            webView.evaluateJavascript("window.__rileyDisconnected()", null);
        });
    }

    @Override
    public void onBackPressed() {
        if (webView != null && webView.canGoBack()) webView.goBack();
        else super.onBackPressed();
    }

    private class Bridge {
        @JavascriptInterface public String deviceName() { return ScooterBleService.getDeviceNameStatic(); }
        @JavascriptInterface public boolean connected() { return ScooterBleService.isConnectedStatic(); }
        @JavascriptInterface public boolean ready() { return ScooterBleService.isReadyStatic(); }
        @JavascriptInterface public String serviceId() { return ScooterBleService.getServiceIdStatic(); }
        @JavascriptInterface public void requestDevice() { runOnUiThread(() -> beginPickerFlow()); }
        @JavascriptInterface public void startConnect() { ensureGuardRunning(); }
        @JavascriptInterface public void disconnect() {
            Intent i = new Intent(InterfaceActivity.this, ScooterBleService.class);
            i.setAction(ScooterBleService.ACTION_DISCONNECT);
            startService(i);
        }
        @JavascriptInterface public void write(String b64) {
            try {
                byte[] data = Base64.decode(b64, Base64.DEFAULT);
                ScooterBleService.writeFromWeb(data);
            } catch (Exception ignored) {}
        }
    }
}
