#!/bin/sh
# Build mod/deckglyphs.dll (32-bit, no CRT) with clang + lld-link. Usage: tools/build_dll.sh
set -e
cd "$(dirname "$0")/.."
B=build; mkdir -p $B
printf 'LIBRARY kernel32.dll\nEXPORTS\nVirtualProtect@16\nFlushInstructionCache@12\nGetCurrentProcess@0\nGetModuleFileNameA@12\n' > $B/kernel32.def
llvm-dlltool -m i386 -k -d $B/kernel32.def -l $B/kernel32.lib
clang --target=i686-pc-windows-msvc -O2 -Wall -Wextra -ffreestanding -fno-stack-protector -mno-sse \
    -c src/deckglyphs.c -o $B/deckglyphs.obj
lld-link /dll /nodefaultlib /entry:DllMain@12 /machine:x86 /subsystem:windows \
    /out:mod/deckglyphs.dll /implib:$B/deckglyphs.lib $B/deckglyphs.obj $B/kernel32.lib
ls -l mod/deckglyphs.dll
