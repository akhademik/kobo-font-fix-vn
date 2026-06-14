from fontTools.ttLib import TTFont
import glob, os, sys, re

WIN_ASCENT_RATIO  = 1.45
WIN_DESCENT_RATIO = 0.50

INPUT_DIR  = sys.argv[1] if len(sys.argv) > 1 else "fonts-src"
OUTPUT_DIR = sys.argv[2] if len(sys.argv) > 2 else "fonts-out"

# Tìm đệ quy tất cả KF_*.ttf hoặc NV_*.ttf trong INPUT_DIR
files = sorted(glob.glob(os.path.join(INPUT_DIR, "**", "KF_*.ttf"), recursive=True) + 
               glob.glob(os.path.join(INPUT_DIR, "**", "NV_*.ttf"), recursive=True))

if not files:
    print(f"Không tìm thấy file font có prefix KF_ hoặc NV_ trong: {INPUT_DIR}")
    sys.exit(1)

print(f"Tìm thấy {len(files)} file, bắt đầu xử lý metadata và thông số tiếng Việt...\n")

def get_family_name(filename):
    """
    Lấy tên family từ tên file và xóa bỏ prefix 2 chữ cái (KF_, NV_, VN_).
    """
    name = re.sub(r"^[A-Z]{2}_", "", filename)
    name = re.sub(r"\.ttf$", "", name)
    name = re.sub(r"[-_](Bold|Italic|BoldItalic|Regular|Light|Medium|SemiBold|ExtraBold|Black|Testing).*$", "", name, flags=re.IGNORECASE)
    name = name.replace("_", " ").strip()
    return name

def get_style_name(filename):
    """
    Lấy style từ tên file (Bold, Italic, Regular, v.v.)
    """
    name = re.sub(r"^[A-Z]{2}_", "", filename)
    name = re.sub(r"\.ttf$", "", name)
    match = re.search(r"[-_](Bold|Italic|BoldItalic|Regular|Light|Medium|SemiBold|ExtraBold|Black|Testing)", name, flags=re.IGNORECASE)
    if match:
        return match.group(1)
    return "Regular"

def update_font_metadata(font, family, style):
    """
    Cập nhật bảng name của font để đồng bộ với prefix VN.
    """
    if "name" not in font:
        return

    name_table = font["name"]
    prefix = "VN"
    
    # Chuẩn hóa style display (VD: BoldItalic -> Bold Italic)
    style_display = style
    if style.lower() == "bolditalic": style_display = "Bold Italic"
    
    full_name = f"{prefix} {family}"
    if style_display != "Regular":
        full_name += f" {style_display}"
        
    ps_name = f"{prefix}_{family.replace(' ', '-')}"
    if style != "Regular":
        ps_name += f"-{style}"

    # Các ID cần cập nhật: 1 (Family), 2 (Subfamily), 4 (Full Name), 6 (PS Name), 16 (Typo Family), 17 (Typo Subfamily)
    updates = {
        1: f"{prefix} {family}",
        2: style_display,
        4: full_name,
        6: ps_name,
        16: f"{prefix} {family}",
        17: style_display
    }
    
    for record in name_table.names:
        if record.nameID in updates:
            new_val = updates[record.nameID]
            try:
                if record.platformID == 3: # Windows/Unicode
                    record.string = new_val.encode("utf-16-be")
                elif record.platformID == 1: # Macintosh
                    record.string = new_val.encode("mac-roman")
            except:
                pass

for src in files:
    basename = os.path.basename(src)
    family   = get_family_name(basename)
    style    = get_style_name(basename)

    family_dir = os.path.join(OUTPUT_DIR, family)
    os.makedirs(family_dir, exist_ok=True)

    print(f"Processing: {basename}")
    print(f"  Family: {family}, Style: {style} → {family_dir}")

    f    = TTFont(src)
    
    # 1. Cập nhật metadata (Name Table) - QUAN TRỌNG để hiển thị đúng trên Kobo
    update_font_metadata(f, family, style)
    
    # 2. Cập nhật thông số WinAscent/Descent và Typo cho tiếng Việt
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
    
    os2.sTypoAscender  = int(old_typo_asc * 1.2)
    os2.sTypoDescender = old_typo_desc
    os2.sTypoLineGap   = 0
    hhea.ascent  = os2.sTypoAscender
    hhea.descent = old_typo_desc
    hhea.lineGap = 0

    os2.fsSelection |= 0x0080 # USE_TYPO_METRICS

    # 3. Lưu file với tên mới VN_
    new_filename = "VN_" + re.sub(r"^[A-Z]{2}_", "", basename)
    out_path = os.path.join(family_dir, new_filename)
    f.save(out_path)

    os.remove(src)
    print(f"  Updated metadata and saved as: {new_filename}\n")

print(f"Xử lý xong! {len(files)} font đã được cập nhật metadata VN.")
