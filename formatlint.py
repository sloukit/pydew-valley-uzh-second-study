import os
import shutil
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


def find_ruff_executable():
    """Find the ruff executable, handling Windows .exe extension."""
    # Try to find ruff in PATH
    ruff_path = shutil.which("ruff")
    if ruff_path:
        return "ruff"

    # On Windows, also try ruff.exe explicitly
    if sys.platform == "win32":
        ruff_exe_path = shutil.which("ruff.exe")
        if ruff_exe_path:
            return "ruff.exe"

    # If not found, return "ruff" and let the error handling deal with it
    return "ruff"


def prepare_commands():
    """Prepare commands with the correct ruff executable."""
    ruff_cmd = find_ruff_executable()
    return [
        (f"{ruff_cmd} format .", "Formatting"),
        (f"{ruff_cmd} check --select I --fix .", "Sorting imports"),
        (f"{ruff_cmd} check .", "Linting"),
    ]


def run_command(command, description, index):
    print(f"{GRAY}┌── {description} [{command}]{RESET}")

    try:
        process = subprocess.Popen(
            command,
            shell=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            bufsize=1,
            universal_newlines=True,
        )
    except Exception as e:
        print(f"{GRAY}└── {RED}{description} [{command}] failed to start: {e}{RESET}")
        return 1

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

    # Prints diagnostic information
    print(f"{GRAY}Platform: {sys.platform}{RESET}")
    print(f"{GRAY}Working directory: {os.getcwd()}{RESET}")

    # Check if ruff is available
    ruff_cmd = find_ruff_executable()
    print(f"{GRAY}Ruff executable: {ruff_cmd}{RESET}")

    # Test if ruff is accessible
    try:
        result = subprocess.run(
            [ruff_cmd, "--version"], capture_output=True, text=True, timeout=10
        )
        if result.returncode == 0:
            print(f"{GRAY}Ruff version: {result.stdout.strip()}{RESET}")
        else:
            print(
                f"{GRAY}{RED}Warning: Could not get ruff version (return code: {result.returncode}){RESET}"
            )
    except Exception as e:
        print(f"{GRAY}{RED}Warning: Could not access ruff: {e}{RESET}")

    print(f"{GRAY}Running Scripts:{RESET}\n")

    # Prepare commands with correct executable
    commands = prepare_commands()

    overall_success = True
    for i, (command, description) in enumerate(commands):
        return_code = run_command(command, description, i)
        if i < len(commands) - 1:
            print()

        # For formatting and import sorting, failure should stop the process
        # For linting, we want to continue and just report the issues
        if return_code != 0:
            if description == "Linting":
                # Linting failures are informational - don't stop the process
                print(
                    f"{GRAY}Note: Linting found issues that can be fixed with 'ruff check --fix .'{RESET}"
                )
                overall_success = False  # Still mark as not fully successful
            else:
                # Formatting or import sorting failures should stop
                overall_success = False
                break

    if overall_success:
        print(f"\n{GRAY}{GREEN}Scripts run successfully.{RESET}")
    else:
        print(
            f"\n{GRAY}{RED}Scripts completed with issues. See output above for details.{RESET}"
        )


if __name__ == "__main__":
    main()
