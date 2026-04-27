"""Code execution sandbox using Docker."""

import asyncio
import tempfile
from pathlib import Path


def _image_for_lang(language: str) -> str:
    return {
        "python": "python:3.12-slim",
        "javascript": "node:20-slim",
        "bash": "debian:bookworm-slim",
        "ruby": "ruby:3.3-slim",
        "go": "golang:1.22-alpine",
        "rust": "rust:1.78-slim",
    }.get(language, "python:3.12-slim")


async def run(code: str, language: str, timeout: int = 30) -> dict:
    image = _image_for_lang(language)

    # Map language to file/cmd
    if language == "python":
        filename, cmd = "main.py", "python main.py"
    elif language == "javascript":
        filename, cmd = "main.js", "node main.js"
    elif language == "bash":
        filename, cmd = "script.sh", "bash script.sh"
    elif language == "ruby":
        filename, cmd = "main.rb", "ruby main.rb"
    elif language == "go":
        filename, cmd = "main.go", "go run main.go"
    elif language == "rust":
        filename, cmd = "main.rs", "rustc main.rs -o main && ./main"
    else:
        return {"stdout": "", "stderr": f"Unsupported language: {language}", "exit_code": 1, "execution_time": 0}

    with tempfile.TemporaryDirectory() as tmpdir:
        script_path = Path(tmpdir) / filename
        script_path.write_text(code)

        proc = await asyncio.create_subprocess_exec(
            "docker", "run", "--rm", "-v", f"{tmpdir}:/code", "-w", "/code",
            "--network", "none", "--memory", "256m", "--cpus", "1",
            image, "sh", "-c", cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        try:
            stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=timeout)
            return {
                "stdout": stdout.decode("utf-8", errors="replace")[:5000],
                "stderr": stderr.decode("utf-8", errors="replace")[:5000],
                "exit_code": proc.returncode or 0,
                "execution_time": timeout,
            }
        except asyncio.TimeoutError:
            proc.kill()
            return {
                "stdout": "",
                "stderr": f"Execution timed out after {timeout}s",
                "exit_code": 124,
                "execution_time": timeout,
            }
