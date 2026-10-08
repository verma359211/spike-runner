import argparse
import os
import subprocess
import sys
from pathlib import Path


SAMPLES = [
    ("reproduces_bug.test.js", "reproduced"),
    ("no_bug.test.js", "not_reproduced"),
    ("broken_syntax.test.js", "repro_broken"),
]


def run_sample(repo, sample):
    command = [
        sys.executable,
        str(Path(__file__).with_name("run_repro.py")),
        "--repo",
        repo,
        "--test",
        str(Path(__file__).with_name("samples") / sample),
    ]
    completed = subprocess.run(command, capture_output=True, text=True)
    output = completed.stdout.splitlines()
    classification = next(
        (
            line.removeprefix("classification: ")
            for line in output
            if line.startswith("classification: ")
        ),
        "runner_error",
    )
    seconds = next(
        (
            line.removeprefix("seconds: ")
            for line in output
            if line.startswith("seconds: ")
        ),
        "-",
    )
    return classification, seconds


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", required=True, help="Target repository as OWNER/NAME")
    args = parser.parse_args()

    if not os.environ.get("GITHUB_TOKEN"):
        raise RuntimeError("GITHUB_TOKEN is not set")

    print(f"{'sample':28} {'expected':16} {'actual':16} {'seconds':9} result")
    print("-" * 82)
    for sample, expected in SAMPLES:
        for _ in range(3):
            actual, seconds = run_sample(args.repo, sample)
            result = "match" if actual == expected else "mismatch"
            print(f"{sample:28} {expected:16} {actual:16} {seconds:9} {result}")


if __name__ == "__main__":
    main()
