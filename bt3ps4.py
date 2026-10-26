"""ISO9660 compatibility tools for BT3 mods on one Sony PS2-on-PS4 emulator.

Only Python's standard library is required. No game or emulator is included.
"""
import argparse
import hashlib
import json
import re
import shutil
import struct
import subprocess
import sys
import xml.etree.ElementTree as ET
from datetime import datetime
from pathlib import Path

SECTOR = 2048
EMULATOR_SHA256 = '83b771a27b1ac03802e4071068885658224732a15dedaed67f120307c6e651e7'
GS_OPTIONS = {
    'gs-uprender': '2x2', 'gs-upscale': 'edgesmooth',
    'gs-use-clut-merge': '1', 'gs-kernel-cl': '"clutmerge"',
    'gs-kernel-cl-up': '"clutmerge2x2"',
}


def sha256_file(path):
    digest = hashlib.sha256()
    with Path(path).open('rb') as stream:
        while block := stream.read(4 * 1024 * 1024):
            digest.update(block)
    return digest.hexdigest()


def both32(data, offset):
    little = struct.unpack_from('<I', data, offset)[0]
    if little != struct.unpack_from('>I', data, offset + 4)[0]:
        raise ValueError('ISO9660 little/big endian values disagree')
    return little


def round_sector(size):
    return (size + SECTOR - 1) // SECTOR * SECTOR


def scanner(stream, sectors):
    """Model of the observed DVD branch, not an emulation of all Sony loaders."""
    for lba in range(257, min(1000, sectors)):
        stream.seek(lba * SECTOR)
        data = stream.read(SECTOR)
        if data[:2] == b'\x30\x00':
            return {'sector': lba, 'length': struct.unpack_from('<I', data, 10)[0]}
    return {'sector': None, 'length': None}


def inspect(source):
    source = Path(source)
    size = source.stat().st_size
    report = {'bytes': size, 'directories': [], 'files': [], 'supplementary': False}
    with source.open('rb') as stream:
        def read(offset, count):
            if offset < 0 or count < 0 or offset + count > size:
                raise ValueError('ISO9660 extent exceeds the image')
            stream.seek(offset)
            block = stream.read(count)
            if len(block) != count:
                raise ValueError('Truncated image')
            return block

        pvd = None
        for sector in range(16, min(80, size // SECTOR)):
            data = read(sector * SECTOR, SECTOR)
            if data[1:7] != b'CD001\x01':
                continue  # A UDF bridge may have other descriptors.
            if data[0] == 1:
                if pvd is not None:
                    raise ValueError('Multiple primary volume descriptors are unsupported')
                pvd, report['pvd_sector'] = data, sector
            elif data[0] == 2:
                report['supplementary'] = True
            elif data[0] == 255:
                break
        if pvd is None:
            raise ValueError('No ISO9660 primary descriptor found; use a 2048-byte-sector ISO')
        if struct.unpack_from('<H', pvd, 128)[0] != SECTOR or struct.unpack_from('>H', pvd, 130)[0] != SECTOR:
            raise ValueError('Only 2048-byte ISO sectors are supported')
        report['volume_sectors'] = both32(pvd, 80)
        if report['volume_sectors'] * SECTOR > size:
            raise ValueError('Declared volume exceeds image')
        report['root_lba'] = both32(pvd, 158)
        report['pvd_root_record'] = pvd[156:190].hex()
        visited = set()

        def walk(record, path):
            lba, length = both32(record, 2), both32(record, 10)
            if lba in visited:
                raise ValueError('Repeated or cyclic directory extent')
            visited.add(lba)
            if length == 0 or length > 64 * 1024 * 1024:
                raise ValueError('Invalid or unsupported directory size')
            allocated = round_sector(length)
            data = read(lba * SECTOR, allocated)
            if any(data[length:]):
                raise ValueError('Directory tail contains data; refusing to overwrite it')
            directory = {'path': path, 'lba': lba, 'length': length,
                         'allocated': allocated, 'records': []}
            report['directories'].append(directory)
            offset = 0
            children = []
            names = set()
            while offset < length:
                count = data[offset]
                if count == 0:
                    end = min(round_sector(offset + 1), length)
                    if any(data[offset:end]):
                        raise ValueError('Nonzero bytes after directory sector padding')
                    offset = end
                    continue
                if count < 34 or offset + count > length or offset % SECTOR + count > SECTOR:
                    raise ValueError('Truncated record or record crossing a sector boundary')
                rec = data[offset:offset + count]
                if rec[1] or rec[25] & 0x80 or rec[26] or rec[27]:
                    raise ValueError('Extended attributes, multi-extent and interleaved files are unsupported')
                base = 33 + rec[32] + (rec[32] % 2 == 0)
                if base > count:
                    raise ValueError('Invalid file identifier length')
                start, length_entry = both32(rec, 2), both32(rec, 10)
                read(start * SECTOR, min(length_entry, 1))
                if start * SECTOR + length_entry > size:
                    raise ValueError('File extent exceeds image')
                name = rec[33:33 + rec[32]]
                directory['records'].append(rec.hex())
                if name in (b'\0', b'\1'):
                    if not rec[25] & 2:
                        raise ValueError('Dot entries must be directories')
                else:
                    name = name.decode('ascii')
                    if name in names or '/' in name or '\\' in name:
                        raise ValueError('Duplicate or invalid ISO identifier')
                    names.add(name)
                    child_path = path.rstrip('/') + '/' + name
                    if rec[25] & 2:
                        children.append((rec, child_path))
                    else:
                        report['files'].append({'path': child_path, 'lba': start, 'bytes': length_entry})
                offset += count
            if len(directory['records']) < 2:
                raise ValueError('Directory is missing dot entries')
            first = bytes.fromhex(directory['records'][0])
            second = bytes.fromhex(directory['records'][1])
            if first[33:34] != b'\0' or second[33:34] != b'\1' or both32(first, 2) != lba:
                raise ValueError('Invalid dot entry order or extent')
            for rec, child_path in children:
                walk(rec, child_path)

        walk(pvd[156:190], '/')
        report['scanner_before'] = scanner(stream, size // SECTOR)
        cnf = next((f for f in report['files'] if f['path'].upper() == '/SYSTEM.CNF;1'), None)
        if cnf and cnf['bytes'] <= 65536:
            report['system_cnf'] = read(cnf['lba'] * SECTOR, cnf['bytes']).decode('ascii', errors='replace')
        match = re.search(r'(?im)^\s*BOOT2\s*=\s*cdrom0:\\+([A-Z]{4})_(\d{3})\.(\d{2})(?:;\d+)?', report.get('system_cnf', ''))
        report['ps2_id'] = f'{match[1]}-{match[2]}{match[3]}' if match else None
        report['known_bt3_family_id'] = report['ps2_id'] in ('SLUS-21678', 'SLUS-21978')
        footer = read(size - 16384, 16384) if size >= 16384 else b''
        report['has_limg'] = footer[:4] == b'LIMG'
        report['payload_bytes'] = size - 16384 if report['has_limg'] else size
        if report['payload_bytes'] % SECTOR:
            raise ValueError('Image payload is not a multiple of 2048 bytes')
        if report['has_limg']:
            magic, version, sectors, block = struct.unpack_from('>4sIII', footer)
            if version != 1 or sectors * SECTOR != report['payload_bytes'] or block != SECTOR or any(footer[16:]):
                raise ValueError('Unrecognized LIMG footer')
    return report


def plan(source):
    report = inspect(source)
    if report['supplementary']:
        raise ValueError('Supplementary/Joliet descriptors require separate analysis; no rewrite performed')
    if not 257 <= report['root_lba'] < 1000:
        raise ValueError('Root is outside the observed DVD scan range; this fix does not apply')
    directories = report['directories']
    sizes = {d['lba']: d['allocated'] for d in directories}
    patches = []
    for directory in directories:
        result = bytearray()
        for raw in directory['records']:
            rec = bytes.fromhex(raw)
            base = 33 + rec[32] + (rec[32] % 2 == 0)
            if len(rec) - base not in (0, 14) or any(rec[base:]):
                raise ValueError('Unknown System Use data; refusing to strip it')
            rebuilt = bytearray(rec[:base])
            if base + 14 > 255:
                raise ValueError('Record would exceed ISO9660 length limit')
            rebuilt[0] = base + 14
            if rebuilt[25] & 2:
                target = both32(rebuilt, 2)
                if target not in sizes:
                    raise ValueError('Directory reference not present in the tree')
                struct.pack_into('<I', rebuilt, 10, sizes[target])
                struct.pack_into('>I', rebuilt, 14, sizes[target])
            rebuilt.extend(bytes(14))
            remaining = SECTOR - len(result) % SECTOR
            if remaining < len(rebuilt):
                result.extend(bytes(remaining))
            result.extend(rebuilt)
        if len(result) > directory['allocated']:
            raise ValueError('Expanded directory does not fit; moving file LBAs is not supported')
        result.extend(bytes(directory['allocated'] - len(result)))
        patches.append((directory['lba'] * SECTOR, bytes(result)))
    root_size = sizes[report['root_lba']]
    patches.append((report['pvd_sector'] * SECTOR + 166, struct.pack('<I', root_size) + struct.pack('>I', root_size)))
    patches.sort()
    for index, (offset, data) in enumerate(patches):
        if index and patches[index - 1][0] + len(patches[index - 1][1]) > offset:
            raise ValueError('Overlapping metadata extents')
        for item in report['files']:
            if max(offset, item['lba'] * SECTOR) < min(offset + len(data), item['lba'] * SECTOR + item['bytes']):
                raise ValueError('Metadata overlaps game file data')
    with Path(source).open('rb') as stream:
        for lba in range(257, report['root_lba']):
            offset = lba * SECTOR
            stream.seek(offset)
            first = stream.read(2)
            for patch_offset, patch in patches:
                if patch_offset <= offset and offset + 2 <= patch_offset + len(patch):
                    first = patch[offset - patch_offset:offset - patch_offset + 2]
            if first == b'\x30\0':
                raise ValueError('An earlier scanner marker remains; this image needs another solution')
    return report, patches


def normalized(source, output):
    source, output = Path(source), Path(output)
    if source.resolve() == output.resolve():
        raise ValueError('Input and output must be different files')
    report, patches = plan(source)
    if output.exists():
        raise FileExistsError('Output already exists; no overwrite allowed')
    output.parent.mkdir(parents=True, exist_ok=True)
    partial = output.with_name(output.name + '.partial')
    source_hash = hashlib.sha256()
    with partial.open('xb') as dest:
        try:
            with source.open('rb') as stream:
                while block := stream.read(4 * 1024 * 1024):
                    source_hash.update(block)
                    dest.write(block)
            for offset, data in patches:
                dest.seek(offset)
                dest.write(data)
            if not report['has_limg']:
                footer = bytearray(16384)
                struct.pack_into('>4sIII', footer, 0, b'LIMG', 1, report['payload_bytes'] // SECTOR, SECTOR)
                dest.seek(0, 2)
                dest.write(footer)
        except BaseException:
            # Leave a clearly named partial, never alter the user's original.
            raise
    output_hash = hashlib.sha256()
    verified_source_hash = hashlib.sha256()
    with source.open('rb') as left, partial.open('rb') as right:
        offset = 0
        while original := left.read(4 * 1024 * 1024):
            verified_source_hash.update(original)
            expected = bytearray(original)
            for start, patch in patches:
                lo, hi = max(start, offset), min(start + len(patch), offset + len(original))
                if lo < hi:
                    expected[lo - offset:hi - offset] = patch[lo - start:hi - start]
            actual = right.read(len(original))
            if expected != actual:
                raise ValueError('Output differs from the exact planned metadata changes')
            output_hash.update(actual)
            offset += len(original)
        tail = right.read()
        if not report['has_limg']:
            if tail != bytes(footer):
                raise ValueError('Unexpected output footer')
        elif tail:
            raise ValueError('Unexpected extra output bytes')
        output_hash.update(tail)
    if verified_source_hash.hexdigest() != source_hash.hexdigest():
        raise ValueError('Source changed during normalization')
    after = inspect(partial)
    if after['files'] != report['files'] or after['scanner_before'] != {'sector': report['root_lba'], 'length': report['directories'][0]['allocated']}:
        raise ValueError('Post-write file layout or scanner check failed')
    # Exclusive reservation prevents replacing an output created during the run.
    with output.open('xb'):
        pass
    partial.replace(output)
    return {'source_sha256': source_hash.hexdigest(), 'output_sha256': output_hash.hexdigest(),
            'output_bytes': output.stat().st_size, 'ps2_id': report['ps2_id'],
            'files_and_lbas_unchanged': True, 'all_bytes_outside_planned_metadata_unchanged': True,
            'scanner_before': report['scanner_before'], 'scanner_after': after['scanner_before'],
            'directories': len(report['directories']), 'files': len(report['files']),
            'hardware_status': 'not_tested_by_this_run'}


def sfo_update(data, replacements):
    """Update existing bounded UTF-8 PSF entries without proprietary libraries."""
    data = bytearray(data)
    if len(data) < 20 or data[:4] != b'\x00PSF':
        raise ValueError('Not a param.sfo file')
    version, keys, values, count = struct.unpack_from('<4I', data, 4)
    if 20 + 16 * count > keys or keys > values or values > len(data):
        raise ValueError('Invalid SFO tables')
    found = set()
    for index in range(count):
        pos = 20 + index * 16
        key_offset, kind, length, capacity, value_offset = struct.unpack_from('<HHIII', data, pos)
        start = keys + key_offset
        end = data.find(0, start, values)
        if start >= values or end < start:
            raise ValueError('Invalid SFO key')
        key = data[start:end].decode('ascii')
        replacement = replacements.get(key)
        if key.startswith('TITLE_') and key[6:].isdigit():
            replacement = replacements.get('TITLE')
        if replacement is None:
            continue
        payload = replacement.encode('utf-8') + b'\0'
        dest = values + value_offset
        if kind != 0x0204 or len(payload) > capacity or dest + capacity > len(data):
            raise ValueError('SFO replacement does not fit: ' + key)
        data[dest:dest + capacity] = payload + bytes(capacity - len(payload))
        struct.pack_into('<I', data, pos + 4, len(payload))
        found.add(key)
    if set(replacements) - found:
        raise ValueError('Required SFO fields missing: ' + ', '.join(sorted(set(replacements) - found)))
    return bytes(data)


def prepare(image, template, output, title_id, title, version='01.00'):
    """Prepare a new standalone app project from the user's own local wrapper."""
    image, template, output = Path(image).resolve(), Path(template).resolve(), Path(output).resolve()
    if not re.fullmatch(r'[A-Z]{4}[0-9]{5}', title_id) or not re.fullmatch(r'\d{2}\.\d{2}', version):
        raise ValueError('Invalid PS4 title ID or application version')
    if output.exists() or output == template or template in output.parents or output in template.parents:
        raise ValueError('Use a new output directory outside the template')
    report = inspect(image)
    if not report['known_bt3_family_id']:
        raise ValueError('The bundled graphics profile is limited to the inspected BT3-family IDs')
    if not report['has_limg'] or report['scanner_before'] != {'sector': report['root_lba'], 'length': report['directories'][0]['allocated']}:
        raise ValueError('Normalize and validate the image first')
    for name in ('eboot.bin', 'ps2-emu-compiler.self', 'formatted.card', 'config-emu-ps4.txt', 'sce_sys/param.sfo'):
        if not (template / name).is_file():
            raise ValueError('Template is missing ' + name)
    native_hash = sha256_file(template / 'eboot.bin')
    if native_hash != EMULATOR_SHA256:
        raise ValueError('Template emulator is not the inspected revision; no profile will be applied')
    for path in template.rglob('*'):
        if path.is_symlink():
            raise ValueError('Template symlinks are unsupported')
    content_id = 'UP9000-' + title_id + '_00-' + title_id + '0000001'
    param = sfo_update((template / 'sce_sys/param.sfo').read_bytes(), {
        'TITLE_ID': title_id, 'CONTENT_ID': content_id, 'TITLE': title,
        'APP_VER': version, 'CATEGORY': 'gd',
    })
    config = (template / 'config-emu-ps4.txt').read_text(encoding='utf-8-sig')
    kept = []
    for line in config.splitlines():
        key = line.strip().split('=', 1)[0].removeprefix('--')
        if not line.strip().startswith('#') and key not in GS_OPTIONS and key not in (
                'vu1', 'ps2-title-id', 'max-disc-num', 'config-local-lua'):
            kept.append(line)
    config = '\n'.join(kept) + '\n'
    config += '--ps2-title-id=' + report['ps2_id'] + '\n--max-disc-num=1\n--config-local-lua=""\n'
    config += ''.join('--' + key + '=' + value + '\n' for key, value in GS_OPTIONS.items())
    output.mkdir(parents=True)
    app = output / 'app'
    # The user supplies this tree. It is never part of the public repository.
    ignored = {'image', 'patches', 'sce_discmap.plt', 'keystone', 'about', 'icon0.dds', 'pic1.dds'}
    shutil.copytree(template, app, ignore=lambda parent, names: set(names) & ignored)
    (app / 'config-emu-ps4.txt').write_text(config, encoding='utf-8', newline='\n')
    (app / 'sce_sys/param.sfo').write_bytes(param)
    patches = app / 'patches'
    patches.mkdir()
    lua = ('-- Graphics-only profile; no executable-address hooks.\napiRequest(2.2)\n'
           'local emu = getEmuObject()\n'
           'emu.SetGsTitleFix("forceSimpleFetch", "reserved", { texMode=1 })\n'
           'emu.SetGsTitleFix("forceSimpleFetch", "reserved", { texMode=2 })\n')
    (patches / (report['ps2_id'] + '_config.lua')).write_text(lua, encoding='utf-8', newline='\n')
    project = ET.Element('psproject', {'fmt': 'gp4', 'version': '1000'})
    volume = ET.SubElement(project, 'volume')
    ET.SubElement(volume, 'volume_type').text = 'pkg_ps4_app'
    ET.SubElement(volume, 'volume_id')
    ET.SubElement(volume, 'volume_ts').text = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    ET.SubElement(volume, 'package', {'content_id': content_id, 'passcode': '0' * 32,
                                    'storage_type': 'digital50', 'app_type': 'full'})
    info = ET.SubElement(volume, 'chunk_info', {'chunk_count': '1', 'scenario_count': '1'})
    ET.SubElement(ET.SubElement(info, 'chunks'), 'chunk', {'id': '0', 'layer_no': '0', 'label': 'Chunk #0'})
    scenarios = ET.SubElement(info, 'scenarios', {'default_id': '0'})
    ET.SubElement(scenarios, 'scenario', {'id': '0', 'type': 'sp', 'initial_chunk_count': '1', 'label': 'Scenario #0'}).text = '0'
    files = ET.SubElement(project, 'files', {'img_no': '0'})
    paths = [(p.relative_to(app).as_posix(), p) for p in sorted(app.rglob('*')) if p.is_file()]
    paths.append(('image/disc01.iso', image))
    for target, original in paths:
        attributes = {'targ_path': target, 'orig_path': str(original)}
        if target == 'image/disc01.iso':
            attributes['pfs_compression'] = 'enable'
        ET.SubElement(files, 'file', attributes)
    rootdir = ET.SubElement(project, 'rootdir')
    dirs = {'image'}
    for target, original in paths:
        parent = Path(target).parent
        while parent.as_posix() != '.':
            dirs.add(parent.as_posix())
            parent = parent.parent
    nodes = {'': rootdir}
    for directory in sorted(dirs, key=lambda p: (p.count('/'), p)):
        parent, _, name = directory.rpartition('/')
        nodes[directory] = ET.SubElement(nodes[parent], 'dir', {'targ_name': name})
    ET.indent(project)
    project_path = output / 'project.gp4'
    ET.ElementTree(project).write(project_path, encoding='utf-8', xml_declaration=True)
    result = {'title_id': title_id, 'content_id': content_id, 'app_version': version,
              'ps2_id': report['ps2_id'], 'emulator_sha256': native_hash,
              'gp4': str(project_path), 'profile': GS_OPTIONS,
              'source_game_files_modified': False, 'hardware_status': 'not_tested',
              'note': 'Full standalone package project; not an update for an existing title.'}
    (output / 'manifest.json').write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
    return result


def build_pkg(project, builder, output):
    """Invoke a user-supplied local img_create tool; never download a toolchain."""
    project, builder, output = Path(project).resolve(), Path(builder).resolve(), Path(output).resolve()
    if not project.is_file() or not builder.is_file():
        raise ValueError('Supply an existing GP4 project and local PKG builder')
    if output.exists():
        raise FileExistsError('Package output already exists')
    tree = ET.parse(project)
    package = tree.find('./volume/package')
    if package is None or tree.findtext('./volume/volume_type') != 'pkg_ps4_app':
        raise ValueError('Expected a standalone full-application project')
    output.parent.mkdir(parents=True, exist_ok=True)
    # img_create --oformat pkg expects an existing output DIRECTORY.
    build_folder = output.with_name(output.stem + '.build')
    build_folder.mkdir()
    command = [str(builder), 'img_create', '--oformat', 'pkg', '--no_progress_bar', str(project), str(build_folder)]
    subprocess.run(command, cwd=project.parent, check=True)
    packages = list(build_folder.glob('*.pkg'))
    if len(packages) != 1:
        raise ValueError('Expected exactly one package from the builder')
    built = packages[0]
    with built.open('rb') as stream:
        header = stream.read(256)
        if header[:4] != b'\x7fCNT' or header[0x40:0x70].split(b'\0')[0].decode('ascii') != package.attrib['content_id']:
            raise ValueError('Built package header or Content ID does not match the project')
    checksum = sha256_file(built)
    with output.open('xb'):
        pass
    built.replace(output)
    return {'package': str(output), 'bytes': output.stat().st_size, 'sha256': checksum,
            'content_id': package.attrib['content_id'], 'hardware_status': 'not_tested'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    for command in ('inspect', 'normalize'):
        item = sub.add_parser(command)
        item.add_argument('image', type=Path)
        item.add_argument('--report', type=Path)
        if command == 'normalize':
            item.add_argument('--output', required=True, type=Path)
    item = sub.add_parser('prepare-pkg')
    item.add_argument('image', type=Path)
    item.add_argument('--template', required=True, type=Path)
    item.add_argument('--output', required=True, type=Path)
    item.add_argument('--title-id', required=True)
    item.add_argument('--title', required=True)
    item.add_argument('--version', default='01.00')
    item = sub.add_parser('build-pkg')
    item.add_argument('project', type=Path)
    item.add_argument('--builder', required=True, type=Path)
    item.add_argument('--output', required=True, type=Path)
    args = parser.parse_args()
    try:
        if args.command == 'inspect':
            result = inspect(args.image)
            try:
                _, patches = plan(args.image)
                result['normalization_supported'] = True
                result['planned_metadata_regions'] = len(patches)
            except ValueError as exc:
                result['normalization_supported'] = False
                result['reason'] = str(exc)
            for directory in result['directories']:
                directory['records_count'] = len(directory.pop('records'))
        elif args.command == 'normalize':
            result = normalized(args.image, args.output)
        elif args.command == 'prepare-pkg':
            result = prepare(args.image, args.template, args.output, args.title_id, args.title, args.version)
        else:
            result = build_pkg(args.project, args.builder, args.output)
        text = json.dumps(result, ensure_ascii=False, indent=2) + '\n'
        if getattr(args, 'report', None):
            with args.report.open('x', encoding='utf-8') as dest:
                dest.write(text)
        print(text, end='')
    except (ValueError, OSError, struct.error, subprocess.CalledProcessError, ET.ParseError) as exc:
        print('ERROR: ' + str(exc), file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())
