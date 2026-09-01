import unittest

from robot_protocol.actions import (
    ALLOWED_ACTIONS,
    MAX_COMMAND_DURATION_MS,
    MAX_DRIVE_DURATION_MS,
    Action,
    max_duration_ms,
    parse_action,
)


class ActionTests(unittest.TestCase):
    def test_all_enum_values_are_publicly_allowed(self) -> None:
        self.assertEqual(ALLOWED_ACTIONS, {action.value for action in Action})

    def test_parse_action_normalizes_case_and_space(self) -> None:
        self.assertIs(parse_action(" forward "), Action.FORWARD)

    def test_parse_action_rejects_unknown_value(self) -> None:
        with self.assertRaisesRegex(ValueError, "허용되지 않은"):
            parse_action("FLY")

    def test_drive_duration_is_more_restrictive(self) -> None:
        self.assertEqual(max_duration_ms(Action.LEFT), MAX_DRIVE_DURATION_MS)
        self.assertEqual(max_duration_ms(Action.VIDEO_START), MAX_COMMAND_DURATION_MS)


if __name__ == "__main__":
    unittest.main()
