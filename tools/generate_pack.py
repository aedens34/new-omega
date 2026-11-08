#!/usr/bin/env python3
"""
Omega Guns - TACZ gunpack generator.

Regenerates everything under src/main/resources/assets/tacz/custom/omega_guns/ (JSON, bedrock models, PNG textures).
Pure standard library, no dependencies:   python tools/generate_pack.py
Edit GUNS / AMMO / ATTACHMENTS below, re-run, then run tools/build_zip.py.
"""
import json, os, random, shutil, struct, zlib

NS = "omega_guns"
HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "..", "src", "main", "resources", "assets", "tacz", "custom", "omega_guns")

# --------------------------------------------------------------------------
# tiny PNG writer
# --------------------------------------------------------------------------
def write_png(path, w, h, px):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    raw = b"".join(b"\x00" + bytes(c for p in px[y * w:(y + 1) * w] for c in p) for y in range(h))
    def chunk(t, d):
        c = struct.pack(">I", len(d)) + t + d
        return c + struct.pack(">I", zlib.crc32(t + d) & 0xFFFFFFFF)
    data = b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 6, 0, 0, 0))
    data += chunk(b"IDAT", zlib.compress(raw, 9)) + chunk(b"IEND", b"")
    with open(path, "wb") as f:
        f.write(data)

def jdump(path, obj):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(obj, f, indent=2, ensure_ascii=False)

def clamp(v): return max(0, min(255, int(v)))

# --------------------------------------------------------------------------
# palette texture: 4x4 grid of 16px swatches
# 0 dark metal | 1 gunmetal | 2 accent | 3 polymer | 4 lens | 5 glow | 6 steel | 7 rubber
# --------------------------------------------------------------------------
def palette_texture(path, body, accent, glow, seed):
    rnd = random.Random(seed)
    bd = tuple(clamp(c * 0.45) for c in body)
    swatches = [
        bd, body, accent, (28, 29, 32),
        (18, 34, 52), glow, (150, 154, 160), (14, 14, 15),
    ]
    px = [(0, 0, 0, 0)] * (64 * 64)
    px = list(px)
    for i, base in enumerate(swatches):
        sx, sy = (i % 4) * 16, (i // 4) * 16
        for y in range(16):
            for x in range(16):
                n = rnd.randint(-9, 9)
                edge = x in (0, 15) or y in (0, 15)
                grain = 8 if (y % 5 == 0 and i in (0, 1, 6)) else 0   # fine brushed-metal line
                k = (-26 if edge else 0) + grain
                if i == 5:  # emissive core is brighter in the middle
                    k = 40 - abs(x - 8) * 4 - abs(y - 8) * 2
                    n = rnd.randint(-4, 4)
                px[(sy + y) * 64 + sx + x] = (clamp(base[0] + n + k), clamp(base[1] + n + k), clamp(base[2] + n + k), 255)
    write_png(path, 64, 64, px)

def swatch_uv(i):
    u, v = (i % 4) * 16 + 2, (i // 4) * 16 + 2
    f = {"uv": [u, v], "uv_size": [12, 12]}
    return {k: dict(f, uv=list(f["uv"]), uv_size=list(f["uv_size"])) for k in ("north", "east", "south", "west", "up", "down")}

DARK, GUN, ACC, POLY, LENS, GLOW, STEEL, RUB = range(8)

# --------------------------------------------------------------------------
# bedrock model helpers.  Gun points toward -Z, +Y up, bore axis at y=0.
# --------------------------------------------------------------------------
class Model:
    def __init__(self, ident):
        self.ident, self.bones, self.order = ident, {}, []
    def bone(self, name, pivot=(0, 0, 0)):
        if name not in self.bones:
            self.bones[name] = {"name": name, "pivot": list(pivot), "cubes": []}
            self.order.append(name)
        return self.bones[name]
    def box(self, bone, x0, y0, z0, w, h, d, sw, rot=None, pivot=None):
        c = {"origin": [round(x0, 3), round(y0, 3), round(z0, 3)], "size": [w, h, d], "uv": swatch_uv(sw)}
        if rot:
            c["pivot"] = list(pivot); c["rotation"] = list(rot)
        self.bone(bone)["cubes"].append(c)
    def cx(self, bone, cx, cy, z0, w, h, d, sw, **k):   # centred on x/y
        self.box(bone, cx - w / 2, cy - h / 2, z0, w, h, d, sw, **k)
    def json(self):
        bones = []
        for n in self.order:
            b = dict(self.bones[n])
            if not b["cubes"]: del b["cubes"]
            if n != "root": b["parent"] = "root"
            bones.append(b)
        return {"format_version": "1.12.0", "minecraft:geometry": [{"description": {
            "identifier": self.ident, "texture_width": 64, "texture_height": 64,
            "visible_bounds_width": 6, "visible_bounds_height": 4, "visible_bounds_offset": [0, 1, 0]},
            "bones": bones}]}
    def side_rects(self, skip=("mag_extended_1", "mag_extended_2", "mag_extended_3", "sight_folded")):
        out = []
        for n in self.order:
            if n in skip: continue
            for c in self.bones[n]["cubes"]:
                sw = None
                u = c["uv"]["north"]["uv"]
                sw = (u[1] // 16) * 4 + (u[0] // 16)
                if c.get("rotation"):
                    continue
                out.append((c["origin"][2], c["origin"][1], c["size"][2], c["size"][1], sw))
        return out

# --------------------------------------------------------------------------
# GUN DEFINITIONS - every gun differs in ammo, action, stats and silhouette
# --------------------------------------------------------------------------
GUNS = [
 dict(id="vanta_sr9", name="Vanta SR-9", ammo="apx_338", kind="bolt", action="manual_action", mag=5, ext=[7, 9, 11],
      dmg=34, hs=2.6, speed=170, rpm=45, ads=0.34, wt=6.2, blen=26, hg=12, stock="skeletal", magstyle="box", maghgt=5,
      body=(70, 76, 84), accent=(0, 200, 255), glow=(0, 220, 255), rlen=17, muzzle="brake",
      rec=(2.6, 0.5), inacc=(3.2, 6.0, 2.0, 1.2, 0.0), reload=(3.4, 2.9), tip="Long-action precision rifle. Hits like a truck at range."),
 dict(id="aegis_rs1", name="Aegis RS-1 Railshot", ammo="gauss_slug", kind="semi", action="closed_bolt", mag=8, ext=[10, 12, 14],
      dmg=27, hs=2.3, speed=260, rpm=110, ads=0.30, wt=7.4, blen=30, hg=18, stock="solid", magstyle="cell", maghgt=4,
      body=(54, 58, 66), accent=(255, 90, 0), glow=(255, 120, 20), rlen=19, muzzle="rail",
      rec=(1.7, 0.4), inacc=(2.8, 5.2, 1.8, 1.0, 0.0), reload=(2.8, 2.3), tip="Magnetic accelerator marksman rifle. Insane muzzle velocity."),
 dict(id="specter_dmr", name="Specter DMR", ammo="dmr_762", kind="semi", action="closed_bolt", mag=12, ext=[16, 20, 25],
      dmg=19, hs=2.2, speed=140, rpm=190, ads=0.24, wt=4.9, blen=22, hg=14, stock="solid", magstyle="box", maghgt=6,
      body=(48, 52, 50), accent=(120, 255, 90), glow=(120, 255, 90), rlen=16, muzzle="compensator",
      rec=(1.3, 0.55), inacc=(2.4, 4.6, 1.5, 0.8, 0.0), reload=(2.5, 2.0), tip="Fast semi-auto designated marksman rifle."),
 dict(id="helios_lancer", name="Helios Lancer", ammo="plasma_cell", kind="semi", action="closed_bolt", mag=6, ext=[8, 10, 12],
      dmg=36, hs=2.0, speed=95, rpm=65, ads=0.38, wt=8.0, blen=24, hg=16, stock="solid", magstyle="cell", maghgt=5,
      body=(210, 214, 222), accent=(150, 80, 255), glow=(190, 90, 255), rlen=18, muzzle="emitter",
      rec=(1.9, 0.3), inacc=(2.6, 5.5, 1.7, 0.9, 0.0), reload=(3.0, 2.5), tip="Plasma lancer. Slow bolts, brutal damage, almost no drop."),
 dict(id="kestrel_x", name="Kestrel-X", ammo="dmr_762", kind="bolt", action="manual_action", mag=10, ext=[12, 15, 18],
      dmg=28, hs=2.5, speed=150, rpm=70, ads=0.26, wt=4.4, blen=20, hg=10, stock="bullpup", magstyle="box", maghgt=5,
      body=(80, 70, 56), accent=(255, 190, 40), glow=(255, 190, 40), rlen=24, muzzle="brake",
      rec=(2.0, 0.6), inacc=(2.7, 5.0, 1.6, 0.9, 0.0), reload=(2.6, 2.1), tip="Compact bullpup bolt-action. Short, quick, deadly."),
 dict(id="titan_breaker", name="Titan Breaker", ammo="hv_50", kind="semi", action="closed_bolt", mag=5, ext=[7, 9, 11],
      dmg=52, hs=2.0, speed=185, rpm=55, ads=0.52, wt=12.5, blen=32, hg=20, stock="solid", magstyle="box", maghgt=6,
      body=(60, 64, 60), accent=(255, 50, 50), glow=(255, 50, 50), rlen=20, muzzle="heavy_brake",
      rec=(4.2, 0.9), inacc=(3.6, 8.0, 2.4, 1.4, 0.0), reload=(4.0, 3.4), tip="Anti-materiel semi-auto. Heavy, loud, armor-piercing."),
 dict(id="nyx_suppressed", name="Nyx-S Whisper", ammo="subsonic_300", kind="bolt", action="manual_action", mag=8, ext=[10, 12, 15],
      dmg=21, hs=2.7, speed=105, rpm=60, ads=0.28, wt=5.1, blen=24, hg=12, stock="skeletal", magstyle="box", maghgt=4,
      body=(26, 28, 32), accent=(70, 70, 80), glow=(60, 60, 70), rlen=16, muzzle="integral_suppressor",
      rec=(1.1, 0.25), inacc=(2.2, 4.2, 1.2, 0.7, 0.0), reload=(2.7, 2.2), tip="Integrally suppressed subsonic bolt rifle."),
 dict(id="orion_arc", name="Orion ARC-3", ammo="flechette", kind="burst", action="closed_bolt", mag=24, ext=[30, 36, 42],
      dmg=11, hs=2.1, speed=210, rpm=620, ads=0.22, wt=5.6, blen=18, hg=12, stock="solid", magstyle="box", maghgt=5,
      body=(36, 40, 70), accent=(0, 255, 200), glow=(0, 255, 200), rlen=15, muzzle="compensator",
      rec=(0.9, 0.5), inacc=(2.0, 4.0, 1.4, 0.8, 0.0), reload=(2.6, 2.1), tip="3-round burst flechette rifle. Tight, fast groups."),
 dict(id="valkyrie_mk2", name="Valkyrie Mk2", ammo="gauss_slug", kind="semi", action="closed_bolt", mag=14, ext=[18, 22, 26],
      dmg=17, hs=2.2, speed=240, rpm=230, ads=0.20, wt=4.2, blen=17, hg=10, stock="skeletal", magstyle="cell", maghgt=4,
      body=(88, 92, 100), accent=(255, 60, 160), glow=(255, 60, 160), rlen=14, muzzle="rail",
      rec=(1.0, 0.4), inacc=(1.9, 3.8, 1.2, 0.7, 0.0), reload=(2.3, 1.8), tip="Light gauss carbine for mobile marksman work."),
 dict(id="reaper_lb", name="Reaper LB-50", ammo="apx_338", kind="bolt", action="manual_action", mag=4, ext=[5, 6, 8],
      dmg=46, hs=2.9, speed=215, rpm=34, ads=0.44, wt=9.4, blen=40, hg=16, stock="skeletal", magstyle="box", maghgt=4,
      body=(34, 36, 38), accent=(220, 220, 230), glow=(220, 220, 230), rlen=18, muzzle="heavy_brake",
      rec=(3.4, 0.7), inacc=(2.0, 6.5, 1.5, 0.6, 0.0), reload=(3.8, 3.2), tip="Extreme long-range rifle. Fastest rounds, slowest hands."),
 dict(id="zenith_zr4", name="Zenith ZR-4", ammo="plasma_cell", kind="semi", action="open_bolt", mag=3, ext=[4, 5, 6],
      dmg=58, hs=1.9, speed=80, rpm=38, ads=0.46, wt=10.2, blen=28, hg=22, stock="solid", magstyle="cell", maghgt=6,
      body=(26, 70, 82), accent=(80, 255, 255), glow=(80, 255, 255), rlen=22, muzzle="emitter",
      rec=(3.0, 0.2), inacc=(3.0, 7.0, 2.0, 1.1, 0.0), reload=(3.6, 3.1), tip="Heavy plasma railgun. Three charges, one-shot potential."),
 dict(id="cobalt_ranger", name="Cobalt Ranger", ammo="dmr_762", kind="semi", action="closed_bolt", mag=15, ext=[20, 25, 30],
      dmg=14, hs=2.0, speed=125, rpm=260, ads=0.18, wt=3.6, blen=14, hg=8, stock="skeletal", magstyle="box", maghgt=6,
      body=(30, 70, 120), accent=(255, 255, 255), glow=(90, 170, 255), rlen=13, muzzle="compensator",
      rec=(0.8, 0.45), inacc=(1.7, 3.4, 1.0, 0.6, 0.0), reload=(2.0, 1.6), tip="Compact semi-auto ranger. Light and handy."),
]

AMMO = [
 dict(id="apx_338", name="APX .338 Match", stack=30, body=(190, 150, 60), tip=(220, 220, 230), glow=(255, 200, 80)),
 dict(id="dmr_762", name="DMR 7.62 Hybrid", stack=60, body=(180, 130, 50), tip=(120, 120, 130), glow=(255, 160, 60)),
 dict(id="gauss_slug", name="Gauss Slug", stack=40, body=(70, 80, 95), tip=(255, 120, 20), glow=(255, 130, 30)),
 dict(id="plasma_cell", name="Plasma Cell", stack=24, body=(40, 40, 60), tip=(170, 90, 255), glow=(190, 100, 255)),
 dict(id="flechette", name="Flechette Mag Round", stack=90, body=(60, 110, 110), tip=(0, 255, 200), glow=(0, 255, 200)),
 dict(id="hv_50", name="HV .50 Penetrator", stack=20, body=(150, 110, 40), tip=(60, 60, 64), glow=(255, 70, 70)),
 dict(id="subsonic_300", name="Subsonic .300 Quiet", stack=40, body=(120, 120, 128), tip=(30, 30, 34), glow=(120, 120, 130)),
]

# type, id, name, weight, extra data, extra display
ATTACHMENTS = [
 ("scope", "holo_x1", "Omega Holo Sight", 0.2, {"zoom": [1.25]}),
 ("scope", "scope_4x", "Omega 4x Marksman Scope", 0.45, {"zoom": [4.0]}),
 ("scope", "scope_8x", "Omega 8x Long-Range Scope", 0.7, {"zoom": [8.0]}),
 ("scope", "scope_var_4_12", "Omega 4-12x Variable Scope", 0.8, {"zoom": [4.0, 8.0, 12.0]}),
 ("scope", "thermal_6x", "Omega 6x Thermal Optic", 0.9, {"zoom": [6.0]}),
 ("muzzle", "suppressor", "Omega Suppressor", 0.5, {"silence": {"distance_addend": -45, "use_silence_sound": True}}),
 ("muzzle", "brake", "Omega Muzzle Brake", 0.3, {}),
 ("muzzle", "compensator", "Omega Compensator", 0.25, {}),
 ("grip", "vgrip", "Omega Vertical Grip", 0.25, {}),
 ("grip", "agrip", "Omega Angled Grip", 0.2, {}),
 ("stock", "tac_stock", "Omega Tactical Stock", 0.4, {}),
 ("laser", "laser_mod", "Omega Laser Module", 0.15, {}),
 ("extended_mag", "extmag_1", "Omega Extended Mag I", 0.1, {"extended_mag_level": 1}),
 ("extended_mag", "extmag_2", "Omega Extended Mag II", 0.2, {"extended_mag_level": 2}),
 ("extended_mag", "extmag_3", "Omega Extended Mag III", 0.3, {"extended_mag_level": 3}),
]

# --------------------------------------------------------------------------
# build gun model
# --------------------------------------------------------------------------
def build_gun_model(g):
    m = Model(f"geometry.{NS}.{g['id']}")
    m.bone("root")
    rl, bl, hg = g["rlen"], g["blen"], g["hg"]
    zf = -rl / 2 - 1                # front of receiver
    zr = zf + rl                    # rear of receiver
    bullpup = g["stock"] == "bullpup"
    if bullpup:
        zr += 10
    # receiver + rails
    m.cx("root", 0, -0.2, zf, 3.4, 4.6, zr - zf, GUN)
    m.cx("root", 0, 2.4, zf, 2.0, 0.9, zr - zf, DARK)                     # top rail
    for i in range(int((zr - zf) // 2)):
        m.cx("root", 0, 3.0, zf + 0.5 + i * 2, 2.2, 0.4, 0.8, STEEL)       # rail teeth
    m.cx("root", 0, 0.9, zf - 0.2, 3.7, 0.4, rl * 0.45, ACC)               # accent stripe
    for s in (-1, 1):                                                       # glow strips
        m.cx("root", s * 1.75, -0.4, zf + 2, 0.2, 0.7, rl * 0.5, GLOW)
    # barrel / handguard
    m.cx("root", 0, 0, zf - bl, 1.6, 1.6, bl, DARK)
    m.cx("root", 0, -0.2, zf - hg, 3.3, 3.2, hg, POLY)
    m.cx("root", 0, 1.5, zf - hg + 0.5, 1.2, 0.3, hg - 1, ACC)
    for s in (-1, 1):
        for i in range(max(1, hg // 4)):
            m.cx("root", s * 1.7, -0.3, zf - hg + 1 + i * 4, 0.2, 1.4, 2, DARK)  # vent slots
    # muzzle default bone
    m.bone("muzzle_default", (0, 0, zf - bl))
    mz = g["muzzle"]
    zt = zf - bl
    if mz in ("brake", "heavy_brake", "compensator"):
        L = 5 if mz == "heavy_brake" else 3.5
        W = 2.8 if mz == "heavy_brake" else 2.3
        m.cx("muzzle_default", 0, 0, zt - L, W, W, L, STEEL)
        for i in range(3):
            m.cx("muzzle_default", 0, 0, zt - L + 0.6 + i * 1.1, W + 0.4, 0.5, 0.45, DARK)
    elif mz == "rail":
        m.cx("muzzle_default", 0, 0, zt - 6, 2.6, 2.6, 6, DARK)
        for s in (-1, 1):
            m.cx("muzzle_default", s * 1.4, 0, zt - 6, 0.4, 1.2, 6, GLOW)
    elif mz == "emitter":
        m.cx("muzzle_default", 0, 0, zt - 4, 3.0, 3.0, 4, STEEL)
        m.cx("muzzle_default", 0, 0, zt - 4.6, 2.0, 2.0, 0.6, GLOW)
    elif mz == "integral_suppressor":
        m.cx("muzzle_default", 0, 0, zt - 14, 3.0, 3.0, 14, DARK)
        m.cx("muzzle_default", 0, 0, zt - 14.4, 2.0, 2.0, 0.4, RUB)
    # stock
    m.bone("stock_default", (0, 0, zr))
    if g["stock"] == "solid":
        m.cx("stock_default", 0, -1.0, zr, 2.8, 5.2, 14, POLY)
        m.cx("stock_default", 0, 1.8, zr + 2, 2.4, 1.2, 9, RUB)
        m.cx("stock_default", 0, -1.0, zr + 14, 3.0, 6.0, 1.4, RUB)
        m.cx("stock_default", 0, -1.0, zr + 5, 2.9, 1.0, 5, ACC)
    elif g["stock"] == "skeletal":
        for yy in (1.2, -3.2):
            m.cx("stock_default", 0, yy, zr, 1.4, 1.0, 14, DARK)
        m.cx("stock_default", 0, -1.0, zr + 12, 1.4, 5.2, 1.0, DARK)
        m.cx("stock_default", 0, -1.0, zr + 14, 3.0, 6.0, 1.6, RUB)
        m.cx("stock_default", 0, 2.0, zr + 4, 2.2, 1.2, 6, POLY)
    else:  # bullpup butt pad
        m.cx("stock_default", 0, -0.2, zr, 3.2, 5.0, 1.8, RUB)
        m.cx("stock_default", 0, 2.4, zr - 8, 2.4, 1.6, 8, POLY)
    # pistol grip + guard
    gz = zr - 4 if not bullpup else zf + 6
    m.bone("grip_default", (0, -2.5, gz))
    m.box("grip_default", -1.2, -9.5, gz, 2.4, 7, 3, POLY, rot=(-18, 0, 0), pivot=(0, -2.5, gz))
    m.cx("grip_default", 0, -3.4, gz - 7.5, 1.2, 0.7, 7, DARK)
    m.cx("grip_default", 0, -4.8, gz - 7.5, 1.2, 1.6, 0.7, DARK)
    m.cx("root", 0, -4.3, gz - 2.2, 0.5, 2.0, 0.5, STEEL)                  # trigger
    # magazine well + mags
    mz0 = zf + rl * (0.55 if not bullpup else 0.8) - 2.2
    mw = 4.2 if g["magstyle"] == "cell" else 3.0
    md = 5.0 if g["magstyle"] == "cell" else 4.4
    def mag(bone, extra):
        h = g["maghgt"] + extra
        sw = POLY if g["magstyle"] == "box" else DARK
        m.cx(bone, 0, -2.4 - h / 2, mz0, mw, h, md, sw)
        m.cx(bone, 0, -2.4 - h - 0.3, mz0 - 0.2, mw + 0.4, 0.6, md + 0.4, RUB)
        if g["magstyle"] == "cell":
            for s in (-1, 1):
                m.cx(bone, s * (mw / 2 + 0.05), -2.4 - h / 2, mz0 + 0.8, 0.15, h - 1.5, md - 1.6, GLOW)
        else:
            m.cx(bone, 0, -2.4 - h / 2, mz0 + md / 2 - 0.1, 0.8, h - 1, 0.3, ACC)
    m.bone("mag_standard", (0, -2.4, mz0))
    mag("mag_standard", 0)
    for lvl, ex in ((1, 1.8), (2, 3.6), (3, 5.4)):
        m.bone(f"mag_extended_{lvl}", (0, -2.4, mz0))
        mag(f"mag_extended_{lvl}", ex)
    m.cx("root", 0, -2.8, mz0 - 1.2, mw + 1, 1.2, md + 2.4, GUN)           # mag well
    # bolt
    if g["action"] == "manual_action" or g["kind"] == "bolt":
        m.bone("bolt", (0, 1.0, zf + rl * 0.35))
        m.cx("bolt", 2.4, 0.9, zf + rl * 0.35, 2.4, 0.7, 0.8, STEEL)
        m.cx("bolt", 4.0, 0.9, zf + rl * 0.35 - 0.1, 1.2, 1.2, 1.2, RUB)
    else:
        m.bone("bolt", (0, 1.0, zf + rl * 0.35))
        m.cx("bolt", 1.8, 0.9, zf + rl * 0.3, 0.5, 1.0, 2.2, STEEL)
    # iron sights (default) and folded
    m.bone("sight", (0, 3.4, zr - 2))
    m.cx("sight", 0, 4.2, zr - 3, 1.6, 1.6, 0.8, DARK)
    m.cx("sight", 0, 4.3, zr - 3.1, 0.5, 0.7, 0.2, GLOW)
    m.cx("sight", 0, 4.0, zf - 1, 0.7, 1.4, 0.8, DARK)
    m.bone("sight_folded", (0, 3.0, zr - 2))
    m.cx("sight_folded", 0, 3.4, zr - 3, 1.6, 0.5, 0.8, DARK)
    # position / node bones (no cubes)
    m.bone("iron_view", (0, 4.4, zr - 3.5))
    m.bone("scope_pos", (0, 3.4, zf + rl * 0.35))
    m.bone("muzzle_pos", (0, 0, zf - bl - 3))
    m.bone("muzzle_flash", (0, 0, zf - bl - 4))
    m.bone("grip_pos", (0, -1.8, zf - hg * 0.55))
    m.bone("stock_pos", (0, 0, zr))
    m.bone("laser_pos", (0, -1.0, zf - hg + 1))
    m.bone("shell", (1.8, 1.0, zf + rl * 0.35))
    m.bone("lefthand_pos", (0, -2.2, zf - hg * 0.5))
    m.bone("righthand_pos", (0, -6.0, gz + 1.5))
    m.bone("carry", (0, 4.0, 0))
    return m

def draw_icon(m, path, glow, w=128, h=64):
    rects = m.side_rects()
    zmin = min(r[0] for r in rects); zmax = max(r[0] + r[2] for r in rects)
    ymin = min(r[1] for r in rects); ymax = max(r[1] + r[3] for r in rects)
    sc = min((w - 10) / (zmax - zmin), (h - 10) / (ymax - ymin))
    ox = (w - (zmax - zmin) * sc) / 2; oy = (h - (ymax - ymin) * sc) / 2
    cols = {DARK: (36, 38, 42), GUN: (86, 92, 100), ACC: glow, POLY: (52, 54, 58), LENS: (30, 60, 90),
            GLOW: glow, STEEL: (170, 174, 180), RUB: (24, 24, 26)}
    px = [(0, 0, 0, 0)] * (w * h)
    px = list(px)
    for z0, y0, d, hh, sw in rects:
        # flip so muzzle (-z) points right
        x1 = int(w - (ox + (z0 - zmin) * sc)); x0 = int(w - (ox + (z0 + d - zmin) * sc))
        y1 = int(h - (oy + (y0 - ymin) * sc)); y0p = int(h - (oy + (y0 + hh - ymin) * sc))
        c = cols[sw]
        for y in range(max(0, y0p), min(h, max(y1, y0p + 1))):
            for x in range(max(0, x0), min(w, max(x1, x0 + 1))):
                px[y * w + x] = (c[0], c[1], c[2], 255)
    write_png(path, w, h, px)

# --------------------------------------------------------------------------
# attachment / ammo models
# --------------------------------------------------------------------------
def build_attachment_model(kind, aid):
    m = Model(f"geometry.{NS}.att_{aid}")
    m.bone("root")
    if kind == "scope":
        if aid == "holo_x1":
            m.bone("scope_body")
            m.cx("scope_body", 0, 0.4, -1, 3.6, 0.6, 5, DARK)
            for s in (-1, 1):
                m.cx("scope_body", s * 1.6, 2.3, -1, 0.4, 3.6, 0.6, DARK)
                m.cx("scope_body", s * 1.6, 2.3, 2.6, 0.4, 3.6, 0.6, DARK)
            m.cx("scope_body", 0, 4.3, -1, 3.6, 0.4, 3.8, DARK)
            m.cx("scope_body", 0, 2.3, 2.6, 2.8, 3.2, 0.2, LENS)
            m.bone("scope_view", (0, 2.4, 2.8))
            m.cx("scope_view", 0, 2.4, 2.9, 2.6, 3.0, 0.1, LENS)
            m.bone("sight", (0, 2.4, 2.8))
        else:
            L = {"scope_4x": 12, "scope_8x": 17, "scope_var_4_12": 15, "thermal_6x": 13}[aid]
            col = DARK
            m.bone("scope_body")
            m.cx("scope_body", 0, 0.5, -L / 2, 2.4, 1.4, L, DARK)               # mount
            m.cx("scope_body", 0, 3.2, -L / 2 + 1, 2.8, 2.8, L - 2, col)        # main tube
            m.cx("scope_body", 0, 3.2, -L / 2 - 2.4, 4.0, 4.0, 3.4, col)        # objective
            m.cx("scope_body", 0, 3.2, L / 2 - 0.4, 3.4, 3.4, 2.4, col)         # ocular
            m.cx("scope_body", 0, 5.2, 0, 1.4, 0.9, 1.6, STEEL)                  # elevation turret
            m.cx("scope_body", 1.9, 3.2, 0, 0.9, 1.4, 1.6, STEEL)                # windage turret
            m.cx("scope_body", 0, 3.2, -L / 2 - 2.5, 3.4, 3.4, 0.2, GLOW if aid == "thermal_6x" else LENS)
            m.cx("scope_body", 0, 3.2, L / 2 + 2.0, 3.0, 3.0, 0.2, LENS)
            m.cx("scope_body", 0, 3.2, 1.0, 3.0, 3.0, 0.8, ACC)                  # accent ring
            m.bone("scope_view", (0, 3.2, L / 2 + 2.1))
            m.cx("scope_view", 0, 3.2, L / 2 + 2.2, 2.6, 2.6, 0.1, LENS)
    elif kind == "muzzle":
        m.bone("muzzle_body")
        if aid == "suppressor":
            m.cx("muzzle_body", 0, 0, -11, 3.4, 3.4, 11, DARK)
            for i in range(4):
                m.cx("muzzle_body", 0, 0, -10 + i * 2.6, 3.7, 3.7, 0.4, STEEL)
        elif aid == "brake":
            m.cx("muzzle_body", 0, 0, -4.5, 2.8, 2.8, 4.5, STEEL)
            for i in range(4):
                m.cx("muzzle_body", 0, 0, -4 + i * 1.0, 3.2, 0.6, 0.5, DARK)
        else:
            m.cx("muzzle_body", 0, 0, -3.5, 2.4, 2.4, 3.5, STEEL)
            m.cx("muzzle_body", 0, 1.3, -3.5, 1.4, 0.5, 3.5, DARK)
    elif kind == "grip":
        m.bone("grip_body")
        if aid == "vgrip":
            m.cx("grip_body", 0, -4, -1.2, 2.2, 7, 2.4, POLY)
            m.cx("grip_body", 0, -0.4, -2.2, 2.8, 0.8, 4.4, DARK)
        else:
            m.box("grip_body", -1.1, -6.5, -1.2, 2.2, 6, 2.4, POLY, rot=(-40, 0, 0), pivot=(0, -0.5, -1))
            m.cx("grip_body", 0, -0.4, -2.2, 2.8, 0.8, 4.4, DARK)
    elif kind == "stock":
        m.bone("stock_body")
        m.cx("stock_body", 0, 0, 0, 2.6, 4.2, 12, POLY)
        m.cx("stock_body", 0, 2.0, 1, 2.2, 1.0, 7, RUB)
        m.cx("stock_body", 0, 0, 12, 3.0, 5.4, 1.4, RUB)
    elif kind == "laser":
        m.bone("laser_body")
        m.cx("laser_body", 0, 0, -3.5, 2.0, 2.0, 3.5, DARK)
        m.cx("laser_body", 0, 0, -3.8, 0.8, 0.8, 0.3, GLOW)
    elif kind == "extended_mag":
        m.bone("mag_body")
        n = int(aid[-1])
        m.cx("mag_body", 0, -3 - n * 1.2, 0, 3, 6 + n * 2.4, 4.4, POLY)
        m.cx("mag_body", 0, -6.3 - n * 2.4, -0.2, 3.4, 0.6, 4.8, RUB)
    return m

def build_ammo_model(a):
    m = Model(f"geometry.{NS}.ammo_{a['id']}")
    m.bone("root")
    m.cx("root", 0, 0, -1.2, 1.4, 1.4, 4.2, GUN)        # casing
    m.cx("root", 0, 0, -3.0, 1.0, 1.0, 1.8, ACC)        # projectile tip
    m.cx("root", 0, 0, 3.0, 1.5, 1.5, 0.4, STEEL)       # rim
    m.cx("root", 0, 0, 1.0, 1.5, 1.5, 0.5, GLOW)        # coloured band
    return m

# --------------------------------------------------------------------------
# JSON builders
# --------------------------------------------------------------------------
def gun_data(g):
    pitch = g["rec"][0]; yaw = g["rec"][1]
    ia = g["inacc"]
    burst = g["kind"] == "burst"
    d = {
        "ammo": f"{NS}:{g['ammo']}",
        "ammo_amount": g["mag"],
        "extended_mag_ammo_amount": g["ext"],
        "bolt": g["action"],
        "rpm": g["rpm"],
        "fire_mode": ["burst"] if burst else ["semi"],
        "aim_time": g["ads"],
        "draw_time": round(0.35 + g["wt"] * 0.03, 2),
        "put_away_time": round(0.3 + g["wt"] * 0.02, 2),
        "sprint_time": round(0.2 + g["wt"] * 0.015, 2),
        "weight": g["wt"],
        "allow_attachment_types": ["scope", "muzzle", "grip", "stock", "laser", "extended_mag"],
        "reload": {"type": "magazine", "infinite": False,
                   "feed": {"empty": round(g["reload"][0] * 0.7, 2), "tactical": round(g["reload"][1] * 0.7, 2)},
                   "cooldown": {"empty": g["reload"][0], "tactical": g["reload"][1]}},
        "bullet": {
            "life": 6, "bullet_amount": 1, "damage": g["dmg"],
            "extra_damage": {"armor_ignore": 0.15 if g["dmg"] < 40 else 0.35,
                             "head_shot_multiplier": g["hs"],
                             "damage_adjust": [{"distance": 60, "damage": g["dmg"]},
                                               {"distance": 160, "damage": round(g["dmg"] * 0.9, 1)},
                                               {"distance": "infinite", "damage": round(g["dmg"] * 0.75, 1)}]},
            "speed": g["speed"], "gravity": round(0.05 if g["speed"] < 130 else 0.025, 3),
            "knockback": round(0.05 + g["dmg"] / 400, 3), "friction": 0.01, "pierce": 1 if g["dmg"] < 45 else 3,
        },
        "recoil": {"pitch": [{"time": 0.0, "value": [pitch * 0.8, pitch]}, {"time": 0.25, "value": [-pitch * 0.1, 0]}],
                   "yaw": [{"time": 0.0, "value": [-yaw, yaw]}, {"time": 0.25, "value": [0, 0]}]},
        "inaccuracy": {"stand": ia[0], "move": ia[1], "sneak": ia[2], "lie": ia[3], "aim": ia[4]},
    }
    if burst:
        d["burst_data"] = {"count": 3, "bpm": g["rpm"], "continuous_shoot": False, "min_interval": 0.12}
    return d

def main():
    if os.path.isdir(OUT):
        shutil.rmtree(OUT)
    A = os.path.join(OUT, "assets", NS)
    D = os.path.join(OUT, "data", NS)
    lang = {}
    jdump(os.path.join(OUT, "gunpack.meta.json"), {
        "namespace": NS, "name": "Omega Guns", "version": "1.0.0", "license": "MIT",
        "authors": ["Omega Guns contributors"],
        "description": "Futuristic precision rifles, custom ammo and attachments for TACZ.",
        "dependencies": {"tacz": "[1.0.0,)"}})

    # ammo
    for i, a in enumerate(AMMO):
        lang[f"{NS}.ammo.{a['id']}.name"] = a["name"]
        lang[f"{NS}.ammo.{a['id']}.desc"] = "Omega Guns ammunition"
        jdump(os.path.join(D, "index", "ammo", f"{a['id']}.json"),
              {"name": f"{NS}.ammo.{a['id']}.name", "display": f"{NS}:{a['id']}_display", "stack_size": a["stack"]})
        jdump(os.path.join(A, "display", "ammo", f"{a['id']}_display.json"),
              {"model": f"{NS}:ammo/{a['id']}_geo", "texture": f"{NS}:ammo/uv/{a['id']}",
               "slot": f"{NS}:ammo/slot/{a['id']}"})
        m = build_ammo_model(a)
        jdump(os.path.join(A, "geo_models", "ammo", f"{a['id']}_geo.json"), m.json())
        palette_texture(os.path.join(A, "textures", "ammo", "uv", f"{a['id']}.png"), a["body"], a["tip"], a["glow"], 900 + i)
        draw_icon(m, os.path.join(A, "textures", "ammo", "slot", f"{a['id']}.png"), a["glow"], 32, 32)

    # attachments
    for i, (kind, aid, name, wt, extra) in enumerate(ATTACHMENTS):
        lang[f"{NS}.attachment.{aid}.name"] = name
        jdump(os.path.join(D, "index", "attachments", f"{aid}.json"),
              {"name": f"{NS}.attachment.{aid}.name", "display": f"{NS}:{aid}_display",
               "data": f"{NS}:{aid}_data", "type": kind, "sort": i + 1})
        data = {"weight": wt}
        data.update(extra)
        jdump(os.path.join(D, "data", "attachments", f"{aid}_data.json"), data)
        disp = {"slot": f"{NS}:attachment/slot/{aid}", "model": f"{NS}:attachment/{aid}_geo",
                "texture": f"{NS}:attachment/uv/{aid}"}
        if kind == "scope":
            disp["scope"] = aid != "holo_x1"
            disp["sight"] = aid == "holo_x1"
            disp["zoom"] = extra["zoom"][0]
        jdump(os.path.join(A, "display", "attachments", f"{aid}_display.json"), disp)
        m = build_attachment_model(kind, aid)
        jdump(os.path.join(A, "geo_models", "attachment", f"{aid}_geo.json"), m.json())
        palette_texture(os.path.join(A, "textures", "attachment", "uv", f"{aid}.png"),
                        (46, 50, 56), (255, 140, 0), (60, 255, 140) if aid != "thermal_6x" else (255, 90, 40), 700 + i)
        draw_icon(m, os.path.join(A, "textures", "attachment", "slot", f"{aid}.png"), (255, 140, 0), 64, 64)

    # guns
    for i, g in enumerate(GUNS):
        gid = g["id"]
        lang[f"{NS}.gun.{gid}.name"] = g["name"]
        lang[f"{NS}.gun.{gid}.desc"] = g["tip"]
        jdump(os.path.join(D, "index", "guns", f"{gid}.json"),
              {"name": f"{NS}.gun.{gid}.name", "tooltip": f"{NS}.gun.{gid}.desc",
               "display": f"{NS}:{gid}_display", "data": f"{NS}:{gid}_data",
               "type": "sniper", "item_type": "modern_kinetic", "sort": i + 1})
        jdump(os.path.join(D, "data", "guns", f"{gid}_data.json"), gun_data(g))
        jdump(os.path.join(A, "display", "guns", f"{gid}_display.json"), {
            "model": f"{NS}:gun/{gid}_geo", "texture": f"{NS}:gun/uv/{gid}",
            "slot": f"{NS}:gun/slot/{gid}", "hud": f"{NS}:gun/hud/{gid}", "hud_empty": f"{NS}:gun/hud/{gid}",
            "use_default_animation": "rifle",
            "transform": {"scale": {"hip": [1, 1, 1], "thirdperson": [0.8, 0.8, 0.8], "ground": [0.7, 0.7, 0.7], "fixed": [0.6, 0.6, 0.6]}},
        })
        m = build_gun_model(g)
        jdump(os.path.join(A, "geo_models", "gun", f"{gid}_geo.json"), m.json())
        palette_texture(os.path.join(A, "textures", "gun", "uv", f"{gid}.png"), g["body"], g["accent"], g["glow"], 100 + i)
        draw_icon(m, os.path.join(A, "textures", "gun", "slot", f"{gid}.png"), g["glow"])
        draw_icon(m, os.path.join(A, "textures", "gun", "hud", f"{gid}.png"), g["glow"])

    jdump(os.path.join(A, "lang", "en_us.json"), lang)
    print(f"Generated {len(GUNS)} guns, {len(AMMO)} ammo types, {len(ATTACHMENTS)} attachments -> {os.path.abspath(OUT)}")

if __name__ == "__main__":
    main()
