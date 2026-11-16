.PHONY: translate pilot run analyze figures test all
translate: ; python scripts/translate.py
pilot:     ; python scripts/run.py --pilot
run:       ; python scripts/run.py
analyze:   ; python scripts/analyze.py
figures:   ; python scripts/figures.py
test:      ; python -m pytest -q tests
all: translate run analyze figures
