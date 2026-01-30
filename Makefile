.PHONY: setup test run help

help:
	@echo "Available targets:"
	@echo "  setup  - Install dependencies"
	@echo "  test   - Run tests for misc charges module"
	@echo "  run    - Run the Misc Charges Streamlit page"

setup:
	pip install pandas numpy streamlit openpyxl

test:
	python3 tests/test_misc_nonship.py

run:
	streamlit run pages/03_Misc_Charges.py --server.port 5000
