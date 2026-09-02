import pytest

from robot_protocol.transport import pack_binary_event, unpack_binary_event


def test_binary_camera_event_round_trip():
    metadata = {"type": "camera", "stream": True, "timestamp": 123.5}
    image = b"\xff\xd8jpeg-data\xff\xd9"

    decoded_metadata, decoded_image = unpack_binary_event(pack_binary_event(metadata, image))

    assert decoded_metadata == metadata
    assert decoded_image == image


def test_invalid_binary_packet_is_rejected():
    with pytest.raises(ValueError):
        unpack_binary_event(b"not-a-robot-packet")
