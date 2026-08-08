"""Run command-planning examples without initializing Raspberry Pi hardware.

If a Gemini API key is configured, the examples use Gemini. Otherwise the
rule-based fallback in RobotActions is exercised. No motor, camera, sensor,
microphone, or speaker method is called by this file.
"""

from actions import RobotActions


SCENARIOS = [
    "앞으로 세 번 가고 오른쪽으로 돌아",
    "장애물 앞까지 가서 멈춰",
    "내가 진라면을 들고 있으면 앞으로 와 봐",
    "앞에 있는 물건이 무엇인지 알려줘",
]


def run_tests():
    planner = RobotActions(hardware=None)
    for index, command in enumerate(SCENARIOS, start=1):
        print("=" * 60)
        print(f"시나리오 {index}: {command}")
        print(planner.decide_command(command))


if __name__ == "__main__":
    run_tests()
