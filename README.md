\# Van-Chetna 🌲



\### AI + IoT based Forest Threat Detection and Early Warning System



Van-Chetna is an intelligent forest monitoring system designed to detect potential forest threats using acoustic intelligence, IoT sensors, and long-range communication.



The system combines edge-based acoustic classification with ESP32 + LoRa sensor nodes and a centralized backend/dashboard to provide real-time forest monitoring and early warning capabilities.



\---



\## Project Structure



```text

Van-Chetna/

│

├── acoustic-ai/       # Acoustic intelligence and ML pipeline

│

├── firmware/          # ESP32 + LoRa firmware

│

├── backend/           # FastAPI + PostgreSQL backend

│

├── frontend/          # React monitoring dashboard

│

└── docs/              # PRD, architecture and shared contracts



Workstreams

Workstream	Responsibility

acoustic-ai/	FSC22 dataset processing, acoustic classification, YAMNet/CNN models and inference

firmware/	ESP32, sensors and LoRa communication

backend/	FastAPI APIs, PostgreSQL and alert/data management

frontend/	Real-time monitoring and visualization dashboard

docs/	Product requirements, architecture and shared API/data contracts



Acoustic AI



The acoustic intelligence pipeline currently uses the FSC22 environmental sound dataset.



Dataset

2,025 audio clips

27 original FSC22 classes

75 clips per original class

Mapped into 7 ForestGuard/Van-Chetna acoustic classes

Simplified Classes

Animal

Chainsaw\_Threat

Fire\_Threat

Generator\_Mechanical

Human\_Activity

Normal\_Environmental

Vehicle

Current Pipeline

FSC22 Audio

&#x20;    ↓

Metadata Validation

&#x20;    ↓

Class Mapping

&#x20;    ↓

Log-Mel Spectrogram Extraction

&#x20;    ↓

Group-Safe Train / Validation / Test Split

&#x20;    ↓

CNN Baseline

&#x20;    ↓

YAMNet Embeddings

&#x20;    ↓

Classifier / Inference



For acoustic-AI setup and execution instructions, see: acoustic-ai/00\_SETUP\_GUIDE.md



evelopment Workflow



Do not push directly to main.



Create a branch for every task:



git checkout -b <your-name>/<short-description>



Example:



git checkout -b ujwal/fusion-engine



After completing the task:



git add .

git commit -m "Add fusion engine"

git push origin ujwal/fusion-engine



Then create a Pull Request into main.



Data and Model Files



Large generated files are intentionally excluded from Git.



This includes:



FSC22 audio dataset

Generated feature arrays

YAMNet embeddings

Trained Keras models

TensorFlow Lite models

Python virtual environments



These files should be generated locally using the instructions in the respective workstream.



Documentation



Shared project documentation will be maintained under:



docs/



Important shared contracts will be maintained in:



docs/SCHEMAS.md



This file will contain the agreed:



LoRa payload format

Backend API contracts

Alert schema

Sensor data format

Communication interfaces



All workstreams should follow these contracts.



Status



Van-Chetna is currently under active development for the SIH internal evaluation.



The repository is organized into independent workstreams so that AI, firmware, backend and frontend development can proceed in parallel.

