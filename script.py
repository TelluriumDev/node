# coding: utf-8

import json
import os
import shutil
import glob
import subprocess
import hashlib
import urllib.request
import urllib.error

def file_sha256(file_path: str) -> str:
    sha256 = hashlib.sha256()
    with open(file_path, "rb") as file:
        for chunk in iter(lambda: file.read(4096), b""):
            sha256.update(chunk)
    return sha256.hexdigest()

def get_latest_release(repo: str) -> str | None:
    if not isinstance(repo, str): raise TypeError("repo must be a string")

    try:
        with urllib.request.urlopen(f"https://api.github.com/repos/{repo}/releases/latest") as response:
            return json.loads(response.read().decode('utf-8'))["tag_name"]
    except urllib.error.HTTPError: return None
    except urllib.error.URLError as e: raise e
    except Exception: return None

def main() -> None:
    node_version: str = get_latest_release("nodejs/node")
    print(f"当前nodejs/node版本: {node_version}")
    local_version: str = get_latest_release(os.environ.get("GITHUB_REPOSITORY") or "ZMBlocks/node")
    print(f"当前仓库版本: {local_version}")

    # if node_version == local_version:
    #     return print("最新版本的nodejs节点与本地存储库中的最新标签相同")
    
    print("克隆最新版本的nodejs节点...")
    node_version = "v22.17.0"
    subprocess.run(
        [
            "git",
            "clone",
            "--depth",
            "1",
            "--branch",
            node_version,
            "https://github.com/nodejs/node.git",
            "nodejs"
        ],
        shell=True,
        check=True
    )
    
    print("安装nasm...")
    subprocess.run(
        [
            "choco",
            "install",
            "nasm",
            "-y"
        ],
        shell=True,
        check=True
    )

    print("开始编译...")
    subprocess.run(
        [
            "vcbuild.bat",
            "release",
            "x64",
            "static",
            "dll",
            "package"
        ],
        shell=True,
        cwd="nodejs"
    )

    print("编译成功，开始打包...")
    print(f"7zip信息: {subprocess.run(["7z", "--help"], capture_output=True, text=True).stdout.split("\n")[1]}")

    os.makedirs("bin", exist_ok=True)
    os.makedirs("temp/lib", exist_ok=True)
    shutil.copy("nodejs/Release/libnode.dll", "bin/libnode.dll")
    subprocess.run(
        [
            "7z",
            "a",
            "-mm=Deflate",
            "-t7z",
            "../../bin/pdb.7z",
            "*.pdb"
        ],
        check=True,
        shell=True,
        cwd="nodejs/Release"
    )
    for file_path in glob.glob("nodejs/Release/**.lib", recursive=True):
        shutil.copy(file_path, "temp/lib")
    shutil.copytree(f"nodejs/Release/lib", "temp/lib", dirs_exist_ok=True)
    shutil.copytree(f"nodejs/Release/node-{node_version}-win-x64/include/node", "temp/include", dirs_exist_ok=True)
    subprocess.run(
        [
            "7z",
            "a",
            "-mm=Deflate",
            "-t7z",
            "../bin/sdk.7z",
            "*"
        ],
        check=True,
        shell=True,
        cwd="temp"
    )
    subprocess.run(
        [
            "7z",
            "a",
            "-mm=Deflate",
            "-t7z",
            "../../../../bin/node_modules.7z",
            f"*"
        ],
        check=True,
        shell=True,
        cwd=f"nodejs/Release/node-{node_version}-win-x64/node_modules"
    )
    print("打包成功，开始创建发行版")
    
    with open("content.txt", "w", encoding="utf-8") as file:
        file.write("\n".join([
            f"**Full Changelog**: https://github.com/nodejs/node/commits/{node_version}",
            f"",
            f"|       file      |                              sha256                              |",
            f"| --------------- | ---------------------------------------------------------------- |",
            f"|   libnode.dll   | {file_sha256("bin/libnode.dll")} |",
            f"|     pdb.7z      | {file_sha256("bin/pdb.7z")} |",
            f"|     sdk.7z      | {file_sha256("bin/sdk.7z")} |",
            f"| node_modules.7z | {file_sha256("bin/node_modules.7z")} |"
        ]))

    subprocess.run(
        [
            "gh",
            "release",
            "create",
            node_version,
            "--title",
            f"Release {node_version}",
            "--notes-file",
            "content.txt",
            "./bin/*"
        ],
        check=True,
        shell=True
    )
    
if __name__ == "__main__":
    main()
