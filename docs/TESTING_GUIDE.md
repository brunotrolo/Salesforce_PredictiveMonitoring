# Testing Guide - Phase 0

## Backend (Python + pytest)

### Setup
```bash
# From project root
cd services/collector && pip install -r requirements.txt && cd ../..
cd services/heuristic && pip install -r requirements.txt && cd ../..
cd services/comparison && pip install -r requirements.txt && cd ../..
cd services/shared && pip install -r requirements.txt && cd ../..
```

### Run all backend tests
```bash
# Per service
pytest services/collector/ -v
pytest services/heuristic/ -v
pytest services/comparison/ -v
pytest services/shared/ -v

# All services with coverage
pytest services/ -v --cov=src --cov-report=term-missing
```

### Coverage requirements
- **Backend minimum:** 80% line coverage
- **Enforced per service** via `pytest.ini`

### Key conventions
- Fixtures live in `tests/conftest.py`
- Mock data lives in `tests/fixtures/` as YAML
- Tests follow `test_<module>.py` naming
- Use `@pytest.fixture` for reusable test data

---

## Frontend (JavaScript + Jest)

### Setup
```bash
cd site
npm install
```

### Run frontend tests
```bash
cd site
npm test
```

### Coverage requirements
- **Frontend minimum:** 70% line coverage
- **Configured in:** `site/jest.config.js`

### Key conventions
- Mock data in `monitoring/mock-data.js`
- Tests in `monitoring/tests/test-dashboard.js`
- ES modules (`type: "module"` in package.json)
- Jest with `--experimental-vm-modules`

---

## Pipeline Integration

### Run the full mock pipeline
```bash
python monitoring/orchestrate.py --mode mock --log-file monitoring_output.json
```

### Validate output
```bash
cat monitoring_output.json | python -m json.tool
```

---

## CI Validation (GitHub Actions)

```bash
# Backend coverage check
pytest services/ --cov=src --cov-report=xml

# Frontend coverage check
cd site && npm test -- --coverage
```
