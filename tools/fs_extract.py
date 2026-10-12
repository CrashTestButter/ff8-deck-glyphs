#!/usr/bin/env python3
"""Extract files from an FF8 .fs/.fi/.fl archive (Steam 2013 layout).

fi : per file 3 x uint32 LE: uncompressed size, offset in .fs, compression (0 none, 1 LZSS)
fl : one path per line, same order as .fi
LZSS (FF7/FF8): uint32 compressed length, then groups of a flag byte (LSB first, 1 = literal byte,
0 = 2-byte reference: offset = b0 | (b1 & 0xF0) << 4, length = (b1 & 0x0F) + 3, 4096-byte window
whose write position starts at 0xFEE).
Usage: fs_extract.py <archive without extension> <out dir> [substring filter ...]
"""
import os, struct, sys


def lzss(src, size):
    out = bytearray()
    i, n = 4, 4 + struct.unpack_from('<I', src, 0)[0]
    while i < n and len(out) < size:
        flags = src[i]; i += 1
        for bit in range(8):
            if i >= n or len(out) >= size:
                break
            if flags >> bit & 1:
                out.append(src[i]); i += 1
            else:
                b0, b1 = src[i], src[i + 1]; i += 2
                off = b0 | (b1 & 0xF0) << 4
                length = (b1 & 0x0F) + 3
                start = len(out) - ((len(out) - 18 - off) & 0xFFF)
                for k in range(length):
                    p = start + k
                    out.append(out[p] if p >= 0 else 0)
    return bytes(out[:size])


def entries(base):
    fi = open(base + '.fi', 'rb').read()
    names = [l.strip() for l in open(base + '.fl', encoding='latin-1').read().splitlines() if l.strip()]
    assert len(fi) // 12 == len(names), 'fi/fl count mismatch'
    for k, name in enumerate(names):
        yield (name,) + struct.unpack_from('<III', fi, k * 12)


def extract(base, out, filters):
    fs = open(base + '.fs', 'rb').read()
    for name, size, off, comp in entries(base):
        if filters and not any(f.lower() in name.lower() for f in filters):
            continue
        if comp == 0:
            data = fs[off:off + size]
        elif comp == 1:
            data = lzss(fs[off:], size)
        else:
            sys.exit(f'{name}: compression {comp} not supported')
        assert len(data) == size, f'{name}: got {len(data)} of {size} bytes'
        rel = name.split('\\', 2)[-1].replace('\\', os.sep)  # drop "C:\ff8\"
        path = os.path.join(out, rel)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        open(path, 'wb').write(data)
        print(f'{rel}  {size} bytes  comp={comp}')


if __name__ == '__main__':
    extract(sys.argv[1], sys.argv[2], sys.argv[3:])
