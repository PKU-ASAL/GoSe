# GoSe

0. Install required packages

1. Build Instantiation Guidebook
- compile target program (with gcov support)
- prepare target program manual
- (implement your parsing logic in `GoSe/utils/parse_manual.py`)
- `python3 main.py --generate-instantiation-guidebook --prog-path=/path/to/program --option-csv-dir=GoSe/input/instantiation_guidebook`

2. Construct Fine-Grained Decision Probability
- `python3 main.py --build-graph --strategy GoSe --prog-path=/path/to/program --prog-gcov-dir=/path/to/program_gcov_directory --option-csv-dir=GoSe/input/instantiation_guidebook --save-probability-dir=GoSe/output/probability --coverage-server-port=12321`

3. Generate option sequences
- `python3 main.py --test-seeds --strategy GoSe --prog-path=/path/to/program --prog-gcov-dir=/path/to/program_gcov_directory --option-csv-dir=GoSe/input/instantiation_guidebook --save-probability-dir=GoSe/output/probability --output-seeds-dir=GoSe/output/seeds --coverage-server-port=12321`