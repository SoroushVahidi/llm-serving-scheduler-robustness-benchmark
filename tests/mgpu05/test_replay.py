import asyncio
import json
import httpx
import pytest
from robustbench.mgpu05.replay import replay
from robustbench.mgpu05.evidence import Journal, read_journal
from robustbench.mgpu05.design import payload


@pytest.mark.parametrize('mode,expected',[('ok','STREAM_DONE'),('error','HTTP_ERROR'),
                                         ('eof','EOF_WITHOUT_DONE'),('timeout','TIMEOUT')])
def test_real_cpu_http_transport(tmp_path,mode,expected):
    """Actual loopback HTTP transport/SSE framing; no inference or GPU."""
    async def exercise():
        async def handle(reader,writer):
            try:
                head=await reader.readuntil(b'\r\n\r\n')
                n=int(next(l.split(b':',1)[1] for l in head.split(b'\r\n') if l.lower().startswith(b'content-length:')))
                body=json.loads(await reader.readexactly(n))
                assert body['request_id']=='fixture-balanced-00'
                if mode=='timeout':
                    await reader.read()  # ends when timeout closes client connection
                    return
                status=b'500 Error' if mode=='error' else b'200 OK'
                writer.write(b'HTTP/1.1 '+status+b'\r\nContent-Type: text/event-stream\r\nConnection: close\r\n\r\n')
                await writer.drain()
                if mode in ('ok','eof'):
                    # Fragment SSE across network writes, including UTF-8 and CRLF.
                    for fragment in [b'da',b'ta: {"text":"', 'é'.encode()[:1], 'é'.encode()[1:], b'"}\r\n\r\n']:
                        writer.write(fragment); await writer.drain(); await asyncio.sleep(0)
                if mode=='ok': writer.write(b'data: [DONE]\n\n')
                await writer.drain()
            finally:
                writer.close(); await writer.wait_closed()
        server=await asyncio.start_server(handle,'127.0.0.1',0)
        port=server.sockets[0].getsockname()[1]
        journal=Journal(tmp_path/'client.jsonl',synthetic=True)
        try:
            async with server, httpx.AsyncClient(base_url=f'http://127.0.0.1:{port}',trust_env=False) as client:
                await replay([payload('balanced',0,'spread')],client=client,journal=journal,
                             provenance='synthetic_test',timeout_s=.05,start_delay_s=.001)
        finally:
            journal.close()
    asyncio.run(exercise())
    rows=read_journal(tmp_path/'client.jsonl')
    assert [e['data']['state'] for e in rows if e['kind']=='terminal']==[expected]
    assert len([e for e in rows if e['kind']=='transport_send'])==1
    if mode=='ok':
        assert [e['data']['value'] for e in rows if e['kind']=='sse']==['{"text":"é"}','[DONE]']
    assert rows[0]['data']['provenance']=='synthetic_test' and rows[-1]['kind']=='run_end'


def test_cancellation_and_client_saturation_durable(tmp_path):
    async def exercise():
        entered=asyncio.Event()
        async def handler(request):
            entered.set()
            await asyncio.Event().wait()
        j=Journal(tmp_path/'client.jsonl',synthetic=True)
        inputs=[payload('balanced',i,'burst') for i in range(2)]
        try:
            async with httpx.AsyncClient(base_url='http://test',transport=httpx.MockTransport(handler)) as client:
                task=asyncio.create_task(replay(inputs,client=client,journal=j,provenance='synthetic_test',
                                                start_delay_s=0,max_inflight=1))
                await entered.wait(); await asyncio.sleep(0); task.cancel()
                with pytest.raises(asyncio.CancelledError): await task
        finally: j.close()
    asyncio.run(exercise())
    rows=read_journal(tmp_path/'client.jsonl')
    assert sorted(e['data']['state'] for e in rows if e['kind']=='terminal')==['CANCELLED','CLIENT_SATURATED']
    assert rows[-1]['data']['state']=='ABORTED'


def test_fake_clock_cannot_be_physical():
    with pytest.raises(ValueError,match='actual monotonic'):
        asyncio.run(replay([],client=None,journal=None,clock=lambda:1.))
