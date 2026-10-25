"""Puts an icon into a Windows .exe: every image of an .ico file, exactly as it is in the file.

    set_icon.py <in.exe> <icon.ico | icon.png> <out.exe>

Icons below 256 px are stored as 32-bit bitmaps (same pixels, the format every Windows API reads);
the 256 px icon stays PNG. The exe's resource section (.rsrc) is rebuilt: all existing resources (version info, manifest,
strings...) are kept, and the icon images and icon group are replaced with the ones from the .ico,
at every size it holds (for R64texHD: 16, 24, 32, 48, 64, 128 and 256 px). The .reloc section that
follows .rsrc is moved to make room; its contents don't depend on where it sits, only the
base-relocation directory entry points at it. The result is laid out like a resource editor writes it.
A .png is first turned into a multi-size .ico.
"""
import io, struct, sys
import pefile
from PIL import Image

RT_ICON, RT_GROUP_ICON = 3, 14
ICO_SIZES = [16, 24, 32, 48, 64, 128, 256]


def align(n, a):
    return (n + a - 1) // a * a


def dib(img):
    """32-bit BGRA bitmap with an empty AND mask: the classic in-exe format for icons below 256 px."""
    w, h = img.size
    px = img.convert('RGBA').tobytes('raw', 'BGRA')
    rows = [px[y * w * 4:(y + 1) * w * 4] for y in range(h)][::-1]
    mask_row = ((w + 31) // 32) * 4
    header = struct.pack('<IiiHHIIiiII', 40, w, h * 2, 1, 32, 0, w * h * 4 + mask_row * h, 0, 0, 0, 0)
    return header + b''.join(rows) + b'\0' * (mask_row * h)


def read_ico(path):
    """[(width, height, colours, planes, bits, image bytes)] from an .ico (a .png is converted first)."""
    data = open(path, 'rb').read()
    if data[:4] == b'\x89PNG':
        buf = io.BytesIO()
        Image.open(io.BytesIO(data)).convert('RGBA').save(buf, 'ICO', sizes=[(s, s) for s in ICO_SIZES])
        data = buf.getvalue()
    reserved, kind, count = struct.unpack_from('<HHH', data, 0)
    if reserved != 0 or kind != 1 or not count:
        raise SystemExit(f'{path} is not an .ico file')
    images = []
    for i in range(count):
        w, h, cc, _, planes, bits, size, off = struct.unpack_from('<BBBBHHII', data, 6 + 16 * i)
        blob = data[off:off + size]
        if w and blob[:4] == b'\x89PNG':
            # PNG below 256 px -> the same pixels as a 32-bit bitmap, which every Windows API reads.
            blob, planes, bits, cc = dib(Image.open(io.BytesIO(blob))), 1, 32, 0
        images.append((w, h, cc, planes or 1, bits or 32, blob))
    return images


def read_tree(pe):
    """{type: {name: {lang: (bytes, codepage)}}} for every resource in the exe."""
    tree = {}
    key = lambda e: str(e.name) if e.name is not None else e.id
    for t in pe.DIRECTORY_ENTRY_RESOURCE.entries:
        for n in t.directory.entries:
            for l in n.directory.entries:
                s = l.data.struct
                tree.setdefault(key(t), {}).setdefault(key(n), {})[l.id] = (pe.get_data(s.OffsetToData, s.Size), s.CodePage)
    return tree


def build_rsrc(tree, base_rva):
    """Serialises a resource tree into .rsrc bytes for a section at base_rva."""
    order = lambda d: sorted(d, key=lambda k: (isinstance(k, int), k.upper() if isinstance(k, str) else k))
    # Pass 1: lay out directories (breadth first), name strings, data entries, data.
    dirs = []                                     # (level, dict) in output order

    def add_dirs(d, level):
        idx = len(dirs); dirs.append((level, d))
        return idx
    root = add_dirs(tree, 0)
    queue = [(root, tree, 0)]
    children = {}                                 # dir index -> [(key, child index or leaf)]
    while queue:
        nxt = []
        for idx, d, level in queue:
            items = []
            for k in order(d):
                if level < 2:
                    ci = add_dirs(d[k], level + 1); items.append((k, ci)); nxt.append((ci, d[k], level + 1))
                else:
                    items.append((k, ('leaf', d[k])))
            children[idx] = items
        queue = nxt
    dir_off, pos = {}, 0
    for i, (level, d) in enumerate(dirs):
        dir_off[i] = pos; pos += 16 + 8 * len(d)
    names = {}
    for i in children:
        for k, _ in children[i]:
            if isinstance(k, str) and k not in names:
                names[k] = pos; pos += 2 + 2 * len(k)
    pos = align(pos, 4)
    leaves = [(i, k, v[1]) for i in children for k, v in children[i] if isinstance(v, tuple)]
    entry_off = {}
    for i, k, _ in leaves:
        entry_off[(i, k)] = pos; pos += 16
    data_off = {}
    for i, k, (blob, cp) in leaves:
        pos = align(pos, 8); data_off[(i, k)] = pos; pos += len(blob)
    out = bytearray(pos)
    # Pass 2: write.
    for i, (level, d) in enumerate(dirs):
        items = children[i]
        n_named = sum(isinstance(k, str) for k, _ in items)
        o = dir_off[i]
        struct.pack_into('<IIHHHH', out, o, 0, 0, 0, 0, n_named, len(items) - n_named)
        for j, (k, v) in enumerate(items):
            name_field = (0x80000000 | names[k]) if isinstance(k, str) else k
            target = entry_off[(i, k)] if isinstance(v, tuple) else (0x80000000 | dir_off[v])
            struct.pack_into('<II', out, o + 16 + 8 * j, name_field, target)
    for k, o in names.items():
        struct.pack_into('<H', out, o, len(k)); out[o + 2:o + 2 + 2 * len(k)] = k.encode('utf-16-le')
    for i, k, (blob, cp) in leaves:
        struct.pack_into('<IIII', out, entry_off[(i, k)], base_rva + data_off[(i, k)], len(blob), cp, 0)
        out[data_off[(i, k)]:data_off[(i, k)] + len(blob)] = blob
    return bytes(out)


def main(exe, icon, out):
    images = read_ico(icon)
    pe = pefile.PE(exe, fast_load=True)
    pe.parse_data_directories(directories=[pefile.DIRECTORY_ENTRY['IMAGE_DIRECTORY_ENTRY_RESOURCE']])
    opt = pe.OPTIONAL_HEADER
    if opt.DATA_DIRECTORY[4].Size:
        raise SystemExit('The exe is code-signed; remove the signature before changing its icon.')
    ri = next(i for i, s in enumerate(pe.sections) if s.Name.rstrip(b'\0') == b'.rsrc')
    rsrc, rest = pe.sections[ri], pe.sections[ri + 1:]
    if opt.DATA_DIRECTORY[2].VirtualAddress != rsrc.VirtualAddress:
        raise SystemExit('Resource directory is not at the start of .rsrc.')
    if any(s.Name.rstrip(b'\0') != b'.reloc' for s in rest):
        raise SystemExit('Only .reloc may follow .rsrc for the resource section to be rebuilt.')

    tree = read_tree(pe)
    groups = tree.get(RT_GROUP_ICON, {})
    group_name = min(groups, key=lambda k: (isinstance(k, str), k)) if groups else 1
    lang = next(iter(groups[group_name])) if groups else 1033
    tree[RT_ICON] = {}
    grp = bytearray(struct.pack('<HHH', 0, 1, len(images)))
    for n, (w, h, cc, planes, bits, blob) in enumerate(images, 1):
        tree[RT_ICON][n] = {lang: (blob, 0)}
        grp += struct.pack('<BBBBHHIH', w, h, cc, 0, planes, bits, len(blob), n)
        kind = 'PNG' if blob[:4] == b'\x89PNG' else 'DIB'
        print(f'  icon {w or 256}x{h or 256} {bits}-bit {kind} {len(blob)} bytes')
    groups = {group_name: {lang: (bytes(grp), 0)}}
    tree[RT_GROUP_ICON] = groups

    blob = build_rsrc(tree, rsrc.VirtualAddress)
    fa, sa = opt.FileAlignment, opt.SectionAlignment
    data = pe.__data__
    new_raw = align(len(blob), fa)
    old_raw = rsrc.SizeOfRawData
    after = bytes(data[rsrc.PointerToRawData + old_raw:])          # .reloc and anything after it
    new_file = bytes(data[:rsrc.PointerToRawData]) + blob + b'\0' * (new_raw - len(blob)) + after
    new_end = align(rsrc.VirtualAddress + len(blob), sa)
    va_shift = max(0, new_end - rest[0].VirtualAddress) if rest else 0
    raw_shift = new_raw - old_raw

    pe2 = pefile.PE(data=new_file, fast_load=True)
    r2 = pe2.sections[ri]
    r2.Misc_VirtualSize, r2.SizeOfRawData = len(blob), new_raw
    o2 = pe2.OPTIONAL_HEADER
    o2.DATA_DIRECTORY[2].Size = len(blob)
    for s in pe2.sections[ri + 1:]:
        if o2.DATA_DIRECTORY[5].VirtualAddress == s.VirtualAddress:
            o2.DATA_DIRECTORY[5].VirtualAddress += va_shift
        s.VirtualAddress += va_shift
        s.PointerToRawData += raw_shift
    last = pe2.sections[-1]
    o2.SizeOfImage = align(last.VirtualAddress + max(last.Misc_VirtualSize, last.SizeOfRawData), sa)
    o2.SizeOfInitializedData += raw_shift
    o2.CheckSum = 0
    pe3 = pefile.PE(data=bytes(pe2.write()), fast_load=True)
    pe3.OPTIONAL_HEADER.CheckSum = pe3.generate_checksum()
    pe3.write(out)
    print(f'icon set: {out} ({len(images)} images; .rsrc {rsrc.Misc_VirtualSize} -> {len(blob)} bytes, .reloc moved by 0x{va_shift:x})')


if __name__ == '__main__':
    main(*sys.argv[1:4])
