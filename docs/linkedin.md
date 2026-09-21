# LinkedIn — ORBITIQ (published post copy)

The hardest part wasn't predicting an outage.

It was building an AI network system engineers could trust.


I built ORBITIQ, an AI-powered satellite-to-cellular network intelligence platform that fuses real cell-tower data (OpenCelliD) and live satellite orbital data (CelesTrak) into a digital twin with 10,000+ simulated devices — then detects anomalies, predicts connectivity degradation, ranks satellite handoffs with explanations, simulates outages before/after AI optimization, and lets operators interrogate it all through a grounded GenAI copilot.


The biggest challenge was ensuring AI outputs were never presented as facts without provenance. Solving data classification (real vs derived vs simulated vs predicted), leakage-free model evaluation, deterministic simulation, and refusal guardrails reinforced how important auditability is in AI products: every recommendation ships with its evidence, confidence, and source.


I used Muse Spark as an engineering collaborator throughout development to accelerate research, debugging, implementation, testing, and documentation. The application itself uses transparent, evaluated ML (RandomForest F1 0.98, ROC-AUC 1.0 on held-out simulator data) with a deterministic template copilot by default and optional hosted LLM support.


ORBITIQ is built with React, TypeScript, Python, FastAPI, PostgreSQL/PostGIS, scikit-learn, sgp4, MapLibre, Docker, Playwright, and GitHub Actions.


In the business world, tools like ORBITIQ could help network operations teams predict degradation before subscribers feel it, optimize satellite handoffs with explainable evidence, rehearse outages safely, and maintain human accountability for automated decisions.


Want to try it yourself? Clone the repo, run docker compose up --build, then open http://localhost:5173 and press "Run Demo." No API key needed — live data with snapshot fallback included.


GitHub: https://github.com/sameerhashmiii/ORBITIQ


#GenerativeAI #ArtificialIntelligence #MachineLearning #SoftwareEngineering #Python #FastAPI #Telecommunications #Satellite #5G #AIOps #TechCareers

