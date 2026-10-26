import hashlib
from pathlib import Path
import struct
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import bt3ps4 as tool


def number(data, pos, value):
    struct.pack_into('<I', data, pos, value)
    struct.pack_into('>I', data, pos + 4, value)


def record(name, lba, size, directory=False, extra=b''):
    base = 33 + len(name) + (len(name) % 2 == 0)
    data = bytearray(base)
    data[0] = base + len(extra)
    number(data, 2, lba)
    number(data, 10, size)
    data[25] = 2 if directory else 0
    data[28:32] = b'\x01\x00\x00\x01'
    data[32] = len(name)
    data[33:33 + len(name)] = name
    return bytes(data) + extra


def image(path, extra=b'', files=1, root=259):
    cnf = b'BOOT2 = cdrom0:\\SLUS_216.78;1\r\n'
    entries = [record(b'SYSTEM.CNF;1', 400, len(cnf), extra=extra)]
    entries += [record(('F%05d;1' % i).encode(), 401 + i, 4, extra=extra) for i in range(files - 1)]
    length = 2 * (34 + len(extra)) + sum(map(len, entries))
    directory = record(b'\0', root, length, True, extra) + record(b'\1', root, length, True, extra) + b''.join(entries)
    data = bytearray(1024 * 2048)
    pvd = bytearray(2048)
    pvd[:7] = b'\x01CD001\x01'
    number(pvd, 80, 1024)
    pvd[128:132] = b'\x00\x08\x08\x00'
    pvd[156:190] = record(b'\0', root, length, True)
    data[16 * 2048:17 * 2048] = pvd
    data[17 * 2048:17 * 2048 + 7] = b'\xffCD001\x01'
    data[root * 2048:root * 2048 + len(directory)] = directory
    data[400 * 2048:400 * 2048 + len(cnf)] = cnf
    for i in range(files - 1):
        data[(401 + i) * 2048:(401 + i) * 2048 + 4] = b'DATA'
    data[340 * 2048:340 * 2048 + 2] = b'\x30\0'
    struct.pack_into('<I', data, 340 * 2048 + 10, 589744)
    path.write_bytes(data)
    return data


class ISOTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.source = self.root / 'original.iso'
        self.output = self.root / 'fixed.iso'

    def tearDown(self):
        self.tmp.cleanup()

    def test_normalization_preserves_original_and_every_file(self):
        before = image(self.source)
        result = tool.normalized(self.source, self.output)
        self.assertEqual(self.source.read_bytes(), before)
        self.assertEqual(result['scanner_before'], {'sector': 340, 'length': 589744})
        self.assertEqual(result['scanner_after'], {'sector': 259, 'length': 2048})
        self.assertEqual(tool.inspect(self.source)['files'], tool.inspect(self.output)['files'])
        self.assertEqual(self.output.read_bytes()[400 * 2048:401 * 2048], before[400 * 2048:401 * 2048])
        self.assertEqual(result['ps2_id'], 'SLUS-21678')
        self.assertTrue(result['all_bytes_outside_planned_metadata_unchanged'])

    def test_idempotence_does_not_duplicate_limg(self):
        image(self.source)
        tool.normalized(self.source, self.output)
        again = self.root / 'again.iso'
        tool.normalized(self.output, again)
        self.assertEqual(self.output.read_bytes(), again.read_bytes())

    def test_unknown_system_use_is_not_removed(self):
        image(self.source, extra=b'PX' + bytes(12))
        with self.assertRaisesRegex(ValueError, 'System Use'):
            tool.normalized(self.source, self.output)
        self.assertFalse(self.output.exists())

    def test_directory_growth_cannot_move_game_extents(self):
        image(self.source, files=43)
        with self.assertRaisesRegex(ValueError, 'does not fit'):
            tool.normalized(self.source, self.output)

    def test_overlapping_game_extent_is_rejected(self):
        data = image(self.source)
        number(data, 259 * 2048 + 68 + 2, 259)
        self.source.write_bytes(data)
        with self.assertRaisesRegex(ValueError, 'overlaps game'):
            tool.plan(self.source)

    def test_earlier_false_marker_is_rejected(self):
        data = image(self.source)
        data[258 * 2048:258 * 2048 + 2] = b'\x30\0'
        self.source.write_bytes(data)
        with self.assertRaisesRegex(ValueError, 'earlier scanner'):
            tool.plan(self.source)

    def test_unknown_root_location_is_rejected(self):
        image(self.source, root=250)
        with self.assertRaisesRegex(ValueError, 'outside'):
            tool.plan(self.source)

    def test_existing_output_and_input_are_protected(self):
        image(self.source)
        self.output.write_bytes(b'KEEP')
        with self.assertRaises(FileExistsError):
            tool.normalized(self.source, self.output)
        self.assertEqual(self.output.read_bytes(), b'KEEP')
        with self.assertRaises(ValueError):
            tool.normalized(self.source, self.source)

    def test_endian_mismatch_is_rejected(self):
        data = image(self.source)
        data[16 * 2048 + 84] ^= 1
        self.source.write_bytes(data)
        with self.assertRaisesRegex(ValueError, 'endian'):
            tool.inspect(self.source)

    def test_supplementary_view_is_not_silently_broken(self):
        data = image(self.source)
        data[17 * 2048:17 * 2048 + 7] = b'\x02CD001\x01'
        data[18 * 2048:18 * 2048 + 7] = b'\xffCD001\x01'
        self.source.write_bytes(data)
        with self.assertRaisesRegex(ValueError, 'Joliet'):
            tool.plan(self.source)

    def test_nonzero_directory_tail_is_protected(self):
        data = image(self.source)
        data[259 * 2048 + 2000] = 1
        self.source.write_bytes(data)
        with self.assertRaisesRegex(ValueError, 'tail'):
            tool.plan(self.source)

    def test_template_wrong_revision_is_rejected_before_copy(self):
        image(self.source)
        tool.normalized(self.source, self.output)
        template = self.root / 'template'
        for name in ('eboot.bin', 'ps2-emu-compiler.self', 'formatted.card', 'config-emu-ps4.txt', 'sce_sys/param.sfo'):
            target = template / name
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(b'NOT THE INSPECTED EMULATOR')
        with self.assertRaisesRegex(ValueError, 'revision'):
            tool.prepare(self.output, template, self.root / 'project', 'TEST00001', 'Test')
        self.assertFalse((self.root / 'project').exists())


class SFOTests(unittest.TestCase):
    def make_sfo(self):
        data = bytearray(64)
        struct.pack_into('<4s4I', data, 0, b'\0PSF', 0x101, 36, 48, 1)
        struct.pack_into('<HHIII', data, 20, 0, 0x0204, 4, 16, 0)
        data[36:42] = b'TITLE\0'
        data[48:52] = b'Old\0'
        return data

    def test_bounded_sfo_replacement(self):
        before = self.make_sfo()
        updated = tool.sfo_update(before, {'TITLE': 'New title'})
        self.assertEqual(len(updated), len(before))
        self.assertEqual(updated[48:58], b'New title\0')
        self.assertEqual(struct.unpack_from('<I', updated, 24)[0], 10)
        self.assertEqual(before[48:52], b'Old\0')

    def test_sfo_overflow_and_missing_fields_are_rejected(self):
        with self.assertRaises(ValueError):
            tool.sfo_update(self.make_sfo(), {'TITLE': 'X' * 30})
        with self.assertRaises(ValueError):
            tool.sfo_update(self.make_sfo(), {'TITLE_ID': 'TEST00001'})


class BuilderTests(unittest.TestCase):
    def test_builder_receives_output_directory_and_result_is_checked(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            project, builder, output = root / 'project.gp4', root / 'builder.exe', root / 'result.pkg'
            cid = 'UP9000-TEST00001_00-TEST000010000001'
            project.write_text('<psproject><volume><volume_type>pkg_ps4_app</volume_type><package content_id="' + cid + '"/></volume></psproject>')
            builder.write_bytes(b'USER TOOL')
            package = bytearray(256)
            package[:4] = b'\x7fCNT'
            package[0x40:0x40 + len(cid)] = cid.encode()

            def fake_run(command, **kwargs):
                self.assertEqual(command[1:5], ['img_create', '--oformat', 'pkg', '--no_progress_bar'])
                self.assertTrue(Path(command[-1]).is_dir())
                (Path(command[-1]) / 'sdk-generated-name.pkg').write_bytes(package)

            with patch.object(tool.subprocess, 'run', side_effect=fake_run):
                result = tool.build_pkg(project, builder, output)
            self.assertEqual(output.read_bytes(), package)
            self.assertEqual(result['sha256'], hashlib.sha256(package).hexdigest())
            with self.assertRaises(FileExistsError):
                tool.build_pkg(project, builder, output)

    def test_missing_builder_does_not_create_output(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            with self.assertRaises(ValueError):
                tool.build_pkg(root / 'missing.gp4', root / 'missing.exe', root / 'out.pkg')
            self.assertFalse((root / 'out.pkg').exists())


if __name__ == '__main__':
    unittest.main()
