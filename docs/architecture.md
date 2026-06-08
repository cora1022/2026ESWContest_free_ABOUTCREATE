# Architecture

## System Overview

```mermaid
flowchart TD
    User["User voice/text command"]
    Listener["Command listener"]
    Sensor["Distance sensor"]
    Brain["main_brain.py"]
    Gemini["Gemini model"]
    Tools["Function tools"]
    Actions["actions.py"]
    Hardware["Motor / speaker / sensor hardware"]

    User --> Listener
    Listener --> Brain
    Sensor --> Brain
    Brain --> Gemini
    Gemini --> Tools
    Tools --> Actions
    Actions --> Hardware
```

## Runtime Decision Flow

```mermaid
sequenceDiagram
    participant User
    participant Brain as main_brain.py
    participant Gemini
    participant Actions as actions.py
    participant Robot as Robot hardware

    User->>Brain: Command
    Brain->>Brain: Read distance
    Brain->>Gemini: Command + distance + safety prompt
    Gemini-->>Brain: Text and/or function call
    Brain->>Actions: Execute selected function
    Actions->>Robot: Move, stop, spin, or speak
```

## Module Roles

| File | Role |
| --- | --- |
| `main_brain.py` | Primary Gemini function-calling experiment using `google-genai`. |
| `2main_brain.py` | Older experiment using `google-generativeai`. Keep for comparison or delete later. |
| `actions.py` | Action functions exposed to the model. |
| `hardware.py` | Virtual hardware abstraction used while GPIO integration is incomplete. |
| `test_case.py` | Small local test entrypoint. |

## Safety Boundary

The model does not directly control GPIO. It selects from a small set of Python functions. Real motor control should stay behind the `actions.py` and `hardware.py` boundary so prompts cannot execute arbitrary code.
