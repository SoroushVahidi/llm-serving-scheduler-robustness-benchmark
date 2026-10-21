"""Physical open-loop collector; interpretation lives in the separate validator."""
import asyncio
import json
import time

from .evidence import clock_domain


async def replay(payloads, *, client, journal, provenance='physical_candidate',
                 timeout_s=120., max_inflight=32, clock=time.monotonic,
                 start_delay_s=.1, domain=None):
    if provenance not in ('physical_candidate', 'synthetic_test'):
        raise ValueError('Unknown timing provenance')
    if provenance == 'physical_candidate' and clock is not time.monotonic:
        raise ValueError('Physical collector requires the actual monotonic clock')
    ids = [p['request_id'] for p in payloads]
    if not payloads or len(ids) != len(set(ids)) or max_inflight < 1 or timeout_s <= 0:
        raise ValueError('Invalid replay configuration')
    encoded = [json.dumps(p, sort_keys=True, separators=(',', ':')).encode() for p in payloads]
    epoch = clock() + start_delay_s
    journal.event('run_start', epoch_s=epoch, clock_domain=domain or clock_domain(),
                  provenance=provenance, requests=ids, timeout_s=timeout_s)
    inflight = 0

    async def send(payload, body):
        nonlocal inflight
        rid = payload['request_id']
        arrival = payload['vllm_xargs']['lssp_arrival_s']
        entered = False
        try:
            await asyncio.sleep(max(0., epoch + arrival - clock()))
            if inflight >= max_inflight:
                journal.event('terminal', request_id=rid, state='CLIENT_SATURATED')
                return
            inflight += 1
            entered = True
            traced = False

            async def trace(name, info):
                nonlocal traced
                if name.endswith('send_request_headers.started') and not traced:
                    journal.event('transport_send', request_id=rid)
                    traced = True

            journal.event('dispatch', request_id=rid)
            async with asyncio.timeout(timeout_s):
                async with client.stream('POST', '/v1/completions', content=body,
                                         headers={'Content-Type': 'application/json'},
                                         extensions={'trace': trace}) as response:
                    journal.event('http', request_id=rid, status=response.status_code)
                    if response.status_code != 200:
                        journal.event('terminal', request_id=rid, state='HTTP_ERROR',
                                      status=response.status_code)
                        return
                    data, captured = [], 0
                    async for line in response.aiter_lines():
                        captured += len(line.encode('utf-8'))
                        if captured > 8 * 1024 * 1024:
                            raise ValueError('Synthetic response capture exceeds bounded size')
                        if line.startswith('data:'):
                            data.append(line[5:].removeprefix(' '))
                        elif not line and data:
                            value = '\n'.join(data)
                            journal.event('sse', request_id=rid, value=value,
                                          timestamp_kind='client_stream_event_observation')
                            data = []
                            if value.strip() == '[DONE]':
                                journal.event('terminal', request_id=rid, state='STREAM_DONE')
                                return
                    if data:
                        journal.event('unterminated_sse', request_id=rid, value='\n'.join(data))
                    journal.event('terminal', request_id=rid, state='EOF_WITHOUT_DONE')
        except asyncio.CancelledError:
            journal.event('terminal', request_id=rid, state='CANCELLED')
            raise
        except TimeoutError:
            journal.event('terminal', request_id=rid, state='TIMEOUT')
        except Exception as exc:
            journal.event('terminal', request_id=rid, state='ERROR', error_type=type(exc).__name__,
                          error=str(exc))
        finally:
            if entered:
                inflight -= 1

    tasks = [asyncio.create_task(send(p, body)) for p, body in zip(payloads, encoded)]
    state = 'FINISHED'
    try:
        await asyncio.gather(*tasks)
    except BaseException:
        state = 'ABORTED'
        for task in tasks:
            task.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)
        raise
    finally:
        journal.event('run_end', state=state)
