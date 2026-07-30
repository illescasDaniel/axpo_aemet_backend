import asyncio

import pytest

from meteo_service.shared.single_flight import SingleFlight


pytestmark = pytest.mark.unit


async def test_given_concurrent_same_key_when_do_then_factory_runs_once():
    # given
    single_flight = SingleFlight[int]()
    calls = 0
    started = asyncio.Event()
    release = asyncio.Event()

    async def factory():
        nonlocal calls
        calls += 1
        started.set()
        await release.wait()
        return 42

    # when
    task_a = asyncio.create_task(single_flight.do("key", factory))
    await started.wait()
    task_b = asyncio.create_task(single_flight.do("key", factory))
    release.set()
    result_a, result_b = await asyncio.gather(task_a, task_b)

    # then
    assert calls == 1
    assert result_a == 42
    assert result_b == 42


async def test_given_different_keys_when_do_then_factory_runs_per_key():
    # given
    single_flight = SingleFlight[str]()
    calls = 0
    started_a = asyncio.Event()
    started_b = asyncio.Event()
    release = asyncio.Event()

    async def factory_a():
        nonlocal calls
        calls += 1
        started_a.set()
        await release.wait()
        return "a"

    async def factory_b():
        nonlocal calls
        calls += 1
        started_b.set()
        await release.wait()
        return "b"

    # when
    task_a = asyncio.create_task(single_flight.do("key-a", factory_a))
    task_b = asyncio.create_task(single_flight.do("key-b", factory_b))
    await asyncio.gather(started_a.wait(), started_b.wait())
    release.set()
    result_a, result_b = await asyncio.gather(task_a, task_b)

    # then
    assert calls == 2
    assert result_a == "a"
    assert result_b == "b"


async def test_given_one_waiter_cancelled_when_other_waits_then_shared_work_completes():
    # given
    single_flight = SingleFlight[int]()
    calls = 0
    started = asyncio.Event()
    release = asyncio.Event()

    async def factory():
        nonlocal calls
        calls += 1
        started.set()
        await release.wait()
        return 7

    task_a = asyncio.create_task(single_flight.do("key", factory))
    await started.wait()
    task_b = asyncio.create_task(single_flight.do("key", factory))

    # when
    task_a.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task_a
    release.set()
    result_b = await task_b

    # then
    assert task_a.cancelled()
    assert result_b == 7
    assert calls == 1


async def test_given_factory_raises_when_concurrent_waiters_then_all_see_error():
    # given
    single_flight = SingleFlight[int]()
    calls = 0
    started = asyncio.Event()
    release = asyncio.Event()

    async def factory():
        nonlocal calls
        calls += 1
        started.set()
        await release.wait()
        raise RuntimeError("boom")

    task_a = asyncio.create_task(single_flight.do("key", factory))
    await started.wait()
    task_b = asyncio.create_task(single_flight.do("key", factory))

    # when
    release.set()
    results = await asyncio.gather(task_a, task_b, return_exceptions=True)

    # then
    assert calls == 1
    assert all(isinstance(result, RuntimeError) and str(result) == "boom" for result in results)


async def test_given_completed_inflight_when_same_key_called_again_then_factory_runs_again():
    # given
    single_flight = SingleFlight[int]()
    calls = 0

    async def factory():
        nonlocal calls
        calls += 1
        return calls

    # when
    first = await single_flight.do("key", factory)
    second = await single_flight.do("key", factory)

    # then
    assert first == 1
    assert second == 2
    assert calls == 2
