# Contributing to Varve

Thank you for your interest in contributing to **Varve**! 

Varve is an evidence-backed ML lineage archaeologist built for [DataHub](https://datahubproject.io/). We welcome contributions from the community to expand risk patterns, refine evidence correlation algorithms, and enhance DataHub integrations.

---

## 📜 Code of Conduct

Please review and adhere to our [Code of Conduct](CODE_OF_CONDUCT.md) in all community interactions.

---

## 🚀 How to Contribute

### 1. Reporting Bugs & Suggesting Features
- Search existing [GitHub Issues](https://github.com/cridiv/varve/issues) before opening a new one.
- Use a clear, descriptive title and provide details: steps to reproduce, expected behavior, logs, and system environment.

### 2. Proposing DataHub Aspect & RFC Changes
- Varve proposes the `ValidatedRiskPattern` aspect type for DataHub.
- If you wish to propose enhancements to the schema or correlation logic, please inspect `docs/datahub-rfc-validated-risk-pattern.md` and `docs/validated-risk-pattern.avsc`.

### 3. Local Development Setup
Follow the steps in the [README](README.md#running-it-locally):

```bash
# 1. Clone repo
git clone https://github.com/cridiv/varve.git
cd varve

# 2. Spin up local stack
docker compose up -d

# 3. Run the live verification test
cd scripts
../service/.venv/bin/python e2e_live_test.py
```

### 4. Submitting Pull Requests
1. Fork the repository and create your feature branch: `git checkout -b feature/my-new-feature`.
2. Commit your changes with clear, descriptive commit messages.
3. Ensure verification scripts pass: `python3 service/scripts/verify_ledger.py`.
4. Push to your branch and submit a Pull Request against `main`.

---

## 🛠 Project Structure

- `service/`: FastAPI backend service, pattern correlation engine, and DataHub emitter.
- `app/`: Next.js 16 + React 19 frontend UI (Triage Dashboard, Finding Detail, Audit Ledger Modal).
- `scripts/`: E2E live test harness (`e2e_live_test.py`) and verification tools.
- `docs/`: RFC documents, Avro schemas (`.avsc`), and empirical validation benchmarks.

---

## 📄 License

By contributing to Varve, you agree that your contributions will be licensed under the [Apache 2.0 License](LICENSE).
