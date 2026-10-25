"""Replaces the icon images inside a Windows .exe in place (same sizes, data must fit the existing slots)."""
import io, struct, sys
import pefile
from PIL import Image

def dib(img):
    w, h = img.size
    px = img.convert('RGBA').tobytes('raw', 'BGRA')
    rows = [px[y * w * 4:(y + 1) * w * 4] for y in range(h)][::-1]
    mask_row = ((w + 31) // 32) * 4
    header = struct.pack('<IiiHHIIiiII', 40, w, h * 2, 1, 32, 0, w * h * 4 + mask_row * h, 0, 0, 0, 0)
    return header + b''.join(rows) + b'\0' * (mask_row * h)

def main(exe, icon_png, out):
    src = Image.open(icon_png).convert('RGBA')
    pe = pefile.PE(exe, fast_load=True)
    pe.parse_data_directories(directories=[pefile.DIRECTORY_ENTRY['IMAGE_DIRECTORY_ENTRY_RESOURCE']])
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
            if w >= 256:
                data = None
                for colors in (None, 256, 192, 128, 96, 64):
                    candidate = img if colors is None else img.quantize(colors=colors, method=Image.Quantize.FASTOCTREE).convert('RGBA')
                    buf = io.BytesIO(); candidate.save(buf, 'PNG', optimize=True)
                    data = buf.getvalue()
                    if len(data) <= slot.struct.Size:
                        if colors: print(f'  256x256 icon reduced to {colors} colours to fit ({len(data)} bytes)')
                        break
            else:
                data = dib(img)
            if len(data) > slot.struct.Size:
                raise SystemExit(f'{w}x{h} icon ({len(data)} bytes) does not fit its slot ({slot.struct.Size})')
            pe.set_bytes_at_rva(slot.struct.OffsetToData, data + b'\0' * (slot.struct.Size - len(data)))
            slot.struct.Size = len(data)
            struct.pack_into('<BBBBHHIH', raw, o, w % 256, h % 256, 0, 0, 1, 32, len(data), iid)
        pe.set_bytes_at_rva(g.struct.OffsetToData, bytes(raw))
    pe.write(out)
    print('icon set:', out)

if __name__ == '__main__':
    main(*sys.argv[1:4])
