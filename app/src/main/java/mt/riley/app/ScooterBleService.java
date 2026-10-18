package mt.riley.app;

import android.app.Notification;
import android.app.NotificationChannel;
import android.app.NotificationManager;
import android.app.PendingIntent;
import android.app.Service;
import android.bluetooth.BluetoothAdapter;
import android.bluetooth.BluetoothDevice;
import android.bluetooth.BluetoothGatt;
import android.bluetooth.BluetoothGattCallback;
import android.bluetooth.BluetoothGattCharacteristic;
import android.bluetooth.BluetoothGattDescriptor;
import android.bluetooth.BluetoothGattService;
import android.bluetooth.BluetoothManager;
import android.bluetooth.BluetoothProfile;
import android.bluetooth.le.BluetoothLeScanner;
import android.bluetooth.le.ScanCallback;
import android.bluetooth.le.ScanFilter;
import android.bluetooth.le.ScanResult;
import android.bluetooth.le.ScanSettings;
import android.content.Context;
import android.content.Intent;
import android.content.pm.ServiceInfo;
import android.os.Build;
import android.os.Handler;
import android.os.IBinder;
import android.os.Looper;
import android.os.ParcelUuid;
import android.os.PowerManager;
import android.os.VibrationEffect;
import android.os.Vibrator;

import java.util.ArrayList;
import java.util.List;
import java.util.UUID;

public class ScooterBleService extends Service {

    public static final String ACTION_CONNECT = "mt.riley.app.CONNECT";
    public static final String ACTION_DISCONNECT = "mt.riley.app.DISCONNECT";

    public interface StatusListener { void onStatus(String status); }
    public static volatile StatusListener listener = null;
    public static volatile String lastStatus = "";
    private static void postStatus(String s) {
        lastStatus = s;
        StatusListener l = listener;
        if (l != null) try { l.onStatus(s); } catch (Exception ignored) {}
    }

    // ViCont protocol
    private static final UUID SERVICE_FEE0 = UUID.fromString("0000fee0-0000-1000-8000-00805f9b34fb");
    private static final UUID CHAR_FEE2  = UUID.fromString("0000fee2-0000-1000-8000-00805f9b34fb");
    private static final UUID SERVICE_FFF0 = UUID.fromString("0000fff0-0000-1000-8000-00805f9b34fb");
    private static final UUID CHAR_FFF1  = UUID.fromString("0000fff1-0000-1000-8000-00805f9b34fb");
    private static final UUID CCCD = UUID.fromString("00002902-0000-1000-8000-00805f9b34fb");

    private static final byte[] HS1 = {(byte)0xFA,(byte)0xAF,(byte)0xA5,(byte)0x5A,0x01,0x00,(byte)0x5B};
    private static final byte[] HS2 = {(byte)0xFA,(byte)0xAF,(byte)0xA5,(byte)0xFA,0x01,0x00,(byte)0xFB};
    private static final byte[] HS3 = {(byte)0xFA,(byte)0xAF,(byte)0xA5,(byte)0x5A,0x31,0x01,0x01,(byte)0x8D};
    private static final byte[] QUERY_LIMIT = {(byte)0xFA,(byte)0xAF,(byte)0xA5,(byte)0x5A,0x3C,0x01,0x00,(byte)0x97};

    // Stealth limiter packets: 20 km/h limit, P10 EEPROM sport limit 20, shift to SPORT gear 3
    private static final byte[] SET_LIMIT_20 = {(byte)0xFA,(byte)0xAF,(byte)0xA5,(byte)0x5A,0x3C,0x01,0x14,(byte)0xAB};
    private static final byte[] P10_TO_20     = {(byte)0xFA,(byte)0xAF,(byte)0xA5,(byte)0x5A,(byte)0xD2,0x02,0x09,0x14,(byte)0x4B};
    private static final byte[] GEAR_3       = {(byte)0xFA,(byte)0xAF,(byte)0xA5,(byte)0x5A,0x42,0x01,0x03,(byte)0xA0};

    private static final long GESTURE_MS = 2000L;   // 2-second hold
    private static final int THROTTLE_ADC_TRIGGER = 2000; // ~80% of 12-bit ADC

    private final Handler handler = new Handler(Looper.getMainLooper());
    private BluetoothAdapter adapter;
    private BluetoothLeScanner scanner;
    private BluetoothGatt gatt;
    private BluetoothGattCharacteristic activeChar;
    private PowerManager.WakeLock wakeLock;
    private Vibrator vibrator;

    private volatile boolean running = false;
    private volatile boolean scanningByFilter = false;
    private String deviceAddress = null;

    // Telemetry state
    private volatile int currentGear = 0;
    private volatile int throttleAdc = 0;
    private long ecoHoldStart = 0L;
    private boolean ecoLatched = false;

    private final byte[] frameBuf = new byte[128];
    private int frameLen = 0;

    @Override
    public void onCreate() {
        super.onCreate();
        BluetoothManager bm = (BluetoothManager) getSystemService(Context.BLUETOOTH_SERVICE);
        if (bm != null) adapter = bm.getAdapter();
    }

    @Override
    public int onStartCommand(Intent intent, int flags, int startId) {
        String action = (intent != null) ? intent.getAction() : ACTION_CONNECT;
        startForegroundWithNotification();

        if (ACTION_DISCONNECT.equals(action)) {
            running = false;
            closeAll();
            stopForeground(true);
            stopSelf();
            postStatus("Guard stopped");
            return START_NOT_STICKY;
        }

        boolean wasRunning = running;
        running = true;
        acquireWakeLock();
        if (!wasRunning) {
            postStatus("Speed Guard active");
            if (gatt == null && deviceAddress == null) {
                startScan();
            } else if (gatt != null) {
                postStatus("Re-attaching to scooter...");
            } else {
                attemptReconnect();
            }
        }
        return START_STICKY;
    }

    @Override
    public IBinder onBind(Intent intent) { return null; }

    @Override
    public void onDestroy() {
        running = false;
        closeAll();
        releaseWakeLock();
        super.onDestroy();
    }

    // ---------------- Foreground notification ----------------

    private void startForegroundWithNotification() {
        NotificationManager nm = (NotificationManager) getSystemService(Context.NOTIFICATION_SERVICE);
        String channelId = "riley_guard";
        if (Build.VERSION.SDK_INT >= 26 && nm != null && nm.getNotificationChannel(channelId) == null) {
            NotificationChannel ch = new NotificationChannel(channelId, "Riley Speed Guard", NotificationManager.IMPORTANCE_LOW);
            ch.setDescription("Background scooter limiter monitoring");
            nm.createNotificationChannel(ch);
        }
        PendingIntent pi = PendingIntent.getActivity(this, 0,
                new Intent(this, MainActivity.class),
                PendingIntent.FLAG_UPDATE_CURRENT | PendingIntent.FLAG_IMMUTABLE);

        Notification.Builder b;
        if (Build.VERSION.SDK_INT >= 26) {
            b = new Notification.Builder(this, channelId);
        } else {
            b = new Notification.Builder(this);
        }
        Notification n = b
                .setSmallIcon(R.drawable.ic_guard)
                .setContentTitle("Riley Speed Guard Active")
                .setContentText("Monitoring 2s Eco Limiter in background")
                .setOngoing(true)
                .setContentIntent(pi)
                .build();

        if (Build.VERSION.SDK_INT >= 34) {
            startForeground(1, n, ServiceInfo.FOREGROUND_SERVICE_TYPE_CONNECTED_DEVICE);
        } else {
            startForeground(1, n);
        }
    }

    // ---------------- Wake lock ----------------

    private void acquireWakeLock() {
        try {
            PowerManager pm = (PowerManager) getSystemService(Context.POWER_SERVICE);
            if (pm == null) return;
            if (wakeLock == null) {
                wakeLock = pm.newWakeLock(PowerManager.PARTIAL_WAKE_LOCK, "RileyApp:BleGuard");
                wakeLock.setReferenceCounted(false);
            }
            if (!wakeLock.isHeld()) wakeLock.acquire();
        } catch (Exception ignored) {}
    }

    private void releaseWakeLock() {
        try { if (wakeLock != null && wakeLock.isHeld()) wakeLock.release(); } catch (Exception ignored) {}
    }

    // ---------------- Scanning ----------------

    private void startScan() {
        postStatus("Scanning for scooter...");
        if (adapter == null || !adapter.isEnabled()) {
            postStatus("Bluetooth is off - turn it on and reconnect");
            return;
        }
        scanner = adapter.getBluetoothLeScanner();
        if (scanner == null) { postStatus("Bluetooth LE unavailable"); return; }

        List<ScanFilter> filters = new ArrayList<>();
        try {
            filters.add(new ScanFilter.Builder().setServiceUuid(new ParcelUuid(SERVICE_FEE0)).build());
            filters.add(new ScanFilter.Builder().setServiceUuid(new ParcelUuid(SERVICE_FFF0)).build());
            scanningByFilter = true;
            scanner.startScan(filters,
                    new ScanSettings.Builder().setScanMode(ScanSettings.SCAN_MODE_LOW_LATENCY).build(),
                    scanCallback);
        } catch (Exception e) {
            postStatus("Scan failed: " + e.getMessage());
            return;
        }
        handler.postDelayed(this::scanFallbackByName, 12000);
        handler.postDelayed(this::scanTimeout, 35000);
    }

    private void scanFallbackByName() {
        if (!running || gatt != null) return;
        stopScanInternal();
        if (scanner == null) return;
        scanningByFilter = false;
        try {
            scanner.startScan(null,
                    new ScanSettings.Builder().setScanMode(ScanSettings.SCAN_MODE_LOW_LATENCY).build(),
                    scanCallback);
            postStatus("Broad scan - looking for scooter by name...");
        } catch (Exception ignored) {}
    }

    private void scanTimeout() {
        if (!running || gatt != null) return;
        stopScanInternal();
        postStatus("Scooter not found. Make sure it is powered on and nearby, then press Connect.");
    }

    private void stopScanInternal() {
        handler.removeCallbacks(this::scanFallbackByName);
        handler.removeCallbacks(this::scanTimeout);
        try { if (scanner != null) scanner.stopScan(scanCallback); } catch (Exception ignored) {}
    }

    private final ScanCallback scanCallback = new ScanCallback() {
        @Override
        public void onScanResult(int callbackType, ScanResult result) {
            BluetoothDevice d = result.getDevice();
            if (d == null) return;
            if (scanningByFilter) {
                stopScanInternal();
                connectDevice(d);
                return;
            }
            String name = d.getName() != null ? d.getName().toUpperCase() : "";
            if (name.contains("MK-083") || name.contains("MK083") || name.contains("VOLPAM")
                    || name.contains("VINCET") || name.contains("VICONT") || name.contains("PRO-VC")) {
                stopScanInternal();
                connectDevice(d);
            }
        }
        @Override
        public void onScanFailed(int errorCode) {
            postStatus("Scan failed (code " + errorCode + ")");
        }
    };

    // ---------------- GATT ----------------

    private void connectDevice(BluetoothDevice device) {
        deviceAddress = device.getAddress();
        String name = device.getName() != null ? device.getName() : deviceAddress;
        postStatus("Connecting to " + name + "...");
        try {
            gatt = device.connectGatt(this, true, gattCallback); // autoConnect=true keeps reconnecting
        } catch (SecurityException e) {
            postStatus("Missing Bluetooth permission");
        }
    }

    private void attemptReconnect() {
        if (!running || adapter == null || deviceAddress == null) {
            if (running) startScan();
            return;
        }
        postStatus("Auto-reconnecting...");
        try {
            BluetoothDevice d = adapter.getRemoteDevice(deviceAddress);
            if (gatt != null) { try { gatt.close(); } catch (Exception ignored) {} gatt = null; }
            gatt = d.connectGatt(this, true, gattCallback);
        } catch (Exception e) {
            startScan();
        }
    }

    private final BluetoothGattCallback gattCallback = new BluetoothGattCallback() {
        @Override
        public void onConnectionStateChange(BluetoothGatt g, int status, int newState) {
            if (newState == BluetoothProfile.STATE_CONNECTED) {
                postStatus("Connected - discovering services");
                try { g.discoverServices(); } catch (SecurityException e) { postStatus("Missing Bluetooth permission"); }
            } else if (newState == BluetoothProfile.STATE_DISCONNECTED) {
                activeChar = null;
                resetGesture();
                if (running) {
                    postStatus("Connection lost - auto-reconnecting");
                    handler.postDelayed(() -> { if (running) attemptReconnect(); }, 2500);
                }
            }
        }

        @Override
        public void onServicesDiscovered(BluetoothGatt g, int status) {
            if (status != BluetoothGatt.GATT_SUCCESS) {
                postStatus("Service discovery failed");
                return;
            }
            BluetoothGattService svc = g.getService(SERVICE_FEE0);
            if (svc != null) activeChar = svc.getCharacteristic(CHAR_FEE2);
            if (activeChar == null) {
                svc = g.getService(SERVICE_FFF0);
                if (svc != null) activeChar = svc.getCharacteristic(CHAR_FFF1);
            }
            if (activeChar == null) {
                postStatus("Scooter BLE services not found");
                closeGatt();
                if (running) handler.postDelayed(() -> { if (running) attemptReconnect(); }, 3000);
                return;
            }
            enableNotifications(g, activeChar);
        }

        @Override
        public void onDescriptorWrite(BluetoothGatt g, BluetoothGattDescriptor descriptor, int status) {
            if (status == BluetoothGatt.GATT_SUCCESS) {
                postStatus("Telemetry live - guard monitoring in background");
                sendHandshakes();
            } else {
                postStatus("Could not subscribe to telemetry (status " + status + ")");
            }
        }

        @Override
        public void onCharacteristicChanged(BluetoothGatt g, BluetoothGattCharacteristic c) {
            if (Build.VERSION.SDK_INT < 33) handleFrame(c.getValue());
        }

        @Override
        public void onCharacteristicChanged(BluetoothGatt g, BluetoothGattCharacteristic c, byte[] value) {
            handleFrame(value);
        }
    };

    private void enableNotifications(BluetoothGatt g, BluetoothGattCharacteristic c) {
        try {
            g.setCharacteristicNotification(c, true);
            BluetoothGattDescriptor d = c.getDescriptor(CCCD);
            if (d == null) { postStatus("No CCCD descriptor - continuing anyway"); sendHandshakes(); return; }
            if (Build.VERSION.SDK_INT >= 33) {
                g.writeDescriptor(d, BluetoothGattDescriptor.ENABLE_NOTIFICATION_VALUE);
            } else {
                d.setValue(BluetoothGattDescriptor.ENABLE_NOTIFICATION_VALUE);
                g.writeDescriptor(d);
            }
        } catch (SecurityException e) {
            postStatus("Missing Bluetooth permission");
        }
    }

    // ---------------- Writes ----------------

    private void sendHandshakes() {
        writeAsync(HS1, 300);
        writeAsync(HS2, 700);
        writeAsync(HS3, 1000);
        writeAsync(QUERY_LIMIT, 1400);
    }

    private void writeAsync(final byte[] data, long delay) {
        handler.postDelayed(() -> writeNow(data), delay);
    }

    private void writeNow(byte[] data) {
        BluetoothGatt g = gatt;
        BluetoothGattCharacteristic c = activeChar;
        if (g == null || c == null) return;
        int props = c.getProperties();
        int writeType = ((props & BluetoothGattCharacteristic.PROPERTY_WRITE_TYPE_NO_RESPONSE) != 0)
                ? BluetoothGattCharacteristic.WRITE_TYPE_NO_RESPONSE
                : BluetoothGattCharacteristic.WRITE_TYPE_DEFAULT;
        try {
            if (Build.VERSION.SDK_INT >= 33) {
                g.writeCharacteristic(c, data, writeType);
            } else {
                c.setValue(data);
                c.setWriteType(writeType);
                g.writeCharacteristic(c);
            }
        } catch (SecurityException ignored) {}
    }

    // ---------------- Frame parsing: ZT CODE LEN DATA[LEN] CHECKSUM ----------------

    private void handleFrame(byte[] data) {
        if (data == null || data.length == 0) return;
        synchronized (frameBuf) {
            for (byte b : data) {
                if (frameLen >= frameBuf.length) frameLen = 0;
                frameBuf[frameLen++] = b;
            }
            parseFrames();
        }
    }

    private void parseFrames() {
        while (frameLen >= 4) {
            int len = frameBuf[2] & 0xFF;
            if (len > 20) { resync(); continue; }
            int total = len + 4;
            if (total > frameBuf.length) { resync(); continue; }
            if (frameLen < total) return; // wait for the rest of the frame
            int sum = 0;
            for (int i = 0; i < len + 3; i++) sum += (frameBuf[i] & 0xFF);
            if ((sum & 0xFF) == (frameBuf[3 + len] & 0xFF)) {
                dispatchFrame(frameBuf[1] & 0xFF, frameBuf, 3, len);
                System.arraycopy(frameBuf, total, frameBuf, 0, frameLen - total);
                frameLen -= total;
            } else {
                resync();
            }
        }
    }

    private void resync() {
        if (frameLen <= 0) return;
        System.arraycopy(frameBuf, 1, frameBuf, 0, frameLen - 1);
        frameLen--;
    }

    private void dispatchFrame(int code, byte[] buf, int off, int len) {
        switch (code) {
            case 0x11: // status: gear in bits 0-2
                if (len >= 1) {
                    currentGear = buf[off] & 0x07;
                    evaluateGesture();
                }
                break;
            case 0x13: // throttle ADC, 16-bit big-endian
                if (len >= 2) {
                    throttleAdc = ((buf[off] & 0xFF) << 8) | (buf[off + 1] & 0xFF);
                    evaluateGesture();
                }
                break;
            default:
                break;
        }
    }

    // ---------------- 2-second Eco stealth gesture ----------------

    private void evaluateGesture() {
        boolean held = (currentGear == 1) && (throttleAdc >= THROTTLE_ADC_TRIGGER);
        long now = System.currentTimeMillis();
        if (held) {
            if (ecoHoldStart == 0L) {
                ecoHoldStart = now;
            } else if (!ecoLatched && (now - ecoHoldStart) >= GESTURE_MS) {
                ecoLatched = true;
                triggerPanicLimiter();
            }
        } else {
            ecoHoldStart = 0L;
            ecoLatched = false;
        }
    }

    private void resetGesture() {
        ecoHoldStart = 0L;
        ecoLatched = false;
        throttleAdc = 0;
    }

    private void triggerPanicLimiter() {
        writeAsync(SET_LIMIT_20, 0);
        writeAsync(P10_TO_20, 300);
        writeAsync(GEAR_3, 600);
        vibratePattern();
        postStatus("STEALTH LIMITER TRIGGERED - locked to 20 km/h");
    }

    private void vibratePattern() {
        try {
            if (vibrator == null) vibrator = (Vibrator) getSystemService(Context.VIBRATOR_SERVICE);
            if (vibrator == null) return;
            long[] pattern = {0, 350, 150, 350, 150, 600};
            if (Build.VERSION.SDK_INT >= 26) {
                vibrator.vibrate(VibrationEffect.createWaveform(pattern, -1));
            } else {
                vibrator.vibrate(pattern, -1);
            }
        } catch (Exception ignored) {}
    }

    // ---------------- Cleanup ----------------

    private void closeGatt() {
        if (gatt != null) {
            try { gatt.disconnect(); } catch (Exception ignored) {}
            try { gatt.close(); } catch (Exception ignored) {}
            gatt = null;
        }
        activeChar = null;
        resetGesture();
    }

    private void closeAll() {
        stopScanInternal();
        closeGatt();
        releaseWakeLock();
    }
}
