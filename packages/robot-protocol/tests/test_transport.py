import json
import struct
import unittest

from robot_protocol.transport import (
    HEADER,
    MAGIC,
    MAX_METADATA_BYTES,
    pack_binary_event,
    unpack_binary_event,
)


class TransportTests(unittest.TestCase):
    def test_binary_event_round_trip(self) -> None:
        metadata = {"type": "camera", "stream": True, "timestamp": 123.5}
        payload = b"\xff\xd8jpeg-data\xff\xd9"

        packet = pack_binary_event(metadata, payload)

        unpacked_metadata, unpacked_payload = unpack_binary_event(packet)
        self.assertEqual(unpacked_metadata, metadata)
        self.assertEqual(unpacked_payload, payload)

    def test_pack_rejects_empty_payload(self) -> None:
        with self.assertRaises(ValueError):
            pack_binary_event({"type": "camera"}, b"")

    def test_unpack_rejects_invalid_magic(self) -> None:
        metadata = json.dumps({"type": "camera"}).encode("utf-8")
        packet = struct.pack("!4sI", b"FAIL", len(metadata)) + metadata + b"image"

        with self.assertRaises(ValueError):
            unpack_binary_event(packet)

    def test_unpack_rejects_oversized_metadata_header(self) -> None:
        packet = HEADER.pack(MAGIC, MAX_METADATA_BYTES + 1) + b"payload"

        with self.assertRaises(ValueError):
            unpack_binary_event(packet)


if __name__ == "__main__":
    unittest.main()
