# People Card CLI

## Overview
People Card CLI is a lightweight command line tool for building people-card migration data. It can load URLs from DSM spreadsheets, extract links and embedded resources, cache results, and generate simplified HTML reports.

## Installation
```bash
# clone the repo
git clone <repository-url>
cd people-card-cli
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

## Quick Start
Run the CLI:
```bash
./run
```
Generate a report for a DSM entry:
```bash
report Enterprise 23
```
Process a CSV in bulk:
```bash
bulk_check my_pages.csv
```

## Commands
| Command | Purpose |
|---------|---------|
| `report [--force] [<domain> <row1> [row2 ...]]` | Generate an HTML report showing the existing URL, DSM location, and all found links and resources |
| `bulk_check [csv]` | Process many pages listed in a CSV file |
| `help [command]` | Show help information |
| `exit, quit` | Leave the application |

## File Structure
```
people-card-cli/
├── commands/      # Command implementations
├── data/          # DSM utilities
├── templates/     # HTML report template and assets
├── tests/         # Test suite
├── main.py        # CLI entry point
└── run            # Convenience launcher
```
