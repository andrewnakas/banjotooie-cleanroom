"""Banjo-Tooie asset filesystem (ROM 0x5180 .. 0x1A14580): parse and rebuild.

Layout (found by probing; the decomp keeps the whole region as one `assets` bin):
  u32 slot count (0x3667), u32 0xFFFFFFFF, count x u32 entry, then data (base = table end).
  entry = (offset / 4) << 8 | type.  Size of slot i = offset[i+1] - offset[i]; the last slots are terminators.
  Stored form of every type except 4 (empty), 6, 7 (raw) and 0x1A (encrypted text):
  u16 BE = ceil(decompressed size / 16), then raw deflate (Rare's gzip 1.2.4), padded with 0xAA to 8 bytes
  (rebuilding every retail asset this way reproduces the retail region byte for byte).
"""
import struct
import zlib

TABLE = 0x5180
END = 0x1A14580
RAW_TYPES = (4, 6, 7, 0x1A)
ROM_DEFAULT = "D:/n64work/banjotooie/rom/Banjo-Tooie (USA).z64"


def unzip(b):
    """-> decompressed bytes (length is a multiple of 16 only by the header's rounding: the true
    length is what inflate returns)."""
    return zlib.decompressobj(-15).decompress(bytes(b[2:]))


_RZ = None


def _rarezip():
    global _RZ
    if _RZ is None:
        import ctypes
        import os
        _RZ = ctypes.CDLL(os.path.join(os.path.dirname(__file__), "..", "..", "tools", "rarezip", "rarezip.dll"))
        _RZ.bk_zip.restype = ctypes.c_size_t
        _RZ.bk_zip.argtypes = [ctypes.c_char_p, ctypes.c_size_t, ctypes.c_char_p, ctypes.c_size_t]
    return _RZ


def deflate_rare(b):
    """Raw deflate stream from Rare's compressor (bk_zip writes 0x1172 + u32 size first)."""
    import ctypes
    b = bytes(b)
    cap = len(b) + len(b) // 8 + 0x1000
    out = ctypes.create_string_buffer(cap)
    n = _rarezip().bk_zip(b, len(b), out, cap)
    return out.raw[6:n]


def zip_(b):
    z = struct.pack(">H", (len(b) + 15) // 16) + deflate_rare(b)
    return z + bytes([0xAA]) * (-len(z) % 8)


class Entry:
    __slots__ = ("uid", "type", "raw", "_data")

    def __init__(self, uid, type_, raw):
        self.uid, self.type, self.raw, self._data = uid, type_, raw, None

    @property
    def data(self):
        """Decompressed content (raw for uncompressed types, None for empty slots)."""
        if self._data is None and self.raw:
            self._data = bytes(self.raw) if self.type in RAW_TYPES else unzip(self.raw)
        return self._data

    def set(self, data):
        """Replace the content; recompresses."""
        self._data = bytes(data)
        self.raw = self._data if self.type in RAW_TYPES else zip_(self._data)


def parse(rom):
    n = struct.unpack_from(">I", rom, TABLE)[0]
    ents = struct.unpack_from(">%dI" % n, rom, TABLE + 8)
    base = TABLE + 8 + 4 * n
    out = []
    for i in range(n):
        o = (ents[i] >> 8) * 4
        e = (ents[i + 1] >> 8) * 4 if i + 1 < n else o
        out.append(Entry(i, ents[i] & 0xFF, bytes(rom[base + o:base + e])))
    return out


def build(entries):
    """-> bytes of the whole region (table + data), padded to END - TABLE. Raises if too big."""
    n = len(entries)
    tab = bytearray(struct.pack(">II", n, 0xFFFFFFFF))
    data = bytearray()
    for e in entries:
        assert len(data) % 4 == 0
        tab += struct.pack(">I", (len(data) // 4) << 8 | e.type)
        data += e.raw
        data += bytes(-len(data) % 4)
    blob = bytes(tab) + bytes(data)
    room = END - TABLE
    if len(blob) > room:
        raise ValueError("assets too big: %#x > %#x" % (len(blob), room))
    return blob + bytes(room - len(blob)), len(blob)


def load(path=ROM_DEFAULT):
    with open(path, "rb") as f:
        rom = f.read()
    return rom, parse(rom)


if __name__ == "__main__":
    import collections
    import sys
    rom, ents = load(*sys.argv[1:2])
    c = collections.Counter()
    for e in ents:
        d = e.data
        c[(hex(e.type), d[:4].hex() if d and e.type != 0x13 else "")] += 1
    for k, v in sorted(c.items(), key=lambda kv: -kv[1])[:40]:
        print(k, v)
    blob, used = build(ents)
    print("rebuild identical:", blob == rom[TABLE:END], hex(used))
