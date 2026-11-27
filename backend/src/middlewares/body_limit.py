from fastapi.responses import JSONResponse

MAX_BYTES = 3_800_000


class BodyLimit:
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope['type'] != 'http' or scope['method'] not in ('POST', 'PUT', 'PATCH'):
            return await self.app(scope, receive, send)
        parts = []
        count = 0
        while True:
            message = await receive()
            if message['type'] != 'http.request':
                return
            body = message.get('body', b'')
            count += len(body)
            if count > MAX_BYTES:
                response = JSONResponse({'detail': '提交内容过大'}, status_code=413)
                return await response(scope, receive, send)
            parts.append(body)
            if not message.get('more_body'):
                break
        delivered = False

        async def read_body():
            nonlocal delivered
            if delivered:
                return await receive()
            delivered = True
            return {'type': 'http.request', 'body': b''.join(parts), 'more_body': False}

        await self.app(scope, read_body, send)
