import unittest

import robot_protocol
from robot_protocol.actions import Action
from robot_protocol.messages import (
    CommandMessage,
    HelloAckMessage,
    HelloMessage,
    MessageType,
    parse_message_type,
)
from robot_protocol.version import PROTOCOL_VERSION


class MessageTests(unittest.TestCase):
    def test_hello_round_trip_includes_version_without_exposing_token_in_repr(self) -> None:
        hello = HelloMessage.from_mapping(
            {
                "type": "hello",
                "robot_id": "robot-01",
                "token": "secret-token",
                "protocol_version": PROTOCOL_VERSION,
            }
        )

        self.assertEqual(hello.to_dict()["protocol_version"], PROTOCOL_VERSION)
        self.assertNotIn("secret-token", repr(hello))

    def test_legacy_hello_without_version_uses_current_version(self) -> None:
        hello = HelloMessage.from_mapping(
            {"type": "hello", "robot_id": "robot-01", "token": "secret-token"}
        )

        self.assertEqual(hello.protocol_version, PROTOCOL_VERSION)

    def test_hello_ack_round_trip_includes_protocol_version(self) -> None:
        hello_ack = HelloAckMessage.from_mapping(
            {
                "type": "hello_ack",
                "server_time": 1788275415.78,
                "protocol_version": PROTOCOL_VERSION,
            }
        )
        self.assertEqual(
            hello_ack.to_dict(),
            {
                "type": "hello_ack",
                "server_time": 1788275415.78,
                "protocol_version": PROTOCOL_VERSION,
            },
        )

    def test_hello_ack_is_exported_from_package_root(self) -> None:
        self.assertIs(robot_protocol.HelloAckMessage, HelloAckMessage)

    def test_legacy_hello_ack_without_version_uses_current_version(self) -> None:
        hello_ack = HelloAckMessage.from_mapping(
            {"type": "hello_ack", "server_time": 1788275415.78}
        )

        self.assertEqual(hello_ack.protocol_version, PROTOCOL_VERSION)

    def test_hello_ack_rejects_unsupported_version(self) -> None:
        with self.assertRaisesRegex(ValueError, "지원하지 않는"):
            HelloAckMessage.from_mapping(
                {
                    "type": "hello_ack",
                    "server_time": 1788275415.78,
                    "protocol_version": PROTOCOL_VERSION + 1,
                }
            )

    def test_hello_ack_rejects_invalid_server_time(self) -> None:
        with self.assertRaisesRegex(ValueError, "server_time"):
            HelloAckMessage.from_mapping(
                {"type": "hello_ack", "server_time": float("inf")}
            )

    def test_command_round_trip_normalizes_action(self) -> None:
        command = CommandMessage.from_mapping(
            {
                "type": "command",
                "id": "command-1",
                "action": "left",
                "duration_ms": 650,
            }
        )

        self.assertIs(command.action, Action.LEFT)
        self.assertEqual(command.to_dict()["action"], "LEFT")

    def test_text_command_requires_text(self) -> None:
        with self.assertRaisesRegex(ValueError, "비어"):
            CommandMessage.from_mapping(
                {
                    "type": "command",
                    "id": "command-2",
                    "action": "TEXT_COMMAND",
                }
            )

    def test_direct_command_requires_action_enum(self) -> None:
        with self.assertRaisesRegex(TypeError, "Action"):
            CommandMessage(command_id="command-3", action="LEFT")  # type: ignore[arg-type]

    def test_message_type_rejects_unknown_type(self) -> None:
        with self.assertRaisesRegex(ValueError, "알 수 없는"):
            parse_message_type({"type": "unknown"})

    def test_parse_message_type_returns_enum(self) -> None:
        self.assertIs(parse_message_type({"type": "speech"}), MessageType.SPEECH)


if __name__ == "__main__":
    unittest.main()
