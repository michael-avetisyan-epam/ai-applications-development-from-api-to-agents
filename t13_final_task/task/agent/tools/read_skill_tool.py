from pathlib import Path
from typing import Any

from t13_final_task.task.agent.tools.base import BaseTool


class ReadSkillTool(BaseTool):
    """Reads files from the local skills directory by path."""

    def __init__(self, skills_dir: Path):
        self._skills_dir = skills_dir.resolve()

    @property
    def name(self) -> str:
        return "read_skill"

    @property
    def description(self) -> str:
        return (
            "Read a skill file by its path. Use this to access skill instructions, "
            "scripts, references, or any other skill resource. "
            "Paths are relative to the skills root, e.g. /sample/SKILL.md "
        )

    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": (
                        "Path to the skill file relative to the skills root. "
                        "E.g. /sample/SKILL.md"
                    ),
                }
            },
            "required": ["path"],
        }

    async def _execute(self, arguments: dict[str, Any]) -> str:
        relative_path = str(arguments["path"]).lstrip("/")
        full_path = (self._skills_dir / relative_path).resolve()

        if not full_path.exists():
            return f"ERROR: File not found: {full_path}"
        if not full_path.is_file():
            return f"ERROR: Not a file: {full_path}"

        return full_path.read_text(encoding="utf-8")
