# Orchestrator

The only entry point. See `docs/architecture.md` for the design.

```bash
python3 toolkit/orchestrator/orchestrator.py list                          # departments, dependencies, save locations
python3 toolkit/orchestrator/orchestrator.py run                           # run every department
python3 toolkit/orchestrator/orchestrator.py run --only web                # run web and what it depends on
python3 toolkit/orchestrator/orchestrator.py run --run-engine              # also run the laptop research engine (hours)
python3 toolkit/orchestrator/orchestrator.py status                        # last saved run
python3 toolkit/orchestrator/orchestrator.py match --segment investor --budget-cr 30
python3 -m unittest discover -s tests                                      # tests
```

Python 3.11 or later, standard library only.
