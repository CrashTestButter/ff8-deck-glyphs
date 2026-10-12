#!/bin/sh
set -e
cd "$(dirname "$0")/.."
mkdir -p build
cc -O1 -Wall -o build/test_diamond tests/test_diamond.c && build/test_diamond
