"""Rewrites the version strings inside a Windows .exe in place (what Task Manager and Explorer show).

Each new value must fit in the space of the old one; the rest of the slot is zero-filled.
"""
import json, os, struct, sys
import pefile

# The version comes from app/package.json (the one place it is set).
APP_VERSION = json.load(open(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'app', 'package.json')))['version']

VALUES = {
    'CompanyName': 'R64texHD',
    'FileDescription': 'R64texHD',          # Task Manager's process name
    'FileVersion': APP_VERSION,
    'InternalName': 'R64texHD.exe',
    'LegalCopyright': 'HD Texture Toolkit - RT64 Support',
    'OriginalFilename': 'R64texHD.exe',
    'ProductName': 'R64texHD',
    'ProductVersion': APP_VERSION,
}
VERSION = tuple((list(map(int, APP_VERSION.split('.'))) + [0, 0, 0, 0])[:4])

def main(src, dst):
    pe = pefile.PE(src, fast_load=True)
    pe.parse_data_directories(directories=[pefile.DIRECTORY_ENTRY['IMAGE_DIRECTORY_ENTRY_RESOURCE']])
    data = bytearray(pe.__data__)
    done = set()
    for fi in pe.FileInfo[0]:
        for st in getattr(fi, 'StringTable', []):
            for key, (key_off, value_off) in st.entries_offsets.items():
                name = key.decode()
                if name not in VALUES:
                    continue
                old_len = st.entries_lengths[key][1]          # characters, without the terminator
                new = VALUES[name]
                if len(new) > old_len:
                    raise SystemExit(f'{name}: "{new}" is longer than the original ({old_len} characters)')
                slot = (old_len + 1) * 2
                data[value_off:value_off + slot] = (new.encode('utf-16-le') + b'\0' * slot)[:slot]
                # String header (wLength, wValueLength, wType) sits just before the key.
                header = key_off - 6
                struct.pack_into('<H', data, header + 2, len(new) + 1)
                done.add(name)
    missing = set(VALUES) - done
    if missing:
        raise SystemExit('not found: ' + ', '.join(sorted(missing)))
    ff = pe.VS_FIXEDFILEINFO[0]
    off = ff.get_file_offset()
    ms, ls = (VERSION[0] << 16) | VERSION[1], (VERSION[2] << 16) | VERSION[3]
    struct.pack_into('<IIII', data, off + 8, ms, ls, ms, ls)   # dwFileVersionMS/LS, dwProductVersionMS/LS
    out = pefile.PE(data=bytes(data), fast_load=True)
    out.OPTIONAL_HEADER.CheckSum = out.generate_checksum()
    out.write(dst)
    print('version info set:', dst)

if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2])
