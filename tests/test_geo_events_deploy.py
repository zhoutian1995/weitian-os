import io
import json
import contextlib
import hashlib
import ast
import os
import tempfile
import stat
from unittest import mock
import importlib.util
from pathlib import Path
import unittest


class GeoReleaseMetadataTests(unittest.TestCase):
    def metadata(self, base, local):
        source = Path(__file__).parents[1] / 'scripts/deploy_geo_events.py'
        spec = importlib.util.spec_from_file_location('geo_deploy_metadata_test', source)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        remote = ast.parse(module.REMOTE)
        function = next(node for node in remote.body if isinstance(node, ast.FunctionDef) and node.name == 'release_metadata')
        context = {}
        exec(compile(ast.fix_missing_locations(ast.Module(body=[function], type_ignores=[])), str(source), 'exec'), context)
        return context['release_metadata'](base, local, 'new-release', '/srv/base', 'script-sha', '2026-10-24T00:00:00Z')

    def test_copied_remote_commit_is_not_replaced_with_local_head(self):
        base = {'gitSha': 'remote-actual', 'patches': {'existing': 'preserved'}}
        result = self.metadata(base, 'local-different')
        self.assertEqual(result['gitSha'], 'remote-actual')
        self.assertEqual(result['patch_source_git_sha'], 'local-different')
        self.assertEqual(result['patches']['existing'], 'preserved')
        self.assertEqual(base['patches'], {'existing': 'preserved'})

    def test_unknown_base_commit_remains_unknown(self):
        result = self.metadata({}, 'local-head')
        self.assertIsNone(result['gitSha'])
        self.assertEqual(result['patch_source_git_sha'], 'local-head')


class GeoAtomicConfigurationTests(unittest.TestCase):
    def helpers(self):
        spec = importlib.util.spec_from_file_location('geo_deploy_atomic_test', Path(__file__).parents[1] / 'scripts/deploy_geo_events.py')
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        tree = ast.parse(module.REMOTE)
        names = {'config_bytes', 'atomic_config', 'restore_config', 'validate_static_base'}
        nodes = [node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name in names]
        context = {'os': os, 'stat': stat, 'tempfile': tempfile, 'Path': Path, 'hashlib': hashlib}
        exec(compile(ast.fix_missing_locations(ast.Module(body=nodes, type_ignores=[])), str(spec.origin), 'exec'), context)
        return context

    def test_original_static_files_need_exact_prepared_base_and_missing_paths(self):
        helper = self.helpers()
        with tempfile.TemporaryDirectory() as folder:
            base = Path(folder)
            (base / 'sitemap.xml').write_bytes(b'old-sitemap')
            files = {'sitemap.xml': {}, 'learn/index.html': {}}
            expected = {'sitemap.xml': hashlib.sha256(b'old-sitemap').hexdigest(), 'learn/index.html': None}
            helper['validate_static_base'](base, files, expected)
            (base / 'sitemap.xml').write_bytes(b'another owner changed this')
            with self.assertRaisesRegex(RuntimeError, 'changed since'):
                helper['validate_static_base'](base, files, expected)
            with self.assertRaisesRegex(ValueError, 'exact patch'):
                helper['validate_static_base'](base, files, {})

    def test_atomic_write_preserves_configuration_symlink_and_permissions(self):
        helper = self.helpers()
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            target = root / 'available.conf'
            target.write_bytes(b'old')
            target.chmod(0o640)
            enabled = root / 'enabled.conf'
            enabled.symlink_to(target.name)
            helper['atomic_config'](enabled, b'complete-new', b'old')
            self.assertTrue(enabled.is_symlink())
            self.assertEqual(os.readlink(enabled), target.name)
            self.assertEqual(target.read_bytes(), b'complete-new')
            self.assertEqual(stat.S_IMODE(target.stat().st_mode), 0o640)

    def test_partial_temporary_write_cannot_corrupt_active_config(self):
        helper = self.helpers()
        original = os.fdopen
        def partial(fd, mode):
            stream = original(fd, mode)
            class Writer:
                def __enter__(self): return self
                def __exit__(self, *args): stream.close()
                def write(self, value):
                    stream.write(value[:2])
                    stream.flush()
                    raise OSError('Simulated partial write')
            return Writer()
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'site.conf'
            path.write_bytes(b'old')
            with mock.patch.object(os, 'fdopen', side_effect=partial):
                with self.assertRaises(OSError):
                    helper['atomic_config'](path, b'new-configuration', b'old')
            self.assertEqual(path.read_bytes(), b'old')
            self.assertTrue(helper['restore_config'](path, b'old', b'new-configuration'))
            self.assertEqual(list(Path(directory).glob('.geo-events-*')), [])

    def test_concurrent_configuration_is_not_overwritten_during_rollback(self):
        helper = self.helpers()
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'site.conf'
            path.write_bytes(b'other-owner')
            self.assertFalse(helper['restore_config'](path, b'old', b'ours'))
            self.assertEqual(path.read_bytes(), b'other-owner')
            with self.assertRaisesRegex(RuntimeError, 'changed before'):
                helper['atomic_config'](path, b'ours', b'old')

    def test_new_target_rollback_preserves_original_dangling_symlink(self):
        helper = self.helpers()
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            target = root / 'target.conf'
            alias = root / 'enabled.conf'
            alias.symlink_to(target.name)
            helper['atomic_config'](alias, b'ours', None)
            self.assertTrue(helper['restore_config'](alias, None, b'ours'))
            self.assertTrue(alias.is_symlink())
            self.assertFalse(target.exists())

    def test_personal_and_company_use_actual_distinct_nginx_paths(self):
        spec = importlib.util.spec_from_file_location('geo_profiles_test', Path(__file__).parents[1] / 'scripts/deploy_geo_events.py')
        module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
        self.assertEqual(module.PROFILES['company']['site'], '/www/server/panel/vhost/nginx/willeai.cn.conf')
        self.assertEqual(module.PROFILES['company']['root'], '/srv/weiling-company')
        self.assertEqual(module.PROFILES['company']['lock'], '/srv/weiling-company/.static-deploy.lock')
        self.assertEqual(module.PROFILES['personal']['site'], '/etc/nginx/sites-enabled/willeai-landing')
        self.assertNotEqual(module.PROFILES['company']['host'], module.PROFILES['personal']['host'])

    def test_rollback_recovers_only_our_complete_replacement(self):
        helper = self.helpers()
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'site.conf'
            path.write_bytes(b'ours')
            self.assertTrue(helper['restore_config'](path, b'old', b'ours'))
            self.assertEqual(path.read_bytes(), b'old')
            fresh = Path(directory) / 'fresh.conf'
            fresh.write_bytes(b'ours')
            self.assertTrue(helper['restore_config'](fresh, None, b'ours'))
            self.assertFalse(fresh.exists())


class GeoRemoteDeploymentTests(unittest.TestCase):
    def simulate(self, fail_at=None, concurrent=False):
        spec = importlib.util.spec_from_file_location('geo_remote_test', Path(__file__).parents[1] / 'scripts/deploy_geo_events.py')
        module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            base = root / 'releases/base'; base.mkdir(parents=True)
            (base / 'index.html').write_text('original-page')
            current = root / 'current'; current.symlink_to(base)
            site, snippet, http = [root / name for name in ('site.conf', 'server.conf', 'http.conf')]
            original = ('server {\n    root ' + str(current) + ';\n    index index.html;\n}\n').encode()
            site.write_bytes(original); snippet.write_bytes(b'old-server'); http.write_bytes(b'old-http')
            profile = dict(root=str(root), lock=str(root / 'lock'), site=str(site), snippet=str(snippet), http=str(http), backup=str(root / 'backups'), nginx=['fake-nginx'])
            payload = dict(site='company', profile=profile, expected_release=str(base), script='new-script', script_sha256='abc123', patch_source_git_sha='local-dirty', server='new-server', http='new-http')
            calls = []
            def nginx(command, **kwargs):
                self.assertNotIn('capture_output', kwargs)
                self.assertEqual(kwargs.get('stdout'), __import__('subprocess').PIPE)
                self.assertEqual(kwargs.get('stderr'), __import__('subprocess').PIPE)
                calls.append(command)
                if concurrent:
                    other = root / 'releases/other'; other.mkdir(exist_ok=True)
                    current.unlink(); current.symlink_to(other)
                if len(calls) == fail_at: raise RuntimeError('Injected nginx failure')
            original_mkdir = Path.mkdir
            def mkdir(path, *args, **kwargs):
                if path == Path('/var/log/nginx'): return
                return original_mkdir(path, *args, **kwargs)
            with (mock.patch('sys.stdin', io.StringIO(json.dumps(payload))), mock.patch('subprocess.run', side_effect=nginx),
                  mock.patch.object(Path, 'mkdir', mkdir), contextlib.redirect_stdout(io.StringIO())):
                if fail_at or concurrent:
                    with self.assertRaises(RuntimeError): exec(module.REMOTE, {})
                else: exec(module.REMOTE, {})
            self.assertEqual((base / 'index.html').read_text(), 'original-page')
            if concurrent:
                self.assertEqual(current.resolve().name, 'other')
            elif fail_at:
                self.assertEqual(current.resolve(), base)
                self.assertEqual(site.read_bytes(), original)
                self.assertEqual(snippet.read_bytes(), b'old-server')
                self.assertEqual(http.read_bytes(), b'old-http')
            else:
                self.assertNotEqual(current.resolve(), base)
                self.assertEqual((current / 'assets/geo-events.js').read_text(), 'new-script')
                self.assertIn(str(snippet).encode(), site.read_bytes())
                self.assertEqual(calls, [['fake-nginx', '-t'], ['fake-nginx', '-s', 'reload']])

    def test_success_activates_only_the_new_release(self): self.simulate()
    def test_configuration_test_failure_rolls_back_our_files(self): self.simulate(fail_at=1)
    def test_reload_failure_rolls_back_pointer_and_configuration(self): self.simulate(fail_at=2)
    def test_other_owner_current_is_not_overwritten(self): self.simulate(concurrent=True)


if __name__ == '__main__':
    unittest.main()
