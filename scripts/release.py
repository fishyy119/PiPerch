"""构建、验证并按需上传 PiPerch 的 PyPI 发布包。"""

from __future__ import annotations

import argparse
import subprocess
import sys
import tempfile
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REPOSITORIES = ("testpypi", "pypi")


def run(command: str | list[str]) -> None:
    """固定命令交给 Shell，动态参数使用列表，任一步失败即中止发布。"""
    subprocess.run(command, cwd=ROOT, shell=isinstance(command, str), check=True)  # noqa: S603 - Shell 命令为固定字符串。


def release(repository: str | None) -> None:
    """构建并检查元数据，再按显式指定的目标上传同一份产物。"""
    with (ROOT / "pyproject.toml").open("rb") as configuration:
        version = tomllib.load(configuration)["project"]["version"]

    # 由 Corepack 按 package.json 中的 packageManager 路由 pnpm。
    run("corepack pnpm build")

    # 保留每次构建的独立目录，上传时只传递本次产物，避免混入旧版本。
    distribution = ROOT / "dist"
    distribution.mkdir(exist_ok=True)
    output = Path(tempfile.mkdtemp(prefix=f"release-{version}-", dir=distribution))

    run([sys.executable, "-m", "build", "--wheel", "--outdir", str(output)])
    wheel = next(output.glob("*.whl"))
    run([sys.executable, "-m", "twine", "check", "--strict", str(wheel)])

    if repository is not None:
        run([sys.executable, "-m", "twine", "upload", "--repository", repository, str(wheel)])


def main() -> None:
    parser = argparse.ArgumentParser(description="构建并验证 PiPerch 发布包，默认只在本地生成 wheel。")
    parser.add_argument("--upload", choices=REPOSITORIES, help="全部检查通过后上传到指定仓库，由 Twine 获取 Token")
    arguments = parser.parse_args()
    release(arguments.upload)


if __name__ == "__main__":
    main()
