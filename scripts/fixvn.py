from fontTools.ttLib import TTFont
import glob, os, sys, re

WIN_ASCENT_RATIO  = 1.45
WIN_DESCENT_RATIO = 0.50

INPUT_DIR  = sys.argv[1] if len(sys.argv) > 1 else "fonts-src"
OUTPUT_DIR = sys.argv[2] if len(sys.argv) > 2 else "fonts-out"

# Tìm đệ quy tất cả KF_*.ttf trong INPUT_DIR và các thư mục con
files = sorted(glob.glob(os.path.join(INPUT_DIR, "**", "KF_*.ttf"), recursive=True))

if not files:
    print(f"Không tìm thấy file KF_*.ttf trong: {INPUT_DIR}")
    sys.exit(1)

print(f"Tìm thấy {len(files)} file, bắt đầu xử lý...\n")

def get_family_name(filename):
    """
    Lấy tên family từ tên file.
    VD: KF_ChareInk7SP-Bold.ttf    → ChareInk7SP
        KF_Fern_Text-Regular.ttf   → Fern Text
        KF_Fern_Micro-Italic.ttf   → Fern Micro
    """
    name = re.sub(r"^KF_", "", filename)
    name = re.sub(r"\.ttf$", "", name)
    name = re.sub(r"[-_](Bold|Italic|BoldItalic|Regular|Light|Medium|SemiBold|ExtraBold|Black|Testing).*$", "", name, flags=re.IGNORECASE)
    name = name.replace("_", " ").strip()
    return name

for src in files:
    basename = os.path.basename(src)
    family   = get_family_name(basename)

    family_dir = os.path.join(OUTPUT_DIR, family)
    os.makedirs(family_dir, exist_ok=True)

    print(f"Processing: {basename}")
    print(f"  Family: {family} → {family_dir}")

    f    = TTFont(src)
    os2  = f["OS/2"]
    head = f["head"]
    hhea = f["hhea"]
    upm  = head.unitsPerEm

    old_typo_asc  = os2.sTypoAscender
    old_typo_desc = os2.sTypoDescender

    new_win_asc  = max(head.yMax, int(upm * WIN_ASCENT_RATIO))
    new_win_desc = max(abs(head.yMin), int(upm * WIN_DESCENT_RATIO))

    os2.usWinAscent  = new_win_asc
    os2.usWinDescent = new_win_desc
    print(f"  Win → Ascent: {new_win_asc} ({new_win_asc/upm:.2f}x), Descent: {new_win_desc} ({new_win_desc/upm:.2f}x)")

    os2.sTypoAscender  = int(old_typo_asc * 1.2)
    os2.sTypoDescender = old_typo_desc
    os2.sTypoLineGap   = 0
    hhea.ascent  = os2.sTypoAscender
    hhea.descent = old_typo_desc
    hhea.lineGap = 0
    print(f"  Typo Ascender → {os2.sTypoAscender} (x1.2)")

    os2.fsSelection |= 0x0080
    print(f"  USE_TYPO_METRICS enabled")

    new_name = "VN_" + basename[3:]
    out_path = os.path.join(family_dir, new_name)
    f.save(out_path)

    os.remove(src)
    print(f"  Removed: {basename}")
    print(f"  Saved: {out_path}\n")

print(f"Done! {len(files)} fonts processed.")
print(f"Output: {OUTPUT_DIR}")