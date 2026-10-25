"""Replaces the icon images inside a Windows .exe (16, 32, 48 as 32-bit DIBs, 256 as a PNG).

Images that fit their existing resource slot are written in place. One that is larger (usually the
detailed full-colour 256x256 PNG) is appended to the end of the .rsrc section, which is enlarged for
it; the .reloc section that follows .rsrc is moved up to make room (its contents don't depend on
where it sits, only the base-relocation directory entry points at it). The result is a normal exe
whose resources all live in .rsrc, exactly as a resource editor would write it.
"""
import io, struct, sys
import pefile
from PIL import Image


def align(n, a):
    return (n + a - 1) // a * a


def dib(img):
    w, h = img.size
    px = img.convert('RGBA').tobytes('raw', 'BGRA')
    rows = [px[y * w * 4:(y + 1) * w * 4] for y in range(h)][::-1]
    mask_row = ((w + 31) // 32) * 4
    header = struct.pack('<IiiHHIIiiII', 40, w, h * 2, 1, 32, 0, w * h * 4 + mask_row * h, 0, 0, 0, 0)
    return header + b''.join(rows) + b'\0' * (mask_row * h)


def png_bytes(img):
    buf = io.BytesIO()
    img.save(buf, 'PNG', optimize=True)
    return buf.getvalue()


def section(pe, name):
    for i, s in enumerate(pe.sections):
        if s.Name.rstrip(b'\0') == name: return i, s
    raise SystemExit(f'no {name.decode()} section')


def main(exe, icon_png, out):
    src = Image.open(icon_png).convert('RGBA')
    pe = pefile.PE(exe, fast_load=True)
    pe.parse_data_directories(directories=[pefile.DIRECTORY_ENTRY['IMAGE_DIRECTORY_ENTRY_RESOURCE']])
    opt = pe.OPTIONAL_HEADER
    if opt.DATA_DIRECTORY[4].Size:
        raise SystemExit('The exe is code-signed; remove the signature before changing its icon.')

    ri, rsrc = section(pe, b'.rsrc')
    rest = pe.sections[ri + 1:]
    if any(s.Name.rstrip(b'\0') != b'.reloc' for s in rest):
        raise SystemExit('Only .reloc may follow .rsrc for the resource section to be enlarged.')
    grow_at = align(rsrc.Misc_VirtualSize, 8)          # offset inside .rsrc where extra data goes
    extra = bytearray()

    icons, groups = {}, []
    for t in pe.DIRECTORY_ENTRY_RESOURCE.entries:
        for e in t.directory.entries:
            for l in e.directory.entries:
                if t.id == 3: icons[e.id] = l.data
                if t.id == 14: groups.append(l.data)

    for g in groups:
        raw = bytearray(pe.get_data(g.struct.OffsetToData, g.struct.Size))
        n = struct.unpack_from('<H', raw, 4)[0]
        for i in range(n):
            o = 6 + i * 14
            w, h, cc, r, planes, bits, size, iid = struct.unpack_from('<BBBBHHIH', raw, o)
            w, h = w or 256, h or 256
            slot = icons[iid]
            img = src.resize((w, h), Image.LANCZOS)
            data = png_bytes(img) if w >= 256 else dib(img)
            if len(data) <= slot.struct.Size:
                pe.set_bytes_at_rva(slot.struct.OffsetToData, data + b'\0' * (slot.struct.Size - len(data)))
            else:
                while len(extra) % 8: extra.append(0)
                slot.struct.OffsetToData = rsrc.VirtualAddress + grow_at + len(extra)
                extra += data
                print(f'  {w}x{h} icon ({len(data)} bytes) added to .rsrc (full colour)')
            slot.struct.Size = len(data)
            struct.pack_into('<BBBBHHIH', raw, o, w % 256, h % 256, 0, 0, 1, 32, len(data), iid)
        pe.set_bytes_at_rva(g.struct.OffsetToData, bytes(raw))

    data = bytearray(pe.write())
    if not extra:
        open(out, 'wb').write(data)
        print('icon set:', out)
        return

    fa, sa = opt.FileAlignment, opt.SectionAlignment
    old_raw = rsrc.SizeOfRawData
    new_vsize = grow_at + len(extra)
    new_raw = align(new_vsize, fa)
    body = bytes(data[rsrc.PointerToRawData:rsrc.PointerToRawData + min(grow_at, old_raw)])
    body += b'\0' * (grow_at - len(body)) + bytes(extra)
    body += b'\0' * (new_raw - len(body))
    after = bytes(data[rsrc.PointerToRawData + old_raw:])          # .reloc (and anything after it)
    new_file = bytearray(data[:rsrc.PointerToRawData]) + body + after

    va_shift = max(0, align(rsrc.VirtualAddress + new_vsize, sa) - (rest[0].VirtualAddress if rest else 1 << 62))
    va_shift = align(va_shift, sa)
    raw_shift = new_raw - old_raw

    pe2 = pefile.PE(data=bytes(new_file), fast_load=True)
    r2 = pe2.sections[ri]
    r2.Misc_VirtualSize = new_vsize
    r2.SizeOfRawData = new_raw
    o2 = pe2.OPTIONAL_HEADER
    o2.DATA_DIRECTORY[2].Size = new_vsize
    for s in pe2.sections[ri + 1:]:
        if s.Name.rstrip(b'\0') == b'.reloc' and o2.DATA_DIRECTORY[5].VirtualAddress == s.VirtualAddress:
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
    print(f'icon set: {out} (.rsrc grown by {raw_shift} bytes, .reloc moved by 0x{va_shift:x})')


if __name__ == '__main__':
    main(*sys.argv[1:4])
