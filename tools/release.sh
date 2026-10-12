#!/bin/sh
# Usage: tools/release.sh <version>   (writes dist/FF8DeckGlyphs.iroj)
set -e
cd "$(dirname "$0")/.."
V=${1:?usage: tools/release.sh <version>}
tools/build_dll.sh
tools/test.sh
python3 tools/make_glyphs.py mod/mods/Textures/data/eng/menu/hires
P=build/pkg
rm -rf $P && mkdir -p $P dist
cp -r mod/. $P/
sed -i "s|<Version>[^<]*</Version>|<Version>$V</Version>|; s|<ReleaseDate>[^<]*</ReleaseDate>|<ReleaseDate>$(date -u +%Y-%m-%d)</ReleaseDate>|" $P/mod.xml
grep -q "<Version>$V</Version>" $P/mod.xml
python3 tools/pack_iro.py $P dist/FF8DeckGlyphs.iroj
