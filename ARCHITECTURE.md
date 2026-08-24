# Van-Chetna (Forest Guard) — Flow chart of the model

The full pipeline, laid out in three labeled stages (Sensing / Audio, Edge AI + Model
Training, Backend Fusion + Response). Node colors group related concerns and arrow labels
describe what data moves between parts.

```mermaid
%%{init: {"flowchart": {"nodeSpacing": 60, "rankSpacing": 80, "padding": 15, "useMaxWidth": false}, "themeVariables": {"fontSize": "22px"}}}%%
flowchart TB
    USER(["Forest sound<br/>chainsaw / vehicle / human"])

    %% ---------- STAGE 1: SENSING / AUDIO ----------
    MIC["INMP441 I2S Mic<br/>16 kHz"]
    ESP{{"ESP32 Node<br/>node_main.ino"}}
    WIN["5 s audio window<br/>80000 int16 PCM"]
    GATECHK{"Threat<br/>confirmed?"}
    TOOLOW["Below threshold<br/>0.7"]
    NEEDMORE["Need 2 consecutive<br/>windows"]

    USER -->|"via microphone"| MIC
    MIC -->|"I2S sampling"| ESP
    ESP -->|"buffer + frame"| WIN
    WIN -->|"Serial AUD1 + PCM @921600"| GATECHK
    GATECHK -->|"conf below 0.7"| TOOLOW
    GATECHK -->|"only 1 window"| NEEDMORE
    TOOLOW -.->|"drop, keep listening"| ESP
    NEEDMORE -.->|"wait for next window"| ESP

    %% ---------- STAGE 2: EDGE AI + TRAINING ----------
    COMP["Edge Companion<br/>09_node_companion.py"]
    YAMNET["YAMNet<br/>1024-dim embedding"]
    HEAD["Classifier head<br/>best_model_yamnet.keras"]
    EVENT["Event JSON<br/>class + confidence"]

    GATECHK -->|"confirmed (2x above 0.7)"| COMP
    COMP -->|"embed audio"| YAMNET
    YAMNET -->|"features"| HEAD
    HEAD -->|"predicted class"| EVENT

    %% Training subgraph (offline)
    subgraph TRAIN["Model Fine-tuning and Training Part (offline)"]
        FSC["FSC22 dataset<br/>2025 clips / 27 classes"]
        MAP["02 label mapping<br/>27 -> 7 classes"]
        EMB["05 YAMNet embeddings"]
        FIT["06 train dense head"]
        FSC --> MAP --> EMB --> FIT
    end
    FIT -.->|"trained weights"| HEAD

    %% ---------- STAGE 3: BACKEND FUSION + RESPONSE ----------
    LORA["Gateway ESP32<br/>lora_receiver.ino"]
    APIIN["Backend POST /events<br/>store + dedupe"]
    FUSE["Fusion engine<br/>0.5 ac + 0.3 person + 0.2 veh"]
    SEV{"Severity?"}
    DBST[("PostgreSQL<br/>threats + alerts")]
    WSPUSH["WebSocket /ws/live"]
    DASH["Officer Dashboard<br/>map + alert + toast"]
    ACK["Officer acknowledges<br/>POST /alerts/id/ack"]

    EVENT -->|"LoRa 866 MHz + JSON back to node"| LORA
    LORA -->|"serial JSON -> HTTP POST"| APIIN
    APIIN -->|"run_fusion_for_node"| FUSE
    FUSE -->|"upsert Threat + Alert"| DBST
    FUSE --> SEV
    SEV -->|"critical / medium"| WSPUSH
    SEV -.->|"low: store only"| DBST
    WSPUSH -->|"live alert"| DASH
    DASH -->|"officer action"| ACK
    ACK -.->|"update status"| APIIN

    %% ---------- STYLING ----------
    classDef audio fill:#FDE68A,stroke:#B45309,color:#111;
    classDef decision fill:#34D399,stroke:#065F46,color:#111;
    classDef ai fill:#C4B5FD,stroke:#5B21B6,color:#111;
    classDef backend fill:#93C5FD,stroke:#1E40AF,color:#111;
    classDef alertn fill:#FCA5A5,stroke:#991B1B,color:#111;
    classDef data fill:#F9A8D4,stroke:#9D174F,color:#111;
    classDef reject fill:#FDBA74,stroke:#9A3412,color:#111;

    class MIC,ESP,WIN audio;
    class GATECHK,SEV decision;
    class COMP,YAMNET,HEAD,EVENT,FSC,MAP,EMB,FIT ai;
    class LORA,APIIN,FUSE,ACK backend;
    class WSPUSH,DASH alertn;
    class DBST data;
    class TOOLOW,NEEDMORE reject;
```

Stage legend:

- Yellow = Sensing / Audio part (mic to framed window)
- Green = Decision gates (threat confirmation, severity routing)
- Purple = Edge AI + model training (YAMNet, classifier head, offline training)
- Blue = Backend fusion and API
- Red = Alerting / dashboard
- Pink = Data store
