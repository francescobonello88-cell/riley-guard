package mt.riley.app;

import android.Manifest;
import android.app.Activity;
import android.content.Context;
import android.content.Intent;
import android.content.pm.PackageManager;
import android.net.Uri;
import android.os.Build;
import android.os.Bundle;
import android.os.PowerManager;
import android.provider.Settings;
import android.view.Gravity;
import android.widget.Button;
import android.widget.LinearLayout;
import android.widget.TextView;
import android.widget.Toast;

public class MainActivity extends Activity {

    private static final int REQ_PERMS = 7;
    private TextView statusView;
    private TextView batteryView;

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);

        LinearLayout root = new LinearLayout(this);
        root.setOrientation(LinearLayout.VERTICAL);
        root.setGravity(Gravity.CENTER_HORIZONTAL);
        root.setBackgroundColor(0xFF07090E);
        int pad = (int) (30 * getResources().getDisplayMetrics().density);
        root.setPadding(pad, pad * 3, pad, pad);

        TextView title = new TextView(this);
        title.setText("Riley App");
        title.setTextSize(28);
        title.setTextColor(0xFFFBBF24);
        title.setGravity(Gravity.CENTER);
        root.addView(title);

        TextView sub = new TextView(this);
        sub.setText("Speed Guard for Volpam MK-083");
        sub.setTextSize(13);
        sub.setTextColor(0xFF94A3B8);
        sub.setGravity(Gravity.CENTER);
        sub.setPadding(0, 8, 0, 0);
        root.addView(sub);

        statusView = new TextView(this);
        statusView.setTextSize(15);
        statusView.setTextColor(0xFFF8FAFC);
        statusView.setGravity(Gravity.CENTER);
        statusView.setPadding(0, pad, 0, pad / 2);
        root.addView(statusView);

        batteryView = new TextView(this);
        batteryView.setTextSize(12);
        batteryView.setTextColor(0xFF94A3B8);
        batteryView.setGravity(Gravity.CENTER);
        batteryView.setPadding(0, 0, 0, pad);
        root.addView(batteryView);

        Button ifaceBtn = new Button(this);
        ifaceBtn.setText("Open Interface");
        ifaceBtn.setOnClickListener(v -> startActivity(new Intent(this, InterfaceActivity.class)));
        root.addView(ifaceBtn);

        Button connectBtn = new Button(this);
        connectBtn.setText("Connect and Start Guard");
        connectBtn.setOnClickListener(v -> connect());
        root.addView(connectBtn);

        Button disconnectBtn = new Button(this);
        disconnectBtn.setText("Stop Guard");
        disconnectBtn.setOnClickListener(v -> {
            ScooterBleService.listener = null;
            Intent i = new Intent(this, ScooterBleService.class);
            i.setAction(ScooterBleService.ACTION_DISCONNECT);
            startService(i);
            setStatus("Guard stopped");
        });
        root.addView(disconnectBtn);

        Button batteryBtn = new Button(this);
        batteryBtn.setText("Disable battery optimization");
        batteryBtn.setOnClickListener(v -> requestIgnoreBatteryOptimizations());
        root.addView(batteryBtn);

        setContentView(root);
    }

    @Override
    protected void onResume() {
        super.onResume();
        ScooterBleService.listener = s -> runOnUiThread(() -> setStatus(s));
        if (ScooterBleService.lastStatus != null && !ScooterBleService.lastStatus.isEmpty()) {
            setStatus(ScooterBleService.lastStatus);
        } else {
            setStatus("Tap Connect with the scooter powered on nearby");
        }
        updateBatteryStatus();
    }

    @Override
    protected void onPause() {
        super.onPause();
        ScooterBleService.listener = null;
    }

    private void setStatus(String s) {
        statusView.setText(s);
        updateBatteryStatus();
    }

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
        if (allGranted) {
            startGuard();
        } else {
            Toast.makeText(this, "Bluetooth permissions are required", Toast.LENGTH_LONG).show();
        }
    }

    private boolean batteryPromptShown = false;

    private void startGuard() {
        // Doze can freeze the guard when the screen is off - ask once for an exemption
        if (!batteryPromptShown) {
            PowerManager pm = (PowerManager) getSystemService(Context.POWER_SERVICE);
            if (pm != null && !pm.isIgnoringBatteryOptimizations(getPackageName())) {
                batteryPromptShown = true;
                requestIgnoreBatteryOptimizations();
            }
        }

        Intent i = new Intent(this, ScooterBleService.class);
        i.setAction(ScooterBleService.ACTION_CONNECT);
        if (Build.VERSION.SDK_INT >= 26) {
            startForegroundService(i);
        } else {
            startService(i);
        }
        setStatus("Guard starting - scanning for scooter...");
    }

    // ---------------- Battery optimization (Doze bypass) ----------------

    private void updateBatteryStatus() {
        PowerManager pm = (PowerManager) getSystemService(Context.POWER_SERVICE);
        boolean ignoring = pm != null && pm.isIgnoringBatteryOptimizations(getPackageName());
        batteryView.setText(ignoring
                ? "Battery optimization: DISABLED (guard safe in Doze)"
                : "Battery optimization: ON - tap below to exempt Riley App");
    }

    private void requestIgnoreBatteryOptimizations() {
        try {
            Intent i = new Intent(Settings.ACTION_REQUEST_IGNORE_BATTERY_OPTIMIZATIONS,
                    Uri.parse("package:" + getPackageName()));
            startActivity(i);
        } catch (Exception e) {
            try {
                startActivity(new Intent(Settings.ACTION_IGNORE_BATTERY_OPTIMIZATION_SETTINGS));
            } catch (Exception ignored) {
                Toast.makeText(this, "Open Settings > Battery > Unrestricted for Riley App", Toast.LENGTH_LONG).show();
            }
        }
    }
}
