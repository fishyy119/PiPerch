"""只读检查已安装包的资源，避免依赖源码仓库或当前工作目录。"""

from importlib.resources import files


def main() -> None:
    package = files("piperch")
    required_files = (
        "frontend/index.html",
        "frontend/THIRD_PARTY_LICENSES.md",
        "resources/pixiv_tags.sqlite",
        "resources/pixiv_tags.LICENSE",
        "resources/pixiv_tags.SOURCE.json",
        "database/migrations/env.py",
        "database/migrations/script.py.mako",
    )
    for relative_path in required_files:
        with package.joinpath(relative_path).open("rb") as resource:
            if not resource.read(1):
                raise RuntimeError(f"包内资源为空: {relative_path}")

    versions = package.joinpath("database/migrations/versions")
    if not any(
        entry.is_file() and entry.name.endswith(".py") and entry.name != "__init__.py" for entry in versions.iterdir()
    ):
        raise RuntimeError("包内缺少数据库迁移版本文件。")

    print("包内资源检查通过。")


if __name__ == "__main__":
    main()
