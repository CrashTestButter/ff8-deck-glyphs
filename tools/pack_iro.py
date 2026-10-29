#!/usr/bin/env python3
"""Pack a folder into a Junction VIII .iroj archive (LZMA per file).

Writes the same layout as J8's IrosArc.Create with ArchiveFlags.None
(AppWrapper/IrosArc.cs, Junction-VIII, MS-PL):
  header : int32 'IROS' (0x534F5249), int32 version 0x10002, int32 flags 0, int32 directory offset 16
  dir    : int32 count, then per file: u16 entry_len, u16 name_bytes, UTF-16LE name ('\\' separators),
           int32 file flags (0 = stored, 2 = LZMA), int64 offset, int32 length
  data   : stored bytes, or for LZMA: int32 decompressed size, int32 props size (5), the LZMA props,
           then the raw LZMA stream. Like J8, a file stays stored if LZMA would not save 20 %.
All little endian. Usage: pack_iro.py <folder> <out.iroj>  (then it re-reads and verifies the archive)
"""
import lzma, os, struct, sys

SIG, VERSION = 0x534F5249, 0x10002
STORED, LZMA = 0, 2


def compress(data):
    alone = lzma.compress(data, format=lzma.FORMAT_ALONE)  # props (5), size (8), stream
    props, stream = alone[:5], alone[13:]
    if len(stream) + len(props) + 8 > len(data) * 10 // 8:
        return STORED, data
    return LZMA, struct.pack('<ii', len(data), len(props)) + props + stream


def decompress(blob):
    size, nprops = struct.unpack_from('<ii', blob, 0)
    props, stream = blob[8:8 + nprops], blob[8 + nprops:]
    return lzma.decompress(props + struct.pack('<q', -1) + stream, format=lzma.FORMAT_ALONE)[:size]


def pack(src, out):
    names = sorted(os.path.relpath(os.path.join(r, f), src).replace('/', '\\')
                   for r, _, fs in os.walk(src) for f in fs)
    if not names:
        sys.exit('nothing to pack')
    plain = [open(os.path.join(src, n.replace('\\', os.sep)), 'rb').read() for n in names]
    packed = [compress(b) for b in plain]
    enc = [n.encode('utf-16-le') for n in names]
    dsize = sum(len(e) + 4 + 16 for e in enc)
    pos = 16 + 4 + dsize
    head = struct.pack('<iiii', SIG, VERSION, 0, 16) + struct.pack('<i', len(names))
    dirent, data = b'', b''
    for e, (flags, b) in zip(enc, packed):
        dirent += struct.pack('<HH', len(e) + 4 + 16, len(e)) + e + struct.pack('<iqi', flags, pos, len(b))
        pos += len(b)
        data += b
    with open(out, 'wb') as f:
        f.write(head + dirent + data)
    return dict(zip(names, plain))


def read(path):
    d = open(path, 'rb').read()
    sig, ver, flags, dirofs = struct.unpack_from('<iiii', d, 0)
    assert sig == SIG and 0x10000 <= ver <= 0x10002, 'bad header'
    n, = struct.unpack_from('<i', d, dirofs)
    p, files = dirofs + 4, {}
    for _ in range(n):
        ln, fl = struct.unpack_from('<HH', d, p)
        name = d[p + 4:p + 4 + fl].decode('utf-16-le')
        ff, off, length = struct.unpack_from('<iqi', d, p + 4 + fl)
        assert ff in (STORED, LZMA) and off + length <= len(d)
        blob = d[off:off + length]
        files[name] = decompress(blob) if ff == LZMA else blob
        p += ln
    return files


if __name__ == '__main__':
    src, out = sys.argv[1], sys.argv[2]
    want = pack(src, out)
    got = read(out)
    assert got == want, 'verify failed'
    print(f'{out}: {len(got)} files, {os.path.getsize(out)} bytes, verified: ' + ', '.join(sorted(got)))
