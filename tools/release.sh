#!/bin/sh
# Build everything from source and pack the Junction VIII mod.
# Usage: tools/release.sh <version>   ->  dist/FF8DeckGlyphs.iroj
# Steps: DLL (clang + lld-link), host tests, glyph textures (own art, no game files), copy of mod/
# with <Version> and <ReleaseDate> set, .iroj. Needs clang, lld, llvm (llvm-dlltool), python3 + Pillow,
# DejaVu Sans Bold.
set -e
cd "$(dirname "$0")/.."
V=${1:?usage: tools/release.sh <version>}
tools/build_dll.sh "$V"
tools/test.sh
python3 tools/make_glyphs.py mod/mods/Textures/data/eng/menu/hires
P=build/pkg
rm -rf $P && mkdir -p $P dist
cp -r mod/. $P/
sed -i "s|<Version>[^<]*</Version>|<Version>$V</Version>|; s|<ReleaseDate>[^<]*</ReleaseDate>|<ReleaseDate>$(date -u +%Y-%m-%d)</ReleaseDate>|" $P/mod.xml
grep -q "<Version>$V</Version>" $P/mod.xml
python3 tools/pack_iro.py $P dist/FF8DeckGlyphs.iroj
