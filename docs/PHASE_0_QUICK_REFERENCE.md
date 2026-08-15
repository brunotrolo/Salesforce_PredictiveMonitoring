# PHASE 0 - QUICK REFERENCE GUIDE
**Print this. Put it on your desk during Phase 0.**

---

## 🚀 DAILY STANDUP CHECKLIST

### Every Morning
- [ ] `git pull origin main` (sync latest)
- [ ] `git checkout claude/project-plan-analysis-validation-emeiaw` (work branch)
- [ ] Check assignee list below (who's doing what today?)
- [ ] Review day's tasks in this guide

### Every Evening
- [ ] Run full test suite locally
- [ ] Commit work with clear message
- [ ] Push to branch: `git push -u origin claude/project-plan-analysis-validation-emeiaw`
- [ ] Log blockers in Issues

---

## 📅 PHASE 0 TIMELINE (Quick View)

```
BEFORE DAY 1 (Setup)
├─ (1-2h):  Instalar GitHub Skills            [All]
│           Pydantic, structlog, pytest, faker, Jest, 
│           Tailwind, Black, Ruff, mypy, pre-commit

DAY 1 (Monday)
├─ AM (1-2h):  MCP Salesforce validation       [DevOps]
└─ PM (4h):    Repo scaffold + Backend setup   [Backend]

DAY 2 (Tuesday)
├─ AM (2h):    Frontend scaffold + Jest setup  [Frontend]
├─ PM (1.5h):  Logging structure + tests       [Backend]
└─ PM (1h):    Full pipeline orchestration     [Backend]

DAY 3 (Wednesday)
├─ AM (2h):    Documentation finalization      [Tech Lead]
├─ PM (1h):    Full validation & coverage      [All]
└─ PM (1h):    Phase 0 → Phase 1 prep          [Tech Lead]

TOTAL: 11.5 + 6-8 horas de setup de skills = ~18 horas
       (pode fazer em paralelo antes de começar)
```

---

## 🔄 DAILY WORKFLOW (Each Role)

### Backend Engineer (Days 1-3)

#### Day 1 PM
```bash
# Create service structure
mkdir -p services/{collector,heuristic,comparison,shared}/{src,tests,fixtures}

# Create requirements.txt for each service
cat > services/collector/requirements.txt <<'EOF'
pytest==7.4.0
pytest-cov==4.1.0
pydantic==2.0.0
requests==2.31.0
pandas==2.0.0
structlog==23.1.0
EOF

# Initialize Python packages
touch services/{collector,heuristic,comparison,shared}/src/__init__.py

# Create pytest configs
cat > services/collector/pytest.ini <<'EOF'
[pytest]
testpaths = tests
addopts = --cov=src --cov-report=term-missing
EOF

# Test it
cd services/collector
pip install -r requirements.txt
python -m pytest --version  # Should show pytest 7.4.0
```

#### Day 2 PM
```bash
# Create logger module
cat > services/shared/src/logger.py <<'EOF'
import structlog
def setup_logging():
    structlog.configure(...)
def get_logger(name: str):
    return structlog.get_logger(name)
EOF

# Create tests
cat > services/shared/tests/test_logger.py <<'EOF'
import json
from src.logger import get_logger
def test_logging_json_format():
    # Test that logs output valid JSON
EOF

# Run tests
cd services/shared
pytest -v
```

#### Day 3 AM
```bash
# Document service contracts
cat > docs/SERVICES_CONTRACTS.md <<'EOF'
# Service Input/Output Contracts

## Collector → Heuristic
Input: List<Log>
Output: DataFrame

## Heuristic → Comparison
Input: DataFrame
Output: RiskScore (float 0-1)
EOF

# Full coverage check
pytest services/ --cov=src --cov-report=term-missing
# Look for: "TOTAL" line showing ≥80%
```

---

### Frontend Engineer (Days 2-3)

#### Day 2 AM
```bash
# Create frontend structure
mkdir -p site/{monitoring,shared,styles,tests}

# Initialize npm
cd site
npm init -y
npm install --save-dev jest @jest/globals

# Create Jest config
cat > jest.config.js <<'EOF'
module.exports = {
  testEnvironment: 'jsdom',
  setupFilesAfterEnv: ['<rootDir>/jest.setup.js'],
};
EOF

# Create mock data
cat > monitoring/mock-data.js <<'EOF'
export const mockMonitoringData = {
  risk_score: 0.42,
  alerts: [...],
  health_check: {...}
};
EOF

# Run Jest to verify setup
npm test -- --version  # Should show Jest version
```

#### Day 2 PM
```bash
# Create test file
cat > monitoring/tests/test-dashboard.js <<'EOF'
import { mockMonitoringData } from '../mock-data.js';
describe('Dashboard', () => {
  test('renders risk score', () => {
    expect(mockMonitoringData.risk_score).toBe(0.42);
  });
});
EOF

# Run tests
npm test

# Check coverage
npm test -- --coverage
# Look for: ≥70% coverage
```

---

### DevOps/SRE (Days 1, 3)

#### Day 1 AM
```bash
# Test MCP Salesforce
pip install mcp-salesforce

# Run in non-interactive mode
python3 << 'EOF'
from mcp_salesforce import SalesforceClient
client = SalesforceClient()
result = client.soql_query('SELECT Id FROM Log__c LIMIT 1')
print("✅ MCP Works!" if result else "❌ MCP Failed")
EOF

# Document result
echo "MCP Salesforce: ✅ PASS" >> /tmp/phase0_validation.txt
```

#### Day 3 PM
```bash
# Full validation
echo "=== PHASE 0 VALIDATION ===" > /tmp/validation_report.txt

# Backend tests
cd services
for svc in collector heuristic comparison shared; do
  cd $svc
  pytest -q --tb=short >> /tmp/validation_report.txt
  cd ..
done

# Frontend tests
cd site
npm test >> /tmp/validation_report.txt

# Show results
cat /tmp/validation_report.txt
```

---

## 📝 COMMIT MESSAGES (Format)

```bash
git commit -m "feat: Add collector service with mock data support

- Implement LogCollector class
- Add mock_logs.yaml fixture
- Write unit tests (5 tests, 85% coverage)
- Add structlog integration

Closes #123"
```

**Prefix:** feat, fix, docs, test, refactor, chore  
**Describe the what:** "Add X", "Fix Y", "Update Z"  
**Body:** Bullet points (optional)  
**Footer:** Issue reference (optional)

---

## 🧪 COMMAND CHEAT SHEET

### Running Tests
```bash
# All tests
pytest services/ -v

# Single service
pytest services/collector -v

# With coverage
pytest services/ --cov=src --cov-report=term-missing

# Frontend
npm test
npm test -- --coverage
```

### Git Workflow
```bash
# Create feature branch (Phase 0 already exists, just use it)
git checkout claude/project-plan-analysis-validation-emeiaw

# See what changed
git status
git diff

# Stage & commit
git add <files>
git commit -m "your message"

# Push
git push -u origin claude/project-plan-analysis-validation-emeiaw

# Sync with main
git fetch origin main
git rebase origin/main  # or merge, depending on strategy
```

### File Verification
```bash
# Check Python syntax
python -m py_compile services/collector/src/collector.py

# Check JSON output
cat /tmp/monitoring.log | python -m json.tool

# List structure
tree -L 3 services/
```

---

## ❌ COMMON MISTAKES (AVOID THESE)

| ❌ Mistake | ✅ Fix |
|-----------|--------|
| Forgetting to install requirements | `pip install -r requirements.txt` FIRST |
| Tests pass locally but fail in CI | Use mocks, not real external calls |
| JSON logging broken | Test with `python -m json.tool` |
| Coverage drops | Add tests before new features |
| Commit to main by accident | Always checkout working branch first |
| Forgot to push | Check: `git log --oneline origin/<branch>` |

---

## 📊 SUCCESS METRICS (Track Daily)

```
Day 1:
  ✅ MCP validated
  ✅ Backend services scaffolded
  ✅ Directory structure created

Day 2:
  ✅ Frontend Jest setup
  ✅ Logging tests passing (80%+ coverage)
  ✅ 10+ unit tests written

Day 3:
  ✅ All tests passing (pytest + Jest)
  ✅ Coverage ≥80% backend, ≥70% frontend
  ✅ Pipeline orchestration working
  ✅ Documentation complete
  ✅ Ready for Phase 1 transition

END OF PHASE 0: ✅ DONE
```

---

## 🎯 DEFINITION OF "DONE" FOR EACH TASK

### ✅ "Service Scaffolded"
- [ ] Directory structure exists
- [ ] requirements.txt created
- [ ] pytest.ini configured
- [ ] `pytest --version` works
- [ ] At least 1 dummy test passes

### ✅ "Test Written"
- [ ] Test file created in `tests/test_*.py`
- [ ] Uses fixture from `conftest.py`
- [ ] Passes locally: `pytest -v`
- [ ] Coverage tracked: `--cov=src`

### ✅ "Feature Complete"
- [ ] Code written
- [ ] Tests passing
- [ ] Coverage ≥80%
- [ ] Committed with clear message
- [ ] Pushed to branch

### ✅ "Phase 0 Ready for Phase 1"
- [ ] All tests passing (pytest + Jest)
- [ ] Coverage requirements met
- [ ] 3+ documentation files created
- [ ] Pipeline orchestration working
- [ ] No blockers or known bugs
- [ ] Ready for MCP integration

---

## 🚨 BLOCKING ISSUES (Escalate Immediately)

If you hit these, ping @brunotrolo:
- MCP Salesforce test fails
- pytest/Jest won't install
- Coverage can't be measured
- Pipeline errors midway
- Git conflicts (rebase questions)

---

## 📞 QUICK HELP

**Q: How do I know if my test is good?**  
A: It fails when you remove the feature, passes when you add it. Write the test AFTER the feature.

**Q: My coverage is only 65%, how do I get to 80%?**  
A: Add more test cases. Test edge cases (empty input, errors, etc).

**Q: Should I commit scaffolding or wait until tests pass?**  
A: Commit incrementally. Each commit = one working feature.

**Q: What if I break something?**  
A: `git reset --hard HEAD~1` undoes last commit. No worries.

**Q: Can I skip Phase 0 and go straight to Phase 1?**  
A: No. Phase 0 validates everything works without Salesforce.

---

## 🎓 LEARNING RESOURCES (For your team)

- **pytest:** https://docs.pytest.org/
- **Pydantic:** https://docs.pydantic.dev/
- **structlog:** https://www.structlog.org/
- **Jest:** https://jestjs.io/
- **Tailwind:** https://tailwindcss.com/

---

## 📍 NEXT STEP AFTER PHASE 0

When checklist below is 100% complete:

```bash
# Review branch
git log --oneline origin/main..HEAD  # Should see 5-10 commits

# Run full validation one last time
pytest services/ --cov=src --cov-report=term-missing
npm test -- --coverage

# Create PR
# (Instructions: docs/FASE_0_IMPLEMENTATION_GUIDE.md)
```

Then: **Phase 1 Kickoff** with MCP Salesforce integration.

---

**Print & Pin This Guide**

Keep this on your desk during Phase 0.  
Reference daily. Update as needed.

---

**Assigned Teams by Day:**

| Day | Backend | Frontend | DevOps |
|-----|---------|----------|--------|
| 1 | Setup svc | - | MCP test |
| 2 | Logger + tests | Setup Jest | - |
| 3 | Docs | Coverage ✅ | Validation |

**Questions?** → Create GitHub Issue or Slack @brunotrolo
