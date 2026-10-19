package mt.riley.app;

import android.annotation.SuppressLint;
import android.app.Activity;
import android.content.Intent;
import android.os.Build;
import android.os.Bundle;
import android.util.Base64;
import android.webkit.JavascriptInterface;
import android.webkit.WebSettings;
import android.webkit.WebView;
import android.webkit.WebViewClient;

public class InterfaceActivity extends Activity implements ScooterBleService.WebListener {

    private WebView webView;

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
        if (ScooterBleService.webListener == this) ScooterBleService.webListener = null;
    }

    private void ensureGuardRunning() {
        Intent i = new Intent(this, ScooterBleService.class);
        i.setAction(ScooterBleService.ACTION_CONNECT);
        if (Build.VERSION.SDK_INT >= 26) startForegroundService(i); else startService(i);
    }

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
