package mt.riley.app;

import android.Manifest;
import android.app.Activity;
import android.content.Context;
import android.content.Intent;
import android.content.pm.PackageManager;
import android.graphics.Typeface;
import android.graphics.drawable.Drawable;
import android.graphics.drawable.GradientDrawable;
import android.net.Uri;
import android.os.Build;
import android.os.Bundle;
import android.os.PowerManager;
import android.provider.Settings;
import android.view.Gravity;
import android.view.View;
import android.view.ViewGroup;
import android.widget.Button;
import android.widget.LinearLayout;
import android.widget.ScrollView;
import android.widget.TextView;
import android.widget.Toast;

public class MainActivity extends Activity {

    private static final int REQ_PERMS = 7;
    private static final int GOLD = 0xFFFBBF24;
    private static final int GOLD_DEEP = 0xFFF59E0B;
    private static final int CARD = 0xFF0F1626;
    private static final int STROKE = 0xFF1E2A3E;
    private static final int TEXT = 0xFFE8EEF7;
    private static final int MUTED = 0xFF94A3B8;

    private TextView statusText;
    private TextView batteryText;
    private View statusDot;
    private boolean batteryPromptShown = false;

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);

        ScrollView scroll = new ScrollView(this);
        scroll.setBackgroundColor(0xFF07090E);

        LinearLayout root = new LinearLayout(this);
        root.setOrientation(LinearLayout.VERTICAL);
        root.setPadding(dp(22), dp(40), dp(22), dp(28));
        scroll.addView(root, new ScrollView.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.WRAP_CONTENT));

        // ---- Header ----
        TextView brand = new TextView(this);
        brand.setText("RILEY");
        brand.setTextSize(32);
        brand.setTextColor(GOLD);
        brand.setTypeface(Typeface.DEFAULT_BOLD);
        brand.setLetterSpacing(0.12f);
        root.addView(brand);

        TextView tag = new TextView(this);
        tag.setText("Speed Guard  \u2022  Volpam MK-083");
        tag.setTextSize(13);
        tag.setTextColor(MUTED);
        tag.setPadding(0, dp(2), 0, dp(22));
        root.addView(tag);

        // ---- Status card ----
        LinearLayout card = new LinearLayout(this);
        card.setOrientation(LinearLayout.VERTICAL);
        card.setBackground(rounded(CARD, 20, STROKE));
        card.setPadding(dp(18), dp(16), dp(18), dp(16));
        root.addView(card, lpMatchWrap(dp(0)));

        LinearLayout statusRow = new LinearLayout(this);
        statusRow.setOrientation(LinearLayout.HORIZONTAL);
        statusRow.setGravity(Gravity.CENTER_VERTICAL);

        statusDot = new View(this);
        LinearLayout.LayoutParams dotLp = new LinearLayout.LayoutParams(dp(10), dp(10));
        dotLp.rightMargin = dp(10);
        statusDot.setBackground(dot(0xFF6B7280));
        statusRow.addView(statusDot, dotLp);

        statusText = new TextView(this);
        statusText.setTextSize(14);
        statusText.setTextColor(TEXT);
        statusText.setTypeface(Typeface.DEFAULT_BOLD);
        statusText.setText("Not connected");
        statusRow.addView(statusText);
        card.addView(statusRow);

        batteryText = new TextView(this);
        batteryText.setTextSize(12);
        batteryText.setTextColor(MUTED);
        batteryText.setPadding(0, dp(8), 0, 0);
        card.addView(batteryText);

        // ---- Primary action ----
        Button openIface = makeButton("Open Interface", gradient(), 0xFF1A1205, 17);
        openIface.setOnClickListener(v -> startActivity(new Intent(this, InterfaceActivity.class)));
        root.addView(openIface, lpMatch(dp(56), dp(26), 0));

        // ---- Guard controls ----
        LinearLayout row = new LinearLayout(this);
        row.setOrientation(LinearLayout.HORIZONTAL);
        root.addView(row, lpMatchWrap(dp(12)));

        Button start = makeButton("Start Guard", rounded(0xFF10B981, 16, 0), 0xFF04140C, 15);
        start.setOnClickListener(v -> connect());
        LinearLayout.LayoutParams lpStart = new LinearLayout.LayoutParams(0, dp(52), 1f);
        lpStart.rightMargin = dp(6);
        row.addView(start, lpStart);

        Button stop = makeButton("Stop", rounded(0x14EF4444, 16, 0x66EF4444), 0xFFFCA5A5, 15);
        stop.setOnClickListener(v -> {
            ScooterBleService.listener = null;
            Intent i = new Intent(this, ScooterBleService.class);
            i.setAction(ScooterBleService.ACTION_DISCONNECT);
            startService(i);
            setStatus("Guard stopped");
        });
        LinearLayout.LayoutParams lpStop = new LinearLayout.LayoutParams(0, dp(52), 1f);
        lpStop.leftMargin = dp(6);
        row.addView(stop, lpStop);

        // ---- Battery exemption ----
        Button batt = makeButton("Battery exemption (Doze)", rounded(0xFF0F1626, 14, STROKE), MUTED, 13);
        batt.setOnClickListener(v -> requestIgnoreBatteryOptimizations());
        root.addView(batt, lpMatch(dp(46), dp(10), 0));

        // ---- Footer ----
        TextView foot = new TextView(this);
        foot.setText("Background guard \u2022 2s Eco \u2192 20 km/h + Sport");
        foot.setTextSize(11);
        foot.setTextColor(0xFF5B6675);
        foot.setGravity(Gravity.CENTER);
        foot.setPadding(0, dp(26), 0, 0);
        root.addView(foot);

        setContentView(scroll);
    }

    @Override
    protected void onResume() {
        super.onResume();
        ScooterBleService.listener = s -> runOnUiThread(() -> setStatus(s));
        if (ScooterBleService.lastStatus != null && !ScooterBleService.lastStatus.isEmpty()) {
            setStatus(ScooterBleService.lastStatus);
        } else {
            setStatus("Not connected");
        }
        updateBatteryStatus();
    }

    @Override
    protected void onPause() {
        super.onPause();
        ScooterBleService.listener = null;
    }

    // ---------------- helpers ----------------

    private int dp(float v) { return (int) (v * getResources().getDisplayMetrics().density); }

    private GradientDrawable rounded(int color, float radiusDp, int strokeColor) {
        GradientDrawable d = new GradientDrawable();
        d.setColor(color);
        d.setCornerRadius(dp(radiusDp));
        if (strokeColor != 0) d.setStroke(dp(1), strokeColor);
        return d;
    }

    private GradientDrawable gradient() {
        GradientDrawable d = new GradientDrawable(
                GradientDrawable.Orientation.LEFT_RIGHT, new int[]{GOLD, GOLD_DEEP});
        d.setCornerRadius(dp(18));
        return d;
    }

    private GradientDrawable dot(int color) {
        GradientDrawable d = new GradientDrawable();
        d.setShape(GradientDrawable.OVAL);
        d.setColor(color);
        return d;
    }

    private Button makeButton(String text, Drawable bg, int textColor, float size) {
        Button b = new Button(this);
        b.setText(text);
        b.setAllCaps(false);
        b.setTextSize(size);
        b.setTextColor(textColor);
        b.setTypeface(Typeface.DEFAULT_BOLD);
        b.setBackground(bg);
        b.setPadding(dp(18), dp(12), dp(18), dp(12));
        b.setStateListAnimator(null);
        return b;
    }

    private LinearLayout.LayoutParams lpMatch(int height, int topMargin, int bottomMargin) {
        LinearLayout.LayoutParams lp = new LinearLayout.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT, height);
        lp.topMargin = topMargin;
        lp.bottomMargin = bottomMargin;
        return lp;
    }

    private LinearLayout.LayoutParams lpMatchWrap(int topMargin) {
        LinearLayout.LayoutParams lp = new LinearLayout.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.WRAP_CONTENT);
        lp.topMargin = topMargin;
        return lp;
    }

    private void setStatus(String s) {
        if (statusText != null) statusText.setText(s);
        if (statusDot != null) {
            if (ScooterBleService.isReadyStatic()) statusDot.setBackground(dot(0xFF10B981));
            else if (ScooterBleService.isConnectedStatic()) statusDot.setBackground(dot(0xFFF59E0B));
            else statusDot.setBackground(dot(0xFF6B7280));
        }
        updateBatteryStatus();
    }

    private void updateBatteryStatus() {
        if (batteryText == null) return;
        PowerManager pm = (PowerManager) getSystemService(Context.POWER_SERVICE);
        boolean ignoring = pm != null && pm.isIgnoringBatteryOptimizations(getPackageName());
        batteryText.setText(ignoring
                ? "Battery: Unrestricted \u2014 fully protected in Doze"
                : "Battery optimization is ON \u2014 guard may pause with screen off");
        batteryText.setTextColor(ignoring ? 0xFF34D399 : 0xFFFCA5A5);
    }

    // ---------------- guard control ----------------

    private void connect() {
        if (Build.VERSION.SDK_INT >= 31) {
            if (checkSelfPermission(Manifest.permission.BLUETOOTH_CONNECT) != PackageManager.PERMISSION_GRANTED
                    || checkSelfPermission(Manifest.permission.BLUETOOTH_SCAN) != PackageManager.PERMISSION_GRANTED) {
                requestPermissions(new String[]{
                        Manifest.permission.BLUETOOTH_CONNECT,
                        Manifest.permission.BLUETOOTH_SCAN,
                        Manifest.permission.POST_NOTIFICATIONS}, REQ_PERMS);
                return;
            }
        }
        if (Build.VERSION.SDK_INT >= 33
                && checkSelfPermission(Manifest.permission.POST_NOTIFICATIONS) != PackageManager.PERMISSION_GRANTED) {
            requestPermissions(new String[]{Manifest.permission.POST_NOTIFICATIONS}, REQ_PERMS);
            return;
        }
        startGuard();
    }

    @Override
    public void onRequestPermissionsResult(int requestCode, String[] permissions, int[] grantResults) {
        super.onRequestPermissionsResult(requestCode, permissions, grantResults);
        if (requestCode != REQ_PERMS) return;
        boolean allGranted = true;
        for (int r : grantResults) if (r != PackageManager.PERMISSION_GRANTED) allGranted = false;
        if (allGranted) startGuard();
        else Toast.makeText(this, "Bluetooth permissions are required", Toast.LENGTH_LONG).show();
    }

    private void startGuard() {
        if (!batteryPromptShown) {
            PowerManager pm = (PowerManager) getSystemService(Context.POWER_SERVICE);
            if (pm != null && !pm.isIgnoringBatteryOptimizations(getPackageName())) {
                batteryPromptShown = true;
                requestIgnoreBatteryOptimizations();
            }
        }
        Intent i = new Intent(this, ScooterBleService.class);
        i.setAction(ScooterBleService.ACTION_CONNECT);
        if (Build.VERSION.SDK_INT >= 26) startForegroundService(i); else startService(i);
        setStatus("Starting guard...");
    }

    private void requestIgnoreBatteryOptimizations() {
        try {
            startActivity(new Intent(Settings.ACTION_REQUEST_IGNORE_BATTERY_OPTIMIZATIONS,
                    Uri.parse("package:" + getPackageName())));
        } catch (Exception e) {
            try {
                startActivity(new Intent(Settings.ACTION_IGNORE_BATTERY_OPTIMIZATION_SETTINGS));
            } catch (Exception ignored) {
                Toast.makeText(this, "Settings > Battery > Unrestricted for Riley App", Toast.LENGTH_LONG).show();
            }
        }
    }
}
