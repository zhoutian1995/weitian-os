import ast
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


if __name__ == '__main__':
    unittest.main()
