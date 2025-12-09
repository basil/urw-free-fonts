from collections import defaultdict
from pathlib import Path
import argparse
import contextlib
import shutil
import sys
import zipfile

try:
    import fontforge
except ImportError:
    print(
        "ERROR: This script must be run with FontForge's Python interpreter.",
        file=sys.stderr,
    )
    print(
        "Run it like this: fontforge -script convert.py /path/to/fonts",
        file=sys.stderr,
    )
    sys.exit(1)


def package_family(family_name, fonts, out_dir):
    exts = (".otf", ".ttf", ".woff2")
    zip_path = out_dir / f"{family_name}.zip"
    print("Creating archive:", zip_path)
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for font in sorted(fonts):
            for ext in exts:
                p = out_dir / (font + ext)
                if p.exists():
                    zf.write(p, arcname=p.name)


def fix_unicode_from_glyph_names(font):
    """
    Do what FontForge's 'Set Unicode Value from Name' does:

    For each glyph, compute the Unicode value implied by its glyph name using
    FontForge's internal name tables. If that value is known and differs from
    the current encoding (or the glyph is unencoded), set glyph.unicode to that
    value.
    """
    changes = []  # list of (glyph, old_unicode, new_unicode)

    for g in font.glyphs():
        name = g.glyphname
        if not name:
            continue

        # What Unicode value should this name imply?
        expected = fontforge.unicodeFromName(name)
        if expected is None or expected < 0:
            # Skip if name not in FontForge's name lists
            continue

        current = g.unicode
        if current == expected:
            # Already consistent
            continue

        changes.append((g, current, expected))

    if not changes or len(changes) > 20:
        return False

    print(
        f"Setting Unicode values from glyph names in '{font.fontname}': "
        f"{len(changes)} glyphs will be updated"
    )
    for g, old_u, new_u in changes:
        print(f"  {g.glyphname}: U+{old_u:04X} -> U+{new_u:04X}")
        g.unicode = new_u

    return True


def process_family(stem, files, out_dir, families):
    source = None
    for ext in (".otf", ".ttf", ".pfb", ".pfa"):
        if ext in files:
            source = files[ext]
            break

    if source is None:
        print(
            f"No usable source font found for '{stem}'.",
            file=sys.stderr,
        )
        sys.exit(1)

    with contextlib.closing(fontforge.open(str(source))) as f:
        # Set Unicode encoding (map glyphs to Unicode where possible)
        f.encoding = "UnicodeFull"

        # Fix any mis-encoded glyphs based on their names.
        had_unicode_fixes = fix_unicode_from_glyph_names(f)

        font = f.fontname
        family_name = font.split("-", 1)[0]
        have = set(files.keys())
        want = {".otf", ".ttf", ".woff2"}

        if had_unicode_fixes:
            # The font contained glyphs whose Unicode value did not match the
            # value implied by their names. We have corrected those in memory,
            # so now we must regenerate all target formats from this fixed font.
            print(
                f"Glyph/Unicode mismatches detected in '{font}'. "
                "Regenerating all output formats from the corrected font."
            )
            for ext in want:
                dest = out_dir / (font + ext)
                print(f"Generating: {dest} (from corrected {source})")
                f.generate(str(dest))
        else:
            # Copy any existing inputs.
            for ext in want:
                if ext in have:
                    src = files[ext]
                    dest = out_dir / (font + ext)
                    if dest.resolve() != src.resolve():
                        print("Copying", src, "to", dest)
                        shutil.copy2(src, dest)

            # Generate any missing formats using FontForge.
            for ext in want - have:
                dest = out_dir / (font + ext)
                print(f"Generating: {dest} (from {source})")
                f.generate(str(dest))

    # Record that this font belongs to this family.
    families[family_name].add(font)


def main():
    ap = argparse.ArgumentParser(
        description="Convert fonts to OTF/TTF/WOFF2 using FontForge"
    )
    ap.add_argument(
        "indir", nargs="?", default=".", help="Input directory (default: current dir)"
    )
    ap.add_argument(
        "-o", "--outdir", default=None, help="Output directory (default: same as input)"
    )
    args = ap.parse_args()

    indir = Path(args.indir)
    outdir = Path(args.outdir) if args.outdir else indir

    if not indir.is_dir():
        print("Input directory does not exist:", str(indir), file=sys.stderr)
        sys.exit(1)

    outdir.mkdir(parents=True, exist_ok=True)

    stems = defaultdict(dict)  # stem -> {ext: Path}

    for ext in (".otf", ".ttf", ".pfa", ".pfb"):
        for f in indir.glob(f"*{ext}"):
            if f.is_file():
                stems[f.stem][ext] = f

    if not stems:
        print(
            "No .otf, .pfa, .pfb, or .ttf files found in",
            str(indir),
            file=sys.stderr,
        )
        sys.exit(1)

    families = defaultdict(set)  # family -> styles

    # Process each familhy once.
    for stem, files in sorted(stems.items()):
        process_family(stem, files, outdir, families)

    # After all fonts are converted, package by family.
    for family, fonts in sorted(families.items()):
        package_family(family, fonts, outdir)

    print("Done.")


if __name__ == "__main__":
    main()
