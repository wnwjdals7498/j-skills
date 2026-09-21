#!/usr/bin/env python3
"""Inject the Unity AI Development Pipeline Kit into a Unity project.

Portable counterpart of apply-kit.ps1 — same output, runs wherever Python 3.8+
does, so Claude Code and Codex can both apply the kit on any OS.

Existing files are never overwritten unless --force is given: the kit adds
rules, it does not clobber a project's own conventions.

    python3 scripts/apply_kit.py --project-root /games/MyGame --profile 3d
    python3 scripts/apply_kit.py --project-root /games/MyGame --profile 2d \
        --mode rebase --dry-run
"""

from __future__ import annotations

import argparse
import os
import shutil
import sys
from pathlib import Path

KIT_ROOT = Path(__file__).resolve().parent.parent
TEMPLATES = KIT_ROOT / "templates"

DIRS = [
    "Docs",
    "Docs/Visual",
    "Docs/Visual/Reference",
    "Docs/Visual/Reference/GoldenViews",
    "Docs/Code",
    "Docs/Code/Tasks",
    "Assets/Editor/AIVisual",
    "Assets/VisualTests",
    "Assets/VisualTests/Screenshots",
    "Assets/Art/Approved",
    "Assets/Art/Experimental",
    "Assets/Art/Missing",
    "Tools",
]

SKILLS = ["visual-director", "unity-task-runner"]

# Both agents get the orchestration skills: Claude Code reads .claude/skills,
# Codex and the other agent CLIs read .agents/skills.
SKILL_DIRS = [".claude/skills", ".agents/skills"]

EDITOR_FILES = [
    "GameViewCapture.cs",
    "ConceptOverlay.cs",
    "VisualLinter.cs",
    "AIVisual.Editor.asmdef",
    "README.md",
]

CLAUDE_IMPORT = (
    "# CLAUDE.md\n\n"
    "This project's agent instructions live in AGENTS.md.\n\n"
    "@AGENTS.md\n"
)


class Applier:
    def __init__(self, project_root: Path, profile: str, mode: str,
                 force: bool, dry_run: bool) -> None:
        self.project_root = project_root
        self.profile = profile
        self.mode = mode
        self.force = force
        self.dry_run = dry_run
        self.created: list[Path] = []
        self.skipped: list[Path] = []

    def mkdir(self, path: Path) -> None:
        if path.exists():
            return
        if not self.dry_run:
            path.mkdir(parents=True, exist_ok=True)

    def copy(self, source: Path, destination: Path,
             replace: dict[str, str] | None = None) -> None:
        if not source.exists():
            print(f"WARNING: template missing: {source}", file=sys.stderr)
            return

        if destination.exists() and not self.force:
            self.skipped.append(destination)
            return

        if not self.dry_run:
            self.mkdir(destination.parent)
            if replace:
                content = source.read_text(encoding="utf-8")
                for key, value in replace.items():
                    content = content.replace(key, value)
                # UTF-8 without BOM, LF — keeps Unity and git diffs clean.
                destination.write_text(content, encoding="utf-8", newline="\n")
            else:
                shutil.copyfile(source, destination)

        self.created.append(destination)

    def link_claude_md(self) -> str:
        """Create CLAUDE.md pointing at AGENTS.md. Returns the strategy used."""
        target = self.project_root / "AGENTS.md"
        link = self.project_root / "CLAUDE.md"

        if link.exists() and not self.force:
            return "skipped (exists)"
        if self.dry_run:
            return "dry-run"
        if link.exists() or link.is_symlink():
            link.unlink()

        # Symlinks need admin rights or Developer Mode on Windows; hardlinks
        # need neither but some editors break them on save; the import file
        # always works.
        try:
            link.symlink_to(target.name)
            return "symlink"
        except (OSError, NotImplementedError):
            pass
        try:
            os.link(target, link)
            return "hardlink"
        except (OSError, NotImplementedError):
            pass
        link.write_text(CLAUDE_IMPORT, encoding="utf-8", newline="\n")
        return "import"

    def run(self) -> None:
        kit_root = str(KIT_ROOT)
        project_name = self.project_root.name

        print()
        print("Unity AI Development Pipeline Kit")
        print(f"  Kit    : {kit_root}")
        print(f"  Project: {self.project_root}")
        print(f"  Profile: {self.profile}")
        print(f"  Mode   : {self.mode}")
        if self.dry_run:
            print("  Dry run: nothing will be written")
        print()

        for directory in DIRS + [f"{base}/{s}" for base in SKILL_DIRS for s in SKILLS]:
            self.mkdir(self.project_root / directory)

        # Root agent docs — AGENTS.md is the entry point both agents read.
        self.copy(
            TEMPLATES / "project-root/AGENTS.md",
            self.project_root / "AGENTS.md",
            {
                "{KIT_ROOT}": kit_root,
                "{PROJECT_NAME}": project_name,
                "{3d|2d}": self.profile,
                "{greenfield|rebase}": self.mode,
            },
        )
        link_result = self.link_claude_md()

        # Pipeline state and specs.
        self.copy(
            TEMPLATES / "project-root/Docs/PIPELINE_STATE.md",
            self.project_root / "Docs/PIPELINE_STATE.md",
            {
                "{KIT_ROOT}": kit_root,
                "{NAME}": project_name,
                "{PATH}": str(self.project_root),
                "profile: 3d            # 3d | 2d":
                    f"profile: {self.profile}            # 3d | 2d",
                "mode: greenfield       # greenfield | rebase":
                    f"mode: {self.mode}       # greenfield | rebase",
            },
        )
        self.copy(
            TEMPLATES / f"project-root/Docs/Visual/VISUAL_SPEC.{self.profile}.yaml",
            self.project_root / "Docs/Visual/VISUAL_SPEC.yaml",
            {"{KIT_ROOT}": kit_root},
        )
        self.copy(
            TEMPLATES / "project-root/Docs/Visual/CONCEPT_ANALYSIS.yaml",
            self.project_root / "Docs/Visual/CONCEPT_ANALYSIS.yaml",
        )
        self.copy(
            TEMPLATES / "project-root/Docs/Visual/ASSET_CATALOG.json",
            self.project_root / "Docs/Visual/ASSET_CATALOG.json",
            {"{KIT_ROOT}": kit_root.replace("\\", "\\\\")},
        )
        self.copy(
            TEMPLATES / "project-root/Docs/Code/TASK_TEMPLATE.yaml",
            self.project_root / "Docs/Code/TASK_TEMPLATE.yaml",
            {"{KIT_ROOT}": kit_root},
        )

        for skill in SKILLS:
            for base in SKILL_DIRS:
                self.copy(
                    TEMPLATES / f"skills/{skill}/SKILL.md",
                    self.project_root / base / skill / "SKILL.md",
                    {"{KIT_ROOT}": kit_root},
                )

        for name in EDITOR_FILES:
            self.copy(
                TEMPLATES / f"unity/Editor/{name}",
                self.project_root / "Assets/Editor/AIVisual" / name,
            )

        self.report(link_result)

    def report(self, link_result: str) -> None:
        def rel(path: Path) -> str:
            try:
                return str(path.relative_to(self.project_root))
            except ValueError:
                return str(path)

        print(f"Created ({len(self.created)})")
        for path in self.created:
            print(f"  + {rel(path)}")

        if self.skipped:
            print()
            print(f"Skipped - already exists ({len(self.skipped)}); "
                  "use --force to overwrite")
            for path in self.skipped:
                print(f"  = {rel(path)}")

        print()
        print(f"CLAUDE.md link strategy: {link_result}")
        if link_result == "hardlink":
            print("  Note: some editors break hardlinks on save. For a true symlink,")
            print("  enable Windows Developer Mode or run elevated, then re-run --force.")

        print()
        print("Next steps")
        print("  1. Put concept art in Docs/Visual/Reference/Concept_Master.png")
        print("  2. Tell the agent: 'read AGENTS.md and continue the pipeline'")
        print("  3. The agent runs S0 bootstrap, then stops at the first decision")
        print("     it cannot make.")
        print()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Inject the Unity AI Development Pipeline Kit into a Unity project.")
    parser.add_argument("--project-root", required=True,
                        help="Unity project root — the directory holding Packages/manifest.json")
    parser.add_argument("--profile", required=True, choices=["3d", "2d"],
                        help="selects which VISUAL_SPEC template is installed")
    parser.add_argument("--mode", default="greenfield",
                        choices=["greenfield", "rebase"],
                        help="greenfield (new project) or rebase (visual rebuild)")
    parser.add_argument("--force", action="store_true",
                        help="overwrite files that already exist")
    parser.add_argument("--dry-run", action="store_true",
                        help="show what would happen without writing anything")
    args = parser.parse_args(argv)

    project_root = Path(args.project_root).expanduser().resolve()
    if not project_root.exists():
        print(f"ProjectRoot not found: {project_root}", file=sys.stderr)
        return 1

    if not (project_root / "Packages/manifest.json").exists():
        print(f"WARNING: Packages/manifest.json not found under {project_root}.",
              file=sys.stderr)
        print("WARNING: This does not look like a Unity project root. "
              "Kit files will still be written.", file=sys.stderr)

    Applier(project_root, args.profile, args.mode, args.force, args.dry_run).run()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
