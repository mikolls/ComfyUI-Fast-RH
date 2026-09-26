import importlib
import json
import sys
import types
import unittest
from unittest.mock import AsyncMock, patch
from aiohttp import web
from _bootstrap import load_plugin_package
package = load_plugin_package()
fake_server = types.ModuleType('server')
fake_server.PromptServer = types.SimpleNamespace(instance=types.SimpleNamespace(routes=web.RouteTableDef()))
with patch.dict(sys.modules, {'server': fake_server}):
    routes = importlib.import_module(package + '.routes')

class RouteTests(unittest.IsolatedAsyncioTestCase):
    async def test_status_never_returns_token(self):
        with patch.object(routes, 'load_session', return_value={'site': 'https://www.runninghub.ai', 'access_token': 'SECRET'}):
            response = await routes.session_status(None)
        self.assertNotIn('SECRET', response.text)
        self.assertTrue(json.loads(response.text)['configured'])

    async def test_cross_origin_cannot_replace_login(self):
        request = types.SimpleNamespace(content_type='application/json', headers={'Origin': 'https://evil.example'}, scheme='http', host='localhost:8188')
        with patch.object(routes, 'save_session') as save:
            response = await routes.update_session(request)
        self.assertEqual(response.status, 403)
        save.assert_not_called()

    async def test_save_and_query(self):
        request = types.SimpleNamespace(content_type='application/json', headers={}, scheme='http', host='localhost:8188', json=AsyncMock(return_value={'site': 'https://www.runninghub.ai', 'credential': 'a.b.c'}))
        with patch.object(routes, 'save_session') as save:
            response = await routes.update_session(request)
            save.assert_called_once_with('https://www.runninghub.ai', 'a.b.c')
        self.assertEqual(response.status, 200)
        with patch.object(routes, 'list_resources', return_value={'items': [], 'page': 2, 'total': 0, 'has_next': False}) as fetch:
            response = await routes.get_resources(types.SimpleNamespace(query={'source': 'uploaded', 'page': '2', 'q': 'test'}))
            fetch.assert_called_once_with('uploaded', 2, 'test', False)
        self.assertTrue(json.loads(response.text)['ok'])
    async def test_cover_upload_uses_local_multipart_headers(self):
        model_field = types.SimpleNamespace(name='model', text=AsyncMock(return_value='face.safetensors'))
        image_field = types.SimpleNamespace(
            name='image',
            headers={'Content-Type': 'image/png'},
            read_chunk=AsyncMock(side_effect=[b'\x89PNG\r\n\x1a\nimage', b'']),
        )
        reader = types.SimpleNamespace(next=AsyncMock(side_effect=[model_field, image_field]))
        request = types.SimpleNamespace(
            content_type='multipart/form-data',
            headers={},
            multipart=AsyncMock(return_value=reader),
        )
        with patch.object(routes, 'save_model_cover', return_value='cover.png') as save:
            response = await routes.upload_model_cover(request)
        self.assertEqual(response.status, 200)
        self.assertTrue(json.loads(response.text)['ok'])
        self.assertEqual(save.call_args.args[1:], ('image/png', b'\x89PNG\r\n\x1a\nimage'))
