import importlib
import sys
import types
import unittest
from unittest.mock import Mock

class SettingsPlugin:
    def on_settings_save(self, data):
        self.saved = data

host = types.ModuleType('octoprint')
host.plugin = types.ModuleType('octoprint.plugin')
host.plugin.SettingsPlugin = SettingsPlugin
host.plugin.TemplatePlugin = type('TemplatePlugin', (), {})
host.plugin.AssetPlugin = type('AssetPlugin', (), {})
sys.modules['octoprint'] = host
sys.modules['octoprint.plugin'] = host.plugin
plugin = importlib.import_module('octoprint_prusaxltoolfix')
rewrite = plugin.rewrite_command

class RewriteTests(unittest.TestCase):
    def test_rewrites(self):
        cases = {
            'M201 X7000 Y7000 Z200 E2500': 'M201 T0 X7000 Y7000 Z200 E2500',
            'M203 X400 Y400 Z12 E100': 'M203 T0 X400 Y400 Z12 E100',
            'M201': 'M201 T0',
            'M221 S100': 'M221 T0 S100',
            'm221s95': 'm221 T0 s95',
            'M221 S100 ; T0 comment': 'M221 T0 S100 ; T0 comment',
            'm203x400y400': 'm203 T0 x400y400',
            '\tM201  X2\t ; T0 comment': '\tM201 T0  X2\t ; T0 comment',
            'M203(T0 ignored) X2': 'M203 T0 (T0 ignored) X2',
            'M201 X2 (nested (T3) comment)': 'M201 T0 X2 (nested (T3) comment)',
            'M203;comment': 'M203 T0 ;comment',
        }
        for original, expected in cases.items():
            with self.subTest(original=original):
                self.assertEqual(rewrite(original), expected)
                self.assertEqual(rewrite(expected), expected)
        self.assertEqual(rewrite('M201 X2', 4), 'M201 T4 X2')

    def test_unchanged(self):
        for cmd in ['T0 S1 L0 D0', 'T4', 'M204 P4000 R1200 T5000',
                    'M221 T0 S100', 'M221 S95 T2', 'M221S100T0',
                    'M2210 S100', 'M221.1 S100', 'M205 S0 T0', 'M201 T0 X2', 'M203 T0 X2',
                    'M201 T2 X2', 'M203X2T0', 'M201 t-1', 'M203 T',
                    'M201 T1.5', 'M2010 X2', 'M201.1 X2', '; M201 X2',
                    'M117 M201 X2', 'N12 M201 X2*12', 'M201 X2*43',
                    'M203 "T2"', 'M201 (bad', 'M201 )', 'M201 X2\nT0',
                    'G1 X2', '', 'M203 X2 (bad;comment']:
            with self.subTest(cmd=cmd):
                self.assertEqual(rewrite(cmd), cmd)

    def test_fan_commands(self):
        for original, expected in {
            'M107': 'M107 T0',
            'M106': 'M106 T0',
            'M106 S0': 'M106 T0 S0',
            'M106 P1 S128': 'M106 T0 P1 S128',
            'm106s0': 'm106 T0 s0',
            'M107 ; T0 comment': 'M107 T0 ; T0 comment',
            'M106 (T2 comment) S0': 'M106 T0 (T2 comment) S0',
        }.items():
            with self.subTest(original=original):
                self.assertEqual(rewrite(original), expected)
                self.assertEqual(rewrite(expected), expected)
        for original in ['M107 T0', 'M106 S0 T2', 'M106S0T0', 'M107 T',
                         'M1060 S0', 'M107.1', 'N126 M107*32',
                         'N137 M106 S0*98', 'M106 S0*98', 'M105', 'M108']:
            with self.subTest(original=original):
                self.assertEqual(rewrite(original), original)

    def test_invalid_tool(self):
        for value in [True, -1, 5, 0.5, '0 T1', None, '']:
            with self.subTest(value=value), self.assertRaises(ValueError):
                rewrite('M201', value)

    def test_printer_ids(self):
        self.assertEqual(plugin.printer_ids([]), [])
        self.assertEqual(plugin.printer_ids(['*']), ['*'])
        self.assertEqual(plugin.printer_ids(['xl', '*', 'mk4']), ['*'])
        self.assertEqual(plugin.printer_ids([' xl ', 'mk4', 'xl']), ['xl', 'mk4'])
        for value in ['xl', None, [1], [''], ['a/b'], ['a\\b'], ['a\nb']]:
            with self.subTest(value=value), self.assertRaises(ValueError):
                plugin.printer_ids(value)

class _ProfileManager:
    def __init__(self, printer_id, profiles=None):
        self.printer_id = printer_id
        self.profiles = profiles

    def get_current_or_default(self):
        if self.printer_id is None:
            return None
        return {'id': self.printer_id, 'name': 'Printer'}

    def get_all(self):
        if self.profiles is not None:
            return self.profiles
        if self.printer_id is None:
            return {}
        return {self.printer_id: {'id': self.printer_id, 'name': 'Printer'}}


class _Comm:
    def __init__(self, printer_id):
        self._printerProfileManager = _ProfileManager(printer_id)


class HookTests(unittest.TestCase):
    def setUp(self):
        plugin.__plugin_load__()
        self.p = plugin.__plugin_implementation__
        self.tool_index = 0
        self.printers = ['xl']
        self.p._settings = Mock()
        self.p._settings.get.side_effect = self._settings_get
        self.p._logger = Mock()
        self.p._printer_profile_manager = None
        self.hook = plugin.__plugin_hooks__['octoprint.comm.protocol.gcode.queuing']
        self.comm = _Comm('xl')

    def _settings_get(self, path):
        if path == ['tool_index']:
            return self.tool_index
        if path == ['printers']:
            return list(self.printers)
        raise AssertionError(path)

    def test_contract_and_logging(self):
        tags = {'source:file'}
        self.assertEqual(self.hook(self.comm, 'queuing', 'M201 X2', 'type', 'M201',
                                   None, tags, future=True), ('M201 T0 X2',))
        self.assertEqual(tags, {'source:file'})
        self.p._logger.info.assert_called_once()

    def test_m221_hook(self):
        self.assertEqual(self.hook(self.comm, 'queuing', 'M221 S95', None, 'M221'),
                         ('M221 T0 S95',))
        self.assertIsNone(self.hook(self.comm, 'queuing', 'M221 T0 S95', None, 'M221'))
        self.assertIsNone(self.hook(self.comm, 'queuing', 'M221 T2 S95', None, 'M221'))
        self.tool_index = 3
        self.assertEqual(self.hook(self.comm, 'queuing', 'M221 S95', None, 'M221'),
                         ('M221 T3 S95',))

    def test_fan_hooks(self):
        for code, command in [('M106', 'M106 S0'), ('M107', 'M107')]:
            with self.subTest(code=code):
                self.tool_index = 0
                expected = command.replace(code, code + ' T0', 1)
                self.assertEqual(self.hook(self.comm, 'queuing', command, None, code), (expected,))
                self.assertIsNone(self.hook(self.comm, 'queuing', expected, None, code))
                self.tool_index = 2
                self.assertEqual(self.hook(self.comm, 'queuing', command, None, code),
                                 (command.replace(code, code + ' T2', 1),))

    def test_selected_printers_only(self):
        self.assertIsNone(self.hook(_Comm('mk4'), 'queuing', 'M201 X2', None, 'M201'))
        self.printers = []
        self.assertIsNone(self.hook(self.comm, 'queuing', 'M201 X2', None, 'M201'))
        self.printers = ['xl', 'mk4']
        self.assertEqual(self.hook(_Comm('mk4'), 'queuing', 'M201 X2', None, 'M201'),
                         ('M201 T0 X2',))
        self.assertIsNone(self.hook(_Comm(None), 'queuing', 'M201 X2', None, 'M201'))
        self.p._printer_profile_manager = _ProfileManager('xl')
        self.assertEqual(self.hook(object(), 'queuing', 'M201 X2', None, 'M201'),
                         ('M201 T0 X2',))
        self.printers = 'xl'
        self.assertIsNone(self.hook(self.comm, 'queuing', 'M201 X2', None, 'M201'))
        self.printers = ['*']
        self.assertEqual(self.hook(_Comm('mk4'), 'queuing', 'M201 X2', None, 'M201'),
                         ('M201 T0 X2',))
        self.assertEqual(self.hook(_Comm(None), 'queuing', 'M201 X2', None, 'M201'),
                         ('M201 T0 X2',))
        self.p._logger.info.assert_called()

    def test_guards(self):
        for phase, cmd, code, sub in [('sending', 'M201', 'M201', None),
                                     ('queuing', 'T0', 'T0', None),
                                     ('queuing', 'M201', None, None),
                                     ('queuing', 'M201.1', 'M201', '1'),
                                     ('queuing', 'M201 T0', 'M201', None)]:
            self.assertIsNone(self.hook(self.comm, phase, cmd, None, code, sub))
        self.tool_index = 'invalid'
        self.assertIsNone(self.hook(self.comm, 'queuing', 'M201', None, 'M201'))
        self.p._logger.info.assert_not_called()

    def test_settings(self):
        self.assertEqual(self.p.get_settings_defaults(), {'tool_index': 0, 'printers': ['*']})
        self.assertEqual(self.p.get_template_configs(),
                         [{'type': 'settings', 'custom_bindings': True}])
        self.p.on_settings_save({'tool_index': '3', 'printers': ['xl', 'xl']})
        self.assertEqual(self.p.saved, {'tool_index': 3, 'printers': ['xl']})
        self.p.on_settings_save({'printers': ['mk4']})
        self.assertEqual(self.p.saved, {'printers': ['mk4']})
        for data in [{'tool_index': 9}, {'printers': 'xl'}, {'printers': ['']}]:
            with self.assertRaises(ValueError):
                self.p.on_settings_save(data)

    def test_update_information(self):
        self.p._plugin_version = '1.0.0.post7'
        self.assertEqual(
            plugin.__plugin_hooks__['octoprint.plugin.softwareupdate.check_config'],
            self.p.get_update_information,
        )
        info = self.p.get_update_information()['prusaxltoolfix']
        self.assertEqual(info['type'], 'github_release')
        self.assertEqual((info['user'], info['repo']), ('anuzellig', 'octoprint-prusa-xl-fix'))
        self.assertEqual(info['current'], '1.0.0.post7')
        self.assertEqual(
            info['pip'].format(target_version='1.0.0.post8'),
            'https://github.com/anuzellig/octoprint-prusa-xl-fix/releases/download/'
            '1.0.0.post8/octoprint_prusaxltoolfix-1.0.0.post8.tar.gz',
        )

    def test_profile_list(self):
        self.assertEqual(
            self.p.get_template_vars(),
            {'profiles': [], 'profiles_json': '[]'},
        )
        self.p._printer_profile_manager = _ProfileManager(
            None,
            {
                'mk4': {'id': 'mk4', 'name': 'MK4'},
                'xl': {'id': 'xl', 'name': 'Prusa XL'},
                'bad': {'name': 'Missing id'},
                'blank': {'id': '  ', 'name': 'Blank'},
            },
        )
        self.assertEqual(
            self.p.get_template_vars(),
            {
                'profiles': [{'id': 'mk4', 'name': 'MK4'},
                             {'id': 'xl', 'name': 'Prusa XL'}],
                'profiles_json': '[{"id":"mk4","name":"MK4"},{"id":"xl","name":"Prusa XL"}]',
            },
        )

if __name__ == '__main__':
    unittest.main()
