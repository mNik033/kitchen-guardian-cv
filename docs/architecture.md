# Kitchen Guardian Architecture

This document describes the hardware and software architecture for the *Kitchen Guardian* IoT project.

## High-Level Architecture (Hardware + Software)

The system is composed of physical sensors, an edge compute device (like a Raspberry Pi), actuators to control the stove, and an alert system. The diagram below illustrates how components are connected and how data flows through the system.

```mermaid
graph LR
  subgraph Inputs ["Sensors & Power"]
    Camera["Camera<br/>(USB / Pi Camera)"]
    MQ6["MQ-6 Gas Sensor<br/>(LPG / Butane)"]
    ADC["ADC<br/>(MCP3008 / ADS1115)"]
    PSU["Power Supply<br/>(5-6V for Servo)"]
  end
  
  subgraph Edge ["Edge Device"]
    GPIO["Hardware I/O<br/>(GPIO / I²C)"]
    Vision["VisionSystem<br/>(YOLOv8 Object Detection)"]
    Safety["SafetyGuardian<br/>(Decision Logic)"]
  end
  
  subgraph Outputs ["Actuators & Remote"]
    Servo["Servo Motor<br/>(Stove Knob Controller)"]
    Mobile["Mobile App / Cloud Alerting"]
  end

  %% Data Flow
  Camera -->|Video Frames| Vision
  MQ6 -->|Analog Signal| ADC
  ADC -->|I²C / SPI| GPIO
  
  GPIO -->|Sensor Data| Safety
  Vision -->|Detections| Safety
  
  Safety -->|KILL Command| GPIO
  GPIO -->|PWM Control| Servo
  
  Safety -->|Status/Telemetry| Mobile
  
  %% Power Flow
  PSU -.->|Power| Servo
  PSU -.->|Power| Edge
```

---

## Software Architecture

### Class Diagram

The class diagram shows the structure of the Python application (`main.py`) which acts as the "Brain" on the edge device, unifying the Vision and Safety systems.

```mermaid
classDiagram
    class Main {
        +main()
        -setup_camera()
    }
    
    class Config {
        +TIMEOUT_SECONDS: int
        +WARNING_SECONDS: int
        +CRITICAL_SECONDS: int
        +CAMERA_INDEX: int
        +CONFIDENCE_THRESHOLD: float
    }

    class VisionSystem {
        -model: YOLO
        -classes: List[str]
        +__init__(model_path: str)
        +detect_objects(frame: ndarray) Dict
    }

    class SafetyGuardian {
        -last_person_seen_time: float
        -state: str
        +__init__()
        +update_status(flame_on: bool, person_present: bool) str
    }

    Main ..> VisionSystem : uses
    Main ..> SafetyGuardian : uses
    Main ..> Config : uses
    VisionSystem ..> Config : uses
    SafetyGuardian ..> Config : uses
```

### Sequence Diagram

The sequence diagram illustrates the main event loop running on the edge device, checking for humans and flames on every frame, and triggering state changes based on elapsed time.

```mermaid
sequenceDiagram
    participant C as Camera
    participant M as Main Loop
    participant V as VisionSystem
    participant S as SafetyGuardian
    participant U as UI/Display

    loop Every Frame
        M->>C: read()
        C-->>M: frame
        
        M->>V: detect_objects(frame)
        activate V
        V->>V: YOLO inference
        V-->>M: {person: bool, flame: bool, boxes: []}
        deactivate V

        M->>S: update_status(flame_on, person_present)
        activate S
        alt is person present
            S->>S: reset timer
            S-->>M: "SAFE"
        else is flame on
            S->>S: check time elapsed
            S-->>M: "SAFE" / "WARNING" / "CRITICAL"
        else flame off
            S-->>M: "SAFE"
        end
        deactivate S

        M->>U: draw_boxes(boxes)
        M->>U: draw_status(state)
        M->>U: show(frame)
    end
```