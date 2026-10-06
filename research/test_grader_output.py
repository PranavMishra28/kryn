"""Transport-only checks for the child grader's Docker exec output cap."""

import json
import io
from pathlib import Path
import struct
from types import SimpleNamespace
import tempfile
import threading
import unittest
from unittest.mock import patch

from research.container_grader import (BoundedExecStream, ExecOutputBudgetExceeded,
                                       SOCKET_READ_LIMIT, install_exec_output_budget,
                                       reject_output_breach)


class Source:
    def __init__(self, *parts):
        self.parts = iter(parts)
        self.closed = False
        self._response = SimpleNamespace(closed=False)
        self._response.close = lambda: setattr(self._response, "closed", True)

    def __iter__(self):
        return self

    def __next__(self):
        return next(self.parts)

    def close(self):
        self.closed = True


class API:
    def __init__(self, *sources):
        self.sources = iter(sources)
        self.calls = []

    def exec_start(self, exec_id, **kwargs):
        self.calls.append((exec_id, kwargs))
        return b"" if kwargs.get("detach") else next(self.sources)


class GraderOutputTest(unittest.TestCase):
    def install(self, sources, receipt):
        api = API(*sources)
        requests = []
        socket_module = SimpleNamespace(read=lambda _sock, n=4096: requests.append(n) or n)
        install_exec_output_budget(SimpleNamespace(api=api), receipt, socket_module=socket_module)
        return api, socket_module, requests

    def test_nonstream_and_stream_bytes_are_preserved_and_closed(self):
        with tempfile.TemporaryDirectory() as folder:
            one, two = Source(b"ab", bytearray(b"cd")), Source(memoryview(b"e"), b"f")
            receipt = Path(folder) / "output-budget.json"
            api, _, _ = self.install((one, two), receipt)
            self.assertEqual(api.exec_start("one"), b"abcd")
            self.assertEqual(list(api.exec_start("two", stream=True)), [b"e", b"f"])
            self.assertTrue(all(x.closed and x._response.closed for x in (one, two)))
            self.assertEqual([call[1] for call in api.calls], [{"stream": True}, {"stream": True}])
            self.assertFalse(receipt.exists())

    def test_exact_limit_allowed_but_aggregate_and_single_chunk_overflow_fail(self):
        with tempfile.TemporaryDirectory() as folder, patch("research.container_grader.EXEC_OUTPUT_LIMIT", 4):
            receipt = Path(folder) / "output-budget.json"
            exact, aggregate, single = Source(b"abcd"), Source(b"abc", b"de"), Source(b"abcde")
            api, _, _ = self.install((exact, aggregate, single), receipt)
            self.assertEqual(api.exec_start("exact"), b"abcd")
            self.assertFalse(receipt.exists())
            with self.assertRaises(ExecOutputBudgetExceeded):
                list(api.exec_start("aggregate", stream=True))
            self.assertEqual(json.loads(receipt.read_text())["observed_bytes"], 5)
            with self.assertRaises(ExecOutputBudgetExceeded):
                api.exec_start("single")
            self.assertTrue(all(x.closed and x._response.closed for x in (exact, aggregate, single)))
            with self.assertRaises(ExecOutputBudgetExceeded):
                reject_output_breach(folder)

    def test_invalid_or_failed_source_closes_before_propagation(self):
        class Broken(Source):
            def __next__(self):
                raise OSError("transport failed")

        with tempfile.TemporaryDirectory() as folder:
            bad_type, broken = Source("text"), Broken()
            api, _, _ = self.install((bad_type, broken), Path(folder) / "output-budget.json")
            with self.assertRaises(TypeError):
                api.exec_start("bad-type")
            with self.assertRaisesRegex(OSError, "transport failed"):
                api.exec_start("broken", stream=True).__next__()
            self.assertTrue(all(x.closed and x._response.closed for x in (bad_type, broken)))

    def test_sdk_stream_cannot_hide_a_socket_error_as_eof(self):
        class Swallowing(Source):
            def __init__(self):
                super().__init__()
                self._stream = iter(Broken())

            def __next__(self):
                try:
                    return next(self._stream)
                except OSError:
                    raise StopIteration from None

        class Broken:
            def __iter__(self):
                return self

            def __next__(self):
                raise OSError("socket broke")

        with tempfile.TemporaryDirectory() as folder:
            source = Swallowing()
            stream = BoundedExecStream(source, Path(folder) / "output-budget.json")
            with self.assertRaisesRegex(OSError, "socket broke"):
                next(stream)
            self.assertTrue(source.closed and source._response.closed)

    def test_unsupported_modes_fail_closed_and_detach_passes_through(self):
        with tempfile.TemporaryDirectory() as folder:
            api, socket_module, requests = self.install((), Path(folder) / "output-budget.json")
            for option in ("tty", "socket", "demux"):
                with self.assertRaises(RuntimeError):
                    api.exec_start("unsupported", **{option: True})
            with self.assertRaises(RuntimeError):
                api.exec_start("unsupported", detach=True, stream=True)
            self.assertEqual(api.exec_start("kill", detach=True), b"")
            self.assertEqual(api.calls, [("kill", {"detach": True})])
            self.assertEqual(socket_module.read(None, 10**9), SOCKET_READ_LIMIT)
            self.assertEqual(socket_module.read(None), 4096)
            self.assertEqual(requests, [SOCKET_READ_LIMIT, 4096])

    def test_timeout_style_close_unblocks_and_discards_late_bytes(self):
        class Blocking(Source):
            def __init__(self):
                super().__init__()
                self.started = threading.Event()
                self.release = threading.Event()

            def __next__(self):
                self.started.set()
                self.release.wait(2)
                return b"late"

            def close(self):
                super().close()
                self.release.set()

        with tempfile.TemporaryDirectory() as folder:
            source = Blocking()
            stream = BoundedExecStream(source, Path(folder) / "output-budget.json")
            observed = []
            worker = threading.Thread(target=lambda: observed.extend(list(stream)))
            worker.start()
            self.assertTrue(source.started.wait(1))
            stream.close()
            worker.join(2)
            self.assertFalse(worker.is_alive())
            self.assertEqual(observed, [])
            self.assertTrue(source.closed and source._response.closed)

    def test_pinned_sdk_multiplexed_frames_use_bounded_raw_reads(self):
        try:
            from docker.utils import socket as sdk_socket
        except ImportError:
            self.skipTest("Docker SDK is installed only in the evaluator venv")
        payload = b"x" * 100000
        frame = io.BytesIO(struct.pack(">BxxxL", 1, len(payload)) + payload)
        requests = []

        def raw_read(stream, n=4096):
            requests.append(n)
            return stream.read(n)

        with tempfile.TemporaryDirectory() as folder, patch.object(sdk_socket, "read", raw_read):
            install_exec_output_budget(SimpleNamespace(api=API()), Path(folder) / "output-budget.json",
                                       socket_module=sdk_socket)
            chunks = list(sdk_socket.frames_iter_no_tty(frame))
        self.assertEqual(b"".join(chunk for _, chunk in chunks), payload)
        self.assertLessEqual(max(requests), SOCKET_READ_LIMIT)


if __name__ == "__main__":
    unittest.main()
