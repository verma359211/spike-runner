import argparse
import base64
import io
import json
import os
import time
import uuid
import zipfile
from pathlib import Path
from urllib.parse import quote

import requests


API_ROOT = "https://api.github.com"
POLL_SECONDS = 3
TIMEOUT_SECONDS = 300


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", required=True, help="Target repository as OWNER/NAME")
    parser.add_argument("--test", required=True, type=Path, help="Local Jest test file")
    return parser.parse_args()


def check_response(response):
    if not response.ok:
        raise RuntimeError(
            f"GitHub API returned {response.status_code}: {response.text}"
        )
    return response


def classify(result):
    failed_tests = result.get("numFailedTests", 0)
    failed_suites = result.get("numFailedTestSuites", 0)
    passed_tests = result.get("numPassedTests", 0)

    if failed_tests > 0:
        return "reproduced"
    if failed_suites == 0 and passed_tests > 0:
        return "not_reproduced"
    if failed_suites > 0 and failed_tests == 0:
        return "repro_broken"
    return "infra_error"


def main():
    args = parse_args()
    token = os.environ.get("GITHUB_TOKEN")
    if not token:
        raise RuntimeError("GITHUB_TOKEN is not set")
    if args.repo.count("/") != 1:
        raise RuntimeError("--repo must be in OWNER/NAME format")
    if not args.test.is_file():
        raise RuntimeError(f"Test file does not exist: {args.test}")

    run_id = uuid.uuid4().hex[:12]
    branch = f"repro/{run_id}"
    started = time.monotonic()
    branch_created = False
    classification = "infra_error"

    session = requests.Session()
    session.headers.update(
        {
            "Accept": "application/vnd.github+json",
            "Authorization": f"Bearer {token}",
            "X-GitHub-Api-Version": "2022-11-28",
        }
    )
    repo_url = f"{API_ROOT}/repos/{args.repo}"

    try:
        repository = check_response(session.get(repo_url)).json()
        default_branch = repository["default_branch"]
        branch_info = check_response(
            session.get(f"{repo_url}/branches/{quote(default_branch, safe='')}")
        ).json()
        base_sha = branch_info["commit"]["sha"]

        check_response(
            session.post(
                f"{repo_url}/git/refs",
                json={"ref": f"refs/heads/{branch}", "sha": base_sha},
            )
        )
        branch_created = True

        encoded_test = base64.b64encode(args.test.read_bytes()).decode("ascii")
        check_response(
            session.put(
                f"{repo_url}/contents/repro/repro.test.js",
                json={
                    "message": f"Add reproduction test {run_id}",
                    "content": encoded_test,
                    "branch": branch,
                },
            )
        )

        check_response(
            session.post(
                f"{repo_url}/actions/workflows/repro.yml/dispatches",
                json={"ref": branch, "inputs": {"run_id": run_id}},
            )
        )

        deadline = time.monotonic() + TIMEOUT_SECONDS
        workflow_run = None
        while time.monotonic() < deadline:
            runs = check_response(
                session.get(
                    f"{repo_url}/actions/workflows/repro.yml/runs",
                    params={
                        "event": "workflow_dispatch",
                        "branch": branch,
                        "per_page": 20,
                    },
                )
            ).json()["workflow_runs"]
            workflow_run = next(
                (
                    run
                    for run in runs
                    if run.get("display_title") == f"repro-{run_id}"
                ),
                None,
            )
            if workflow_run:
                break
            time.sleep(POLL_SECONDS)

        if workflow_run is None:
            raise TimeoutError("Timed out waiting for the workflow run to appear")

        while workflow_run["status"] != "completed":
            if time.monotonic() >= deadline:
                raise TimeoutError("Timed out waiting for the workflow run to complete")
            time.sleep(POLL_SECONDS)
            workflow_run = check_response(
                session.get(f"{repo_url}/actions/runs/{workflow_run['id']}")
            ).json()

        artifacts = check_response(
            session.get(f"{repo_url}/actions/runs/{workflow_run['id']}/artifacts")
        ).json()["artifacts"]
        artifact = next(
            (
                item
                for item in artifacts
                if item["name"] == "result" and not item["expired"]
            ),
            None,
        )

        if artifact:
            archive = check_response(
                session.get(
                    f"{repo_url}/actions/artifacts/{artifact['id']}/zip"
                )
            ).content
            with zipfile.ZipFile(io.BytesIO(archive)) as artifact_zip:
                try:
                    result = json.loads(artifact_zip.read("result.json"))
                    classification = classify(result)
                except KeyError:
                    classification = "infra_error"
    finally:
        if branch_created:
            check_response(
                session.delete(
                    f"{repo_url}/git/refs/heads/{quote(branch, safe='')}"
                )
            )
        print(f"classification: {classification}")
        print(f"seconds: {time.monotonic() - started:.2f}")


if __name__ == "__main__":
    main()
