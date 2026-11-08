import argparse
import json
import re
import shutil
import subprocess
import sys
import tomllib
import webbrowser
from pathlib import Path

# --- Configuration ---
ROOT = Path(__file__).resolve().parent
PYPROJECT_PATH = ROOT / "pyproject.toml"
MANIFEST_PATH = ROOT / "manifest.json"
LOCK_PATH = ROOT / "uv.lock"
DIST_DIR = ROOT / "dist"
PYPI_SIMPLE_URL = "https://pypi.org/simple/"
PROJECT_VERSION_RE = re.compile(r'^(\[project\]$.*?^version = ")[^"]+', re.MULTILINE | re.DOTALL)

# --- Helper Functions ---


def run_command(command, check=True, interactive=False):
    """Executes a command from the repo root, allowing interactive input if specified."""
    print(f"🏃 Running: {' '.join(command)}")
    try:
        result = subprocess.run(
            command, check=check, text=True, capture_output=not interactive, cwd=ROOT
        )
    except FileNotFoundError:
        print(f"❌ Error: Command '{command[0]}' not found. Is it installed and in your PATH?")
        sys.exit(1)
    except subprocess.CalledProcessError as e:
        print(f"❌ Command failed with exit code {e.returncode}")
        if e.stdout:
            print(e.stdout)
        if e.stderr:
            print(e.stderr, file=sys.stderr)
        sys.exit(1)
    if result.stdout:
        print(result.stdout)
    if result.stderr:
        print(result.stderr, file=sys.stderr)
    return result


def get_current_version():
    """Reads the current version from pyproject.toml."""
    with PYPROJECT_PATH.open("rb") as f:
        return tomllib.load(f)["project"]["version"]


def update_pyproject_version(new_version):
    """Rewrites the [project] version line in pyproject.toml, leaving the rest untouched."""
    text, count = PROJECT_VERSION_RE.subn(
        rf"\g<1>{new_version}", PYPROJECT_PATH.read_text(), count=1
    )
    if count != 1:
        print(f"❌ Error: could not find the [project] version line in {PYPROJECT_PATH}")
        sys.exit(1)
    PYPROJECT_PATH.write_text(text)
    print(f"✅ Version updated to {new_version} in pyproject.toml")


def update_manifest_version(new_version):
    """Updates the version in manifest.json."""
    data = json.loads(MANIFEST_PATH.read_text())
    # Update version - keep existing tools as they are manually maintained
    data["version"] = new_version
    MANIFEST_PATH.write_text(json.dumps(data, indent=2) + "\n")
    print(f"✅ Version updated to {new_version} in manifest.json")


def get_next_versions(current_version):
    """Calculates next patch, minor, and major versions."""
    major, minor, patch = map(int, current_version.split("."))
    return {
        "patch": f"{major}.{minor}.{patch + 1}",
        "minor": f"{major}.{minor + 1}.0",
        "major": f"{major + 1}.0.0",
    }


def select_version(current_version):
    """Prompts the user to select the next version."""
    next_versions = get_next_versions(current_version)
    print(f"\nCurrent version is {current_version}. Choose the next version:")
    options = list(next_versions.items())
    for i, (level, version) in enumerate(options):
        print(f"  {i + 1}) {level.capitalize()}: {version}")

    while True:
        choice = input(f"Enter your choice (1-{len(options)}): ")
        if choice.isdigit() and 1 <= int(choice) <= len(options):
            return options[int(choice) - 1][1]
        print("Invalid choice. Please try again.")


def remove_existing_tag(tag_name):
    """Removes an existing git tag both locally and remotely."""
    print(f"🗑️ Removing existing tag {tag_name}...")

    local = run_command(
        ["git", "rev-parse", "-q", "--verify", f"refs/tags/{tag_name}"], check=False
    )
    if local.returncode == 0:
        run_command(["git", "tag", "-d", tag_name])
        print(f"✅ Removed local tag {tag_name}")
    else:
        print(f"Local tag {tag_name} does not exist")

    remote = run_command(["git", "ls-remote", "--tags", "origin", f"refs/tags/{tag_name}"])
    if remote.stdout.strip():
        run_command(["git", "push", "origin", f":refs/tags/{tag_name}"])
        print(f"✅ Removed remote tag {tag_name}")
    else:
        print(f"Remote tag {tag_name} does not exist")


def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description="Release script for quantconnect-mcp")
    parser.add_argument(
        "--re-release",
        action="store_true",
        help="Re-release the current version (removes existing tags)",
    )
    return parser.parse_args()


# --- Main Release Logic ---


def main():
    """Main function to orchestrate the release process."""
    args = parse_args()

    if args.re_release:
        print("🔄 Starting re-release process for quantconnect-mcp...")
    else:
        print("🚀 Starting the release process for quantconnect-mcp...")

    # 1. Pre-flight checks
    print("\n--- 1. Running Pre-flight Checks ---")
    git_status_output = run_command(["git", "status", "--porcelain"]).stdout
    # Allow untracked files, but fail on modified or staged files.
    if any(not line.startswith("??") for line in git_status_output.splitlines()):
        print("❌ Error: Your git working directory has modified or staged files.")
        print("Please commit or stash them.")
        sys.exit(1)
    print("✅ Git working directory is clean (untracked files are ignored).")
    branch = run_command(["git", "branch", "--show-current"]).stdout.strip()
    if not branch:
        print("❌ Error: HEAD is detached. Check out the branch you want to release.")
        sys.exit(1)
    run_command(["git", "fetch", "--tags"])
    print("✅ Fetched latest git tags.")

    # 2. Version selection
    current_version = get_current_version()
    tag_name = f"v{current_version}"

    if args.re_release:
        print("\n--- 2. Re-release Setup ---")
        new_version = current_version
        print(f"Re-releasing current version: {new_version}")
        remove_existing_tag(tag_name)
    else:
        print("\n--- 2. Selecting Version ---")
        new_version = select_version(current_version)
        tag_name = f"v{new_version}"

    # 3. Update version files (skip for re-release since version is already correct)
    if not args.re_release:
        print("\n--- 3. Updating Version ---")
        update_pyproject_version(new_version)
        update_manifest_version(new_version)
        # uv.lock records the project version and CI runs `uv sync --locked`.
        run_command(["uv", "lock"])
    else:
        print("\n--- 3. Skipping Version Update (re-release) ---")
        print(f"Version files already at {new_version}")

    # 4. Build the project
    print("\n--- 4. Building Project ---")
    if DIST_DIR.exists():
        print(f"🧹 Cleaning up old build artifacts in {DIST_DIR}...")
        shutil.rmtree(DIST_DIR)
    run_command(["uv", "build", "--out-dir", str(DIST_DIR)])
    print(f"✅ Project built successfully in {DIST_DIR}")

    # 5. Git commit and tag
    print("\n--- 5. Committing and Tagging ---")
    if not args.re_release:
        # Normal release: commit version changes and tag
        run_command(["git", "add", str(PYPROJECT_PATH), str(MANIFEST_PATH), str(LOCK_PATH)])
        run_command(["git", "commit", "-m", f"chore: release {tag_name}"])
        run_command(["git", "tag", "-a", tag_name, "-m", f"Release {tag_name}"])
        print(f"✅ Committed and tagged release {tag_name}")
    else:
        # Re-release: just create the tag (no commit needed)
        run_command(["git", "tag", "-a", tag_name, "-m", f"Re-release {tag_name}"])
        print(f"✅ Tagged re-release {tag_name}")

    # 6. Push to GitHub
    print("\n--- 6. Pushing to GitHub ---")
    if not args.re_release:
        # Explicit refspec: new branches may track origin/main.
        run_command(["git", "push", "origin", f"HEAD:refs/heads/{branch}", "--follow-tags"])
        print(f"✅ Pushed {branch} and tag {tag_name} to origin.")
    else:
        # Re-release: only push the tag (no commits to push)
        run_command(["git", "push", "origin", f"refs/tags/{tag_name}"])
        print(f"✅ Pushed tag {tag_name} to origin.")

    # 7. Upload to PyPI
    print("\n--- 7. Uploading to PyPI ---")
    print("🔑 You may be prompted for PyPI credentials (or set UV_PUBLISH_TOKEN).")
    run_command(
        ["uv", "publish", "--check-url", PYPI_SIMPLE_URL, str(DIST_DIR / "*")], interactive=True
    )
    print("✅ Successfully uploaded to PyPI (or skipped if already present).")

    # 8. Create GitHub Release
    print("\n--- 8. Creating GitHub Release ---")
    print("📝 Creating a draft release on GitHub...")
    run_command(
        ["gh", "release", "create", tag_name, "--draft", "--title", tag_name], interactive=True
    )

    # Open the release in the browser for manual editing
    remote_url = run_command(["git", "remote", "get-url", "origin"]).stdout.strip()
    match = re.search(r"github\.com[/:](.+?)/(.+?)(?:\.git)?$", remote_url)
    if match:
        owner, repo = match.groups()
        release_url = f"https://github.com/{owner}/{repo}/releases/edit/{tag_name}"
        print(f"🌍 Opening your browser to edit the release: {release_url}")
        webbrowser.open(release_url)
    else:
        print("⚠️ Could not determine repository URL to open browser.")

    print(f"✅ GitHub draft release for {tag_name} created.")
    print(
        "\n🎉 Re-release process complete! 🎉" if args.re_release else "\n🎉 Release complete! 🎉"
    )


if __name__ == "__main__":
    main()
