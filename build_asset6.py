src = open('../incoming_files/d06c59d92_volpam-quickswitch_UI-polished201.html', encoding='utf-8').read()

# Re-apply the 2-second gesture timer (this build regressed to 5s)
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
    n = src.count(old)
    assert n > 0, "missing: " + old
    src = src.replace(old, new)
    print(f"x{n}: {old[:45]}")
# trigger line may use a different quote style
src = src.replace('textContent = "0.0s / 5.0s"', 'textContent = "0.0s / 2.0s"')
src = src.replace('textContent = "5.0s / 5.0s - TRIGGERED!"', 'textContent = "2.0s / 2.0s - TRIGGERED!"')

shim = open('shim_block.html', encoding='utf-8').read()
marker = '<meta name="theme-color" content="#0a0514">'
assert marker in src
src = src.replace(marker, marker + shim, 1)
open('app/src/main/assets/index.html', 'w', encoding='utf-8').write(src)
print('asset OK:', len(src))
