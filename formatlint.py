import os
import subprocess
import sys

# Define ANSI escape codes for colors
GRAY = "\033[90m"
RED = "\033[91m"
GREEN = "\033[92m"
RESET = "\033[0m"

# Define the commands to be run
commands = [
    ("ruff format .", "Formatting"),
    ("ruff check --select I --fix .", "Sorting imports"),
    ("ruff check .", "Linting"),
]


def run_command(command, description, index):
    print(f"{GRAY}┌── {description} [{command}]{RESET}")
    process = subprocess.Popen(
        command,
        shell=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        bufsize=1,
        universal_newlines=True,
    )
    assert process.stdout is not None

    while True:
        output = process.stdout.readline()
        if output == "" and process.poll() is not None:
            break
        if output:
            sys.stdout.write(f"{GRAY}│   >{RESET} {output}")
            sys.stdout.flush()

    # Read any remaining output after the process has completed
    remaining_output = process.stdout.read()
    if remaining_output:
        for line in remaining_output.splitlines():
            print(f"{GRAY}│   >{RESET} " + line)

    return_code = process.poll()

    if return_code == 0:
        print(
            f"{GRAY}└── {GREEN}{description} [{command}] completed successfully.{RESET}"
        )
    else:
        print(
            f"{GRAY}└── {RED}{description} [{command}] failed with return code {return_code}.{RESET}"
        )

    return return_code


def main():
    script_dir = os.path.dirname(os.path.realpath(__file__))
    os.chdir(script_dir)
    print(f"{GRAY}Running Scripts:{RESET}\n")

    for i, (command, description) in enumerate(commands):
        return_code = run_command(command, description, i)
        if i < len(commands) - 1:
            print()
        if return_code != 0:
            break

    if return_code == 0:
        print(f"\n{GRAY}{GREEN}Scripts run successfully.{RESET}")
    else:
        print(f"\n{GRAY}{RED}A script failed with return code {return_code}.{RESET}")


if __name__ == "__main__":
    main()
