import io
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from urllib.error import HTTPError
from _bootstrap import load_plugin_package
load_plugin_package()
from fast_rh_test_package import resources as r

class ResourceTests(unittest.TestCase):
    def test_three_sources(self):
        for source, expected in [('public', True), ('uploaded', False)]:
            endpoint, body = r.build_query(source, 2, '测试')
            self.assertEqual(endpoint, '/api/resource/list')
            self.assertIs(body['systemResource'], expected)
            self.assertTrue(body['choiceModel'])
            self.assertEqual((body['current'], body['resourceName']), (2, '测试'))
        endpoint, body = r.build_query('favorites', 1, '')
        self.assertEqual(endpoint, '/api/likeOrCollect/resource/list')
        self.assertEqual(body['operateType'], 2)
        self.assertNotIn('systemResource', body)
        with self.assertRaises(r.ResourceError):
            r.build_query('wrong', 1, '')

    def test_versions_keep_real_storage_name_and_subfolders(self):
        result = r.normalize_record({'resourceName': None, 'versions': [
            {'resourceStorageName': 'models/loras/sub/真实.safetensors', 'versionResourceName': 'display.safetensors', 'version': 'V1'},
            {'versionResourceName': 'models/loras/v2.safetensors', 'version': 'V2'},
            {'version': 'unavailable'}]})
        self.assertEqual(result['title'], 'sub/真实.safetensors')
        self.assertEqual([v['model'] for v in result['versions']], ['sub/真实.safetensors', 'v2.safetensors'])
        self.assertEqual(r.normalize_record({'versions': None})['versions'], [])

    def test_only_access_token_is_saved(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'session.json'
            r.save_session('https://www.runninghub.ai', 'x=y; Rh-Accesstoken=abc.def.ghi; Rh-Refreshtoken=SECRET', path)
            self.assertEqual(r.load_session(path)['access_token'], 'abc.def.ghi')
            self.assertNotIn('SECRET', path.read_text())
            with self.assertRaises(r.ResourceError):
                r.save_session('https://evil.example', 'abc.def.ghi', path)
            with self.assertRaises(r.ResourceError):
                r.save_session('https://www.runninghub.ai', 'bad\r\nheader', path)
            self.assertEqual(r.load_session(path)['access_token'], 'abc.def.ghi')

    @patch.object(r, 'load_session', return_value={'site': 'https://www.runninghub.ai', 'access_token': 'abc.def.ghi'})
    def test_request_and_pagination(self, _session):
        payload = {'code': 0, 'data': {'records': [], 'total': '31', 'hasNext': True}}
        with patch.object(r, 'urlopen', return_value=io.BytesIO(json.dumps(payload).encode())) as fetch:
            result = r.list_resources('favorites', 1, '中文', refresh=True)
        self.assertEqual(result['total'], 31)
        self.assertTrue(result['has_next'])
        request = fetch.call_args.args[0]
        self.assertEqual(request.get_header('Authorization'), 'Bearer abc.def.ghi')
        self.assertEqual(json.loads(request.data)['resourceName'], '中文')

    @patch.object(r, 'load_session', return_value={'site': 'https://www.runninghub.ai', 'access_token': 'abc.def.ghi'})
    def test_expired_and_invalid_responses(self, _session):
        with patch.object(r, 'urlopen', side_effect=HTTPError('url', 401, 'secret', {}, None)):
            with self.assertRaisesRegex(r.ResourceError, 'Login has expired'):
                r.list_resources('public', 1, '')
        for payload in [{'code': 401, 'msg': 'secret'}, {'code': 0, 'data': None}]:
            with patch.object(r, 'urlopen', return_value=io.BytesIO(json.dumps(payload).encode())):
                with self.assertRaises(r.ResourceError) as caught:
                    r.list_resources('public', 1, '')
                self.assertNotIn('secret', str(caught.exception))
