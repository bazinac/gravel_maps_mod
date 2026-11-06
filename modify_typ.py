#!/usr/bin/env python3
"""
Gravelista Garmin Map Style Customizer (Bazinac Mod)
---------------------------------------------------
Modifies line dimensions, bitmap patterns, and header table offsets in Garmin TYP files.
Designed for GravelistaCZ map optimization on Garmin Edge 850 / 1050 / 1060.
"""

import os
import sys
import struct

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

def update_widths(input_path=None, output_path=None):
    if input_path is None:
        input_path = os.path.join(BASE_DIR, 'STYLE_original.typ')
    if output_path is None:
        output_path = os.path.join(BASE_DIR, 'STYLE_BAZINAC_V4.typ')
    
    with open(input_path, 'rb') as f:
        data = bytearray(f.read())
        
    hdr_len = struct.unpack('<H', data[:2])[0]
    fmt = '<6I2HIH2IH2IH2IH1I'
    header = list(struct.unpack(fmt, data[23:91]))
    
    line_dataofs = header[2]
    line_datalen = header[3]
    line_ar_ofs = header[11]
    line_ar_mod = header[12]
    line_ar_sz = header[13]
    count = line_ar_sz // line_ar_mod
    
    entries = []
    for i in range(count):
        chunk = data[line_ar_ofs + i*line_ar_mod : line_ar_ofs + (i+1)*line_ar_mod]
        otyp, ofs = struct.unpack('<HH', chunk[:4])
        wtyp = (otyp >> 5) | ((otyp & 0x1f) << 11)
        typ = wtyp & 0x7ff
        subtyp = wtyp >> 11
        entries.append({
            'idx': i,
            'otyp': otyp,
            'ofs': ofs,
            'typ': typ,
            'sub': subtyp
        })
        
    sorted_entries = sorted(entries, key=lambda x: x['ofs'])
    for i, e in enumerate(sorted_entries):
        if i + 1 < len(sorted_entries):
            e['len'] = sorted_entries[i+1]['ofs'] - e['ofs']
        else:
            e['len'] = line_datalen - e['ofs']
            
    line_colortypes = {
        0x00: {'numcolors': 2, 'borderless': False},
        0x01: {'numcolors': 4, 'borderless': False},
        0x03: {'numcolors': 3, 'borderless': False},
        0x05: {'numcolors': 3, 'borderless': True},
        0x06: {'numcolors': 1, 'borderless': True},
        0x07: {'numcolors': 2, 'borderless': True},
    }

    mods = {
        # Category 1: Cycling Infrastructure
        (0x11, 0): {'lw': 7, 'total': 7},                                 # dedicated cycleway (7px)
        (0x16, 0): {'lw': 4, 'total': 6},                                 # bike path (4+1=6px)
        (0x0b, 0): {'new_height': 6, 'pattern_mode': 'dash_2on2off'},     # unpaved bikepath (6px)
        (0x0e, 0): {'new_height': 6, 'pattern_mode': 'dash_6on2off'},     # bikepath compacted (6px)
        (0x101, 0x16): {'new_height': 7, 'pattern_mode': 'solid_border'}, # cyclestreet (7px)
        (0x26, 0): {'new_height': 8, 'pattern_mode': 'bikelane_8'},       # road with bikelane (8px)
        (0x100, 0x09): {'new_height': 9, 'pattern_mode': 'cycleway_9'},   # road with cycleway (9px)
        (0x100, 0x16): {'lw': 4, 'total': 4},                             # paved road (cycling allowed) (4px)
        
        # Category 2: Gravel, Tracks & Pathways
        (0x0f, 0): {'lw': 3, 'total': 3},                                 # track road (gravel) (3px)
        (0x0a, 0): {'new_height': 5, 'pattern_mode': 'dash_5on3off'},     # path / singletrack (5px as Petr V4/V5)
        (0x15, 0): {'new_height': 5, 'pattern_mode': 'dash_5on3off'},     # track or path (5px as Petr V4/V5)
        (0x0d, 0): {'new_height': 4, 'pattern_mode': 'orig_path_0d'},     # path (cycling allowed) (4px) [V4]
        (0x08, 0): {'new_height': 2, 'pattern_mode': 'dots3'},            # pedestrian (2px)
        
        # Category 3: General Roads
        (0x01, 0): {'lw': 12, 'total': 16},                               # motorway, trunk (12+2=16px) [V4]
        (0x03, 0): {'lw': 12, 'total': 16},                               # principal highway (12+2=16px) [V4]
        (0x04, 0): {'lw': 11, 'total': 15},                               # secondary highway (11+2=15px) [V4]
        (0x05, 0): {'lw': 10, 'total': 14},                               # tertiary road (10+2=14px) [V4]
        (0x06, 0): {'lw': 7, 'total': 11},                                # residential street (7+2=11px) [V4]
        (0x07, 0): {'lw': 2, 'total': 2},                                 # service road (2px)
        (0x10, 0): {'lw': 7, 'total': 11},                                # minor paved road (7+2=11px) [V4]
        (0x12, 0): {'lw': 11, 'total': 15},                               # secondary road (11+2=15px) [V4]
        (0x100, 0): {'lw': 4, 'total': 4},                                # minor paved road alt (4px)
        (0x100, 0x01): {'lw': 6, 'total': 10},                            # tertiary road alt (6+2=10px) [V4]
        (0x100, 0x13): {'lw': 5, 'total': 9},                             # motorway, trunk alt (5+2=9px)
        (0x101, 0x03): {'new_height': 8, 'pattern_mode': 'solid_border'}, # principal (8px)
        (0x101, 0x04): {'new_height': 8, 'pattern_mode': 'solid_border'}, # secondary (8px)
        (0x101, 0x05): {'new_height': 7, 'pattern_mode': 'solid_border'}, # tertiary (7px)
        (0x101, 0x06): {'new_height': 6, 'pattern_mode': 'solid_border'}, # street (6px)
    }

    def generate_pattern(mode, height):
        row_transparent = b'\x00\x00\x00\x00'
        if mode == 'dots3':
            # Original STYLE.TYP dot pattern: 0x03 = 00000011 (2px dot every 8px)
            row_dot = b'\x03\x03\x03\x03'
            return row_dot * height
        elif mode == 'dash_2on2off':
            row_dash = b'\x33\x33\x33\x33'
            return row_transparent + row_dash * (height - 2) + row_transparent
        elif mode == 'dash_5on3off':
            row_dash = b'\x1f\x1f\x1f\x1f'
            return row_transparent + row_dash * (height - 2) + row_transparent
        elif mode == 'dash_6on2off':
            row_dash = b'\xfc\xfc\xfc\xfc'
            return row_transparent + row_dash * (height - 2) + row_transparent
        elif mode == 'orig_path_0a':
            return b'\x0f\x3e\xf8\xc0' * height
        elif mode == 'orig_path_15':
            return b'\xcf\x3f\xff\xf8' * height
        elif mode == 'orig_path_0d':
            return b'\xcf\x3f\xff\xfc' * height
        elif mode == 'solid_border':
            row_solid = b'\xff\xff\xff\xff'
            return row_transparent + row_solid * (height - 2) + row_transparent
        elif mode == 'bikelane_8':
            # 8px: 2px dashed top, 4px transparent center, 2px dashed bottom
            return b'\x33\x33\x33\x33' * 2 + b'\x00\x00\x00\x00' * 4 + b'\x33\x33\x33\x33' * 2
        elif mode == 'cycleway_9':
            # 9px: 2px solid top, 5px transparent center, 2px solid bottom
            return b'\xff\xff\xff\xff' * 2 + b'\x00\x00\x00\x00' * 5 + b'\xff\xff\xff\xff' * 2
        else:
            raise ValueError(f"Unknown mode: {mode}")

    cely_obsah = data[line_dataofs : line_dataofs + line_datalen]
    new_elements = []
    
    for e in sorted_entries:
        edata = bytearray(cely_obsah[e['ofs'] : e['ofs'] + e['len']])
        key = (e['typ'], e['sub'])
        
        a, b = edata[0], edata[1]
        ctype = a & 0x07
        radku = a >> 3
        info = line_colortypes.get(ctype, {'numcolors': 0, 'borderless': False})
        pos = 2 + 3 * info['numcolors']
        
        if key in mods:
            m = mods[key]
            if radku == 0:
                if info['borderless']:
                    edata[pos] = m['lw']
                else:
                    edata[pos] = m['lw']
                    edata[pos+1] = m['total']
            else:
                new_h = m['new_height']
                new_bm = generate_pattern(m['pattern_mode'], new_h)
                edata[0] = ctype | (new_h << 3)
                old_bm_len = 4 * radku
                labels_part = edata[pos + old_bm_len :]
                edata = edata[:pos] + new_bm + labels_part
                
        new_elements.append({
            'entry': e,
            'data': edata
        })

    new_line_data = bytearray()
    for ne in new_elements:
        ne['new_ofs'] = len(new_line_data)
        new_line_data.extend(ne['data'])
        
    delta = len(new_line_data) - line_datalen
    print(f'Old line datalen: {line_datalen}, New: {len(new_line_data)}, Delta: {delta:+d}')
    
    new_line_ar = bytearray()
    for e in entries:
        ne = next(item for item in new_elements if item['entry']['idx'] == e['idx'])
        chunk = struct.pack('<HH', e['otyp'], ne['new_ofs'])
        new_line_ar.extend(chunk)
        
    part1 = data[:line_dataofs]
    part2 = new_line_data
    part3 = new_line_ar
    old_after_line_ar = data[line_ar_ofs + line_ar_sz :]
    
    new_data = part1 + part2 + part3 + old_after_line_ar
    
    header[3] = len(new_line_data)
    header[11] += delta
    header[0] += delta
    header[8] += delta
    header[17] += delta
    
    new_header_bytes = struct.pack(fmt, *header)
    new_data[23:91] = new_header_bytes
    
    with open(output_path, 'wb') as f:
        f.write(new_data)
    print(f'Wrote {output_path} (size={len(new_data)})')
    
    # Also write default STYLE.TYP for gmt convenience
    try:
        default_style_typ = os.path.join(BASE_DIR, 'STYLE.TYP')
        if os.path.abspath(output_path) != os.path.abspath(default_style_typ):
            with open(default_style_typ, 'wb') as f:
                f.write(new_data)
            print(f'Wrote {default_style_typ} (size={len(new_data)})')
    except Exception as ex:
        print(f'Note: Could not write default STYLE.TYP: {ex}')

if __name__ == '__main__':
    in_file = sys.argv[1] if len(sys.argv) > 1 else None
    out_file = sys.argv[2] if len(sys.argv) > 2 else None
    update_widths(in_file, out_file)
