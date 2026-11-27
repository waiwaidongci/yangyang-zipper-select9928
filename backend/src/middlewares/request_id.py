from uuid import uuid4


async def request_id(request, call_next):
    response = await call_next(request)
    response.headers['X-Request-ID'] = str(uuid4())
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['Cache-Control'] = 'no-store'
    return response
