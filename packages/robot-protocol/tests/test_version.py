import unittest

from robot_protocol.version import PROTOCOL_VERSION, is_supported_protocol_version


class VersionTests(unittest.TestCase):
    def test_current_version_is_supported(self) -> None:
        self.assertTrue(is_supported_protocol_version(PROTOCOL_VERSION))
        self.assertTrue(is_supported_protocol_version(str(PROTOCOL_VERSION)))

    def test_unknown_and_boolean_versions_are_rejected(self) -> None:
        self.assertFalse(is_supported_protocol_version(PROTOCOL_VERSION + 1))
        self.assertFalse(is_supported_protocol_version(True))


if __name__ == "__main__":
    unittest.main()
