# Spike runner

## Setup

1. Create two empty GitHub repositories named `spike-target` and `spike-runner`.
2. Commit and push the contents of each local folder to its matching repository's default branch.
3. Confirm GitHub Actions is enabled in the `spike-target` repository.
4. Create a fine-grained personal access token restricted to `spike-target` with **Actions: Read and write** and **Contents: Read and write**. Metadata read access is included automatically.
5. Install Python 3.11, then create and activate a virtual environment inside `spike-runner`:
   - PowerShell: `py -3.11 -m venv .venv` then `.venv\Scripts\Activate.ps1`
   - macOS/Linux: `python3.11 -m venv .venv` then `source .venv/bin/activate`
6. Install the only dependency: `python -m pip install -r requirements.txt`
7. Copy `.env.example` to `.env`, then replace the example value in `.env` with your token. The `.env` file is ignored by Git and must not be committed.
8. Run one sample: `python run_repro.py --repo OWNER/spike-target --test samples/reproduces_bug.test.js`
9. Run all three samples three times each: `python run_all.py --repo OWNER/spike-target`

The target repository must contain the `repro.yml` workflow from `spike-target`, and GitHub Actions must be enabled.
After reading the result, the runner deletes both the temporary branch and its workflow run.
