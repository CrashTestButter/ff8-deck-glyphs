#!/bin/sh
# Host test of the diamond rearranging logic in src/deckglyphs.c.
set -e
cd "$(dirname "$0")/.."
mkdir -p build
cc -O1 -Wall -o build/test_diamond tests/test_diamond.c && build/test_diamond
