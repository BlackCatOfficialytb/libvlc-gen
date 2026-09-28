#!/usr/bin/env python3
"""
libvlc-gen: Universal LibVLC Binary Generator
Fetches or builds LibVLC binaries for all supported platforms.
"""

import argparse
import hashlib
import os
import platform
import shutil
import subprocess
import sys
import tarfile
import tempfile
import zipfile
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from urllib.parse import urljoin

import requests
from tqdm import tqdm

try:
    from colorama import Fore, Style, init
    init(autoreset=True)
except ImportError:
    class Fore:
        RED = GREEN = YELLOW = BLUE = CYAN = MAGENTA = WHITE = RESET = ""
    class Style:
        BRIGHT = DIM = NORMAL = RESET_ALL = ""


VLC_REPO_URL = "https://code.videolan.org/videolan/vlc.git"
VLC_RELEASES_API = "https://code.videolan.org/api/v4/projects/videolan%2Fvlc/releases"
VLC_NIGHTLY_BASE = "https://artifacts.videolan.org/vlc/nightly"

TARGET_OS_CHOICES = ["ios", "android", "macos", "linux", "windows"]
ARCH_CHOICES = ["arm64", "armv7", "x86_64", "x86"]

OS_ARCH_MAP: Dict[str, List[str]] = {
    "ios": ["arm64", "armv7"],
    "android": ["arm64", "armv7", "x86_64", "x86"],
    "macos": ["arm64", "x86_64"],
    "linux": ["arm64", "x86_64", "x86"],
    "windows": ["arm64", "x86_64", "x86"],
}

HOST_OS_MAP = {
    "darwin": "macos",
    "linux": "linux",
    "win32": "windows",
}

HOST_ARCH_MAP = {
    "arm64": "arm64",
    "aarch64": "arm64",
    "x86_64": "x86_64",
    "amd64": "x86_64",
    "x86": "x86",
    "i386": "x86",
    "i686": "x86",
}


class Logger:
    @staticmethod
    def info(msg: str) -> None:
        print(f"{Fore.CYAN}[INFO]{Style.RESET_ALL} {msg}")

    @staticmethod
    def success(msg: str) -> None:
        print(f"{Fore.GREEN}[OK]{Style.RESET_ALL} {msg}")

    @staticmethod
    def warning(msg: str) -> None:
        print(f"{Fore.YELLOW}[WARN]{Style.RESET_ALL} {msg}")

    @staticmethod
    def error(msg: str) -> None:
        print(f"{Fore.RED}[ERROR]{Style.RESET_ALL} {msg}")

    @staticmethod
    def debug(msg: str) -> None:
        print(f"{Fore.MAGENTA}[DEBUG]{Style.RESET_ALL} {msg}")


def detect_host() -> Tuple[str, str]:
    sys_platform = sys.platform.lower()
    host_os = HOST_OS_MAP.get(sys_platform, "linux")
    host_arch = HOST_ARCH_MAP.get(platform.machine().lower(), "x86_64")
    return host_os, host_arch


def validate_os_arch(target_os: str, arch: str) -> bool:
    if target_os not in OS_ARCH_MAP:
        return False
    return arch in OS_ARCH_MAP[target_os]


def get_artifact_name(target_os: str, arch: str, mode: str) -> str:
    suffix = "prebuilt" if mode == "fetch" else "built"
    return f"libvlc-{target_os}-{arch}-{suffix}"


def run_cmd(cmd: List[str], cwd: Optional[Path] = None, env: Optional[Dict] = None, capture: bool = False) -> subprocess.CompletedProcess:
    Logger.debug(f"Running: {' '.join(cmd)}")
    result = subprocess.run(cmd, cwd=cwd, env=env, capture_output=capture, text=True)
    if result.returncode != 0 and capture:
        Logger.error(f"Command failed: {' '.join(cmd)}")
        Logger.error(f"stderr: {result.stderr}")
    return result


def download_file(url: str, dest: Path, chunk_size: int = 8192) -> bool:
    try:
        response = requests.get(url, stream=True, timeout=30)
        response.raise_for_status()
        total = int(response.headers.get('content-length', 0))
        with open(dest, 'wb') as f, tqdm(total=total, unit='B', unit_scale=True, desc=dest.name) as pbar:
            for chunk in response.iter_content(chunk_size=chunk_size):
                if chunk:
                    f.write(chunk)
                    pbar.update(len(chunk))
        return True
    except Exception as e:
        Logger.error(f"Download failed: {e}")
        return False


def extract_archive(archive: Path, dest: Path) -> bool:
    try:
        if archive.suffix == '.zip':
            with zipfile.ZipFile(archive, 'r') as zf:
                zf.extractall(dest)
        elif archive.suffix in ('.tar', '.gz', '.bz2', '.xz'):
            with tarfile.open(archive, 'r:*') as tf:
                tf.extractall(dest)
        else:
            Logger.error(f"Unsupported archive format: {archive.suffix}")
            return False
        return True
    except Exception as e:
        Logger.error(f"Extraction failed: {e}")
        return False


def find_vlc_artifacts(search_root: Path, target_os: str) -> Tuple[List[Path], List[Path]]:
    libs = []
    headers = []
    lib_patterns = {
        "ios": ["*.a", "*.dylib"],
        "android": ["*.so", "*.a"],
        "macos": ["*.dylib", "*.a"],
        "linux": ["*.so", "*.a"],
        "windows": ["*.dll", "*.lib", "*.pdb"],
    }
    patterns = lib_patterns.get(target_os, ["*"])
    for pattern in patterns:
        libs.extend(search_root.rglob(pattern))
    headers.extend(search_root.rglob("*.h"))
    headers.extend(search_root.rglob("*.hpp"))
    return libs, headers


def organize_output(libs: List[Path], headers: List[Path], output_dir: Path, target_os: str, arch: str) -> Path:
    dist_dir = output_dir / f"{target_os}-{arch}"
    include_dir = dist_dir / "include" / "vlc"
    lib_dir = dist_dir / "lib"
    include_dir.mkdir(parents=True, exist_ok=True)
    lib_dir.mkdir(parents=True, exist_ok=True)

    for h in headers:
        rel = h.name
        if "vlc" in str(h.parent).lower() or "include" in str(h.parent).lower():
            dest = include_dir / rel
            if not dest.exists():
                shutil.copy2(h, dest)

    for lib in libs:
        dest = lib_dir / lib.name
        if not dest.exists():
            shutil.copy2(lib, dest)

    return dist_dir


def print_summary(dist_dir: Path, target_os: str, arch: str) -> None:
    lib_dir = dist_dir / "lib"
    include_dir = dist_dir / "include" / "vlc"
    libs = list(lib_dir.glob("*")) if lib_dir.exists() else []
    headers = list(include_dir.glob("*")) if include_dir.exists() else []

    Logger.success(f"Output organized at: {dist_dir}")
    print(f"\n{Fore.BLUE}=== Artifact Summary ==={Style.RESET_ALL}")
    print(f"Target: {target_os}-{arch}")
    print(f"Headers ({len(headers)}):")
    for h in sorted(headers)[:20]:
        size = h.stat().st_size
        print(f"  {h.name} ({size:,} bytes)")
    if len(headers) > 20:
        print(f"  ... and {len(headers) - 20} more")

    print(f"\nLibraries ({len(libs)}):")
    for lib in sorted(libs):
        size = lib.stat().st_size
        print(f"  {lib.name} ({size:,} bytes)")

    total_size = sum(f.stat().st_size for f in libs + headers)
    print(f"\nTotal size: {total_size:,} bytes ({total_size / 1024 / 1024:.2f} MB)")


def fetch_prebuilt(target_os: str, arch: str, output_dir: Path) -> bool:
    Logger.info(f"Fetching prebuilt LibVLC for {target_os}-{arch}")
    
    if target_os == "android":
        return fetch_android_prebuilt(arch, output_dir)
    elif target_os == "ios":
        return fetch_ios_prebuilt(arch, output_dir)
    elif target_os == "macos":
        return fetch_macos_prebuilt(arch, output_dir)
    elif target_os == "linux":
        return fetch_linux_prebuilt(arch, output_dir)
    elif target_os == "windows":
        return fetch_windows_prebuilt(arch, output_dir)
    return False


def fetch_android_prebuilt(arch: str, output_dir: Path) -> bool:
    url_map = {
        "arm64": "arm64-v8a",
        "armv7": "armeabi-v7a",
        "x86_64": "x86_64",
        "x86": "x86",
    }
    abi = url_map.get(arch)
    if not abi:
        Logger.error(f"Unknown Android arch: {arch}")
        return False

    url = f"{VLC_NIGHTLY_BASE}/android/{abi}/libvlc-android-{abi}.zip"
    with tempfile.TemporaryDirectory() as tmp:
        archive = Path(tmp) / f"libvlc-android-{abi}.zip"
        if not download_file(url, archive):
            return False
        extract_dir = Path(tmp) / "extracted"
        if not extract_archive(archive, extract_dir):
            return False
        libs, headers = find_vlc_artifacts(extract_dir, "android")
        organize_output(libs, headers, output_dir, "android", arch)
    return True


def fetch_ios_prebuilt(arch: str, output_dir: Path) -> bool:
    url_map = {
        "arm64": "arm64",
        "armv7": "armv7",
    }
    ios_arch = url_map.get(arch)
    if not ios_arch:
        Logger.error(f"Unknown iOS arch: {arch}")
        return False

    url = f"{VLC_NIGHTLY_BASE}/ios/{ios_arch}/libvlc-ios-{ios_arch}.zip"
    with tempfile.TemporaryDirectory() as tmp:
        archive = Path(tmp) / f"libvlc-ios-{ios_arch}.zip"
        if not download_file(url, archive):
            return False
        extract_dir = Path(tmp) / "extracted"
        if not extract_archive(archive, extract_dir):
            return False
        libs, headers = find_vlc_artifacts(extract_dir, "ios")
        organize_output(libs, headers, output_dir, "ios", arch)
    return True


def fetch_macos_prebuilt(arch: str, output_dir: Path) -> bool:
    url_map = {
        "arm64": "arm64",
        "x86_64": "x86_64",
    }
    mac_arch = url_map.get(arch)
    if not mac_arch:
        Logger.error(f"Unknown macOS arch: {arch}")
        return False

    url = f"{VLC_NIGHTLY_BASE}/macos/{mac_arch}/libvlc-macos-{mac_arch}.tar.gz"
    with tempfile.TemporaryDirectory() as tmp:
        archive = Path(tmp) / f"libvlc-macos-{mac_arch}.tar.gz"
        if not download_file(url, archive):
            return False
        extract_dir = Path(tmp) / "extracted"
        if not extract_archive(archive, extract_dir):
            return False
        libs, headers = find_vlc_artifacts(extract_dir, "macos")
        organize_output(libs, headers, output_dir, "macos", arch)
    return True


def fetch_linux_prebuilt(arch: str, output_dir: Path) -> bool:
    url_map = {
        "x86_64": "x86_64",
        "arm64": "aarch64",
        "x86": "i686",
    }
    linux_arch = url_map.get(arch)
    if not linux_arch:
        Logger.error(f"Unknown Linux arch: {arch}")
        return False

    url = f"{VLC_NIGHTLY_BASE}/linux/{linux_arch}/libvlc-linux-{linux_arch}.tar.gz"
    with tempfile.TemporaryDirectory() as tmp:
        archive = Path(tmp) / f"libvlc-linux-{linux_arch}.tar.gz"
        if not download_file(url, archive):
            return False
        extract_dir = Path(tmp) / "extracted"
        if not extract_archive(archive, extract_dir):
            return False
        libs, headers = find_vlc_artifacts(extract_dir, "linux")
        organize_output(libs, headers, output_dir, "linux", arch)
    return True


def fetch_windows_prebuilt(arch: str, output_dir: Path) -> bool:
    url_map = {
        "x86_64": "x86_64",
        "arm64": "arm64",
        "x86": "x86",
    }
    win_arch = url_map.get(arch)
    if not win_arch:
        Logger.error(f"Unknown Windows arch: {arch}")
        return False

    url = f"{VLC_NIGHTLY_BASE}/win{'' if arch == 'x86_64' else '32'}/libvlc-win{'' if arch == 'x86_64' else '32'}-{win_arch}.zip"
    with tempfile.TemporaryDirectory() as tmp:
        archive = Path(tmp) / f"libvlc-win-{win_arch}.zip"
        if not download_file(url, archive):
            return False
        extract_dir = Path(tmp) / "extracted"
        if not extract_archive(archive, extract_dir):
            return False
        libs, headers = find_vlc_artifacts(extract_dir, "windows")
        organize_output(libs, headers, output_dir, "windows", arch)
    return True


def build_from_source(target_os: str, arch: str, output_dir: Path, source_url: str, branch: str = "master") -> bool:
    Logger.info(f"Building LibVLC from source for {target_os}-{arch}")
    
    with tempfile.TemporaryDirectory() as tmp:
        src_dir = Path(tmp) / "vlc"
        run_cmd(["git", "clone", "--depth", "1", "--branch", branch, source_url, str(src_dir)])
        
        if target_os == "android":
            return build_android(src_dir, arch, output_dir)
        elif target_os == "ios":
            return build_ios(src_dir, arch, output_dir)
        elif target_os == "macos":
            return build_macos(src_dir, arch, output_dir)
        elif target_os == "linux":
            return build_linux(src_dir, arch, output_dir)
        elif target_os == "windows":
            return build_windows(src_dir, arch, output_dir)
    return False


def build_android(src_dir: Path, arch: str, output_dir: Path) -> bool:
    Logger.warning("Android build requires NDK and proper toolchain setup")
    Logger.info("This is a placeholder - full Android build requires extensive NDK configuration")
    return False


def build_ios(src_dir: Path, arch: str, output_dir: Path) -> bool:
    Logger.warning("iOS build requires Xcode and proper toolchain setup")
    Logger.info("This is a placeholder - full iOS build requires extensive Xcode configuration")
    return False


def build_macos(src_dir: Path, arch: str, output_dir: Path) -> bool:
    build_dir = src_dir / "build"
    build_dir.mkdir(exist_ok=True)
    
    meson_args = [
        "meson", "setup", str(build_dir),
        f"-Dbuildtype=release",
        f"-Dc_args=-arch {arch}",
        f"-Dcpp_args=-arch {arch}",
        f"-Dlink_args=-arch {arch}",
        "-Dvulkan=disabled",
    ]
    
    result = run_cmd(meson_args, cwd=src_dir)
    if result.returncode != 0:
        return False
    
    result = run_cmd(["ninja", "-C", str(build_dir)], cwd=src_dir)
    if result.returncode != 0:
        return False
    
    libs, headers = find_vlc_artifacts(build_dir, "macos")
    organize_output(libs, headers, output_dir, "macos", arch)
    return True


def build_linux(src_dir: Path, arch: str, output_dir: Path) -> bool:
    build_dir = src_dir / "build"
    build_dir.mkdir(exist_ok=True)
    
    meson_args = [
        "meson", "setup", str(build_dir),
        "-Dbuildtype=release",
    ]
    
    if arch != "x86_64":
        meson_args.extend([f"--cross-file=build/cross/{arch}.meson"])
    
    result = run_cmd(meson_args, cwd=src_dir)
    if result.returncode != 0:
        return False
    
    result = run_cmd(["ninja", "-C", str(build_dir)], cwd=src_dir)
    if result.returncode != 0:
        return False
    
    libs, headers = find_vlc_artifacts(build_dir, "linux")
    organize_output(libs, headers, output_dir, "linux", arch)
    return True


def build_windows(src_dir: Path, arch: str, output_dir: Path) -> bool:
    Logger.warning("Windows build requires MSVC/MinGW and proper environment setup")
    Logger.info("This is a placeholder - full Windows build requires extensive toolchain configuration")
    return False


def create_package(dist_dir: Path, target_os: str, arch: str, mode: str) -> Path:
    package_name = get_artifact_name(target_os, arch, mode)
    package_path = dist_dir.parent / f"{package_name}.zip"
    
    with zipfile.ZipFile(package_path, 'w', zipfile.ZIP_DEFLATED) as zf:
        for file in dist_dir.rglob("*"):
            if file.is_file():
                arcname = file.relative_to(dist_dir.parent)
                zf.write(file, arcname)
    
    Logger.success(f"Created package: {package_path} ({package_path.stat().st_size:,} bytes)")
    return package_path


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Universal LibVLC Binary Generator",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Fetch prebuilt binaries for current platform
  python generate_libvlc.py --mode fetch
  
  # Fetch Android arm64 binaries
  python generate_libvlc.py --mode fetch --target-os android --arch arm64
  
  # Build from source for macOS arm64
  python generate_libvlc.py --mode build --target-os macos --arch arm64
  
  # Build iOS arm64 from specific branch
  python generate_libvlc.py --mode build --target-os ios --arch arm64 --branch 3.0
        """
    )
    
    host_os, host_arch = detect_host()
    
    parser.add_argument("--target-os", choices=TARGET_OS_CHOICES, default=host_os,
                        help=f"Target OS (default: auto-detect = {host_os})")
    parser.add_argument("--arch", choices=ARCH_CHOICES, default=host_arch,
                        help=f"Target architecture (default: auto-detect = {host_arch})")
    parser.add_argument("--mode", choices=["fetch", "build"], default="fetch",
                        help="Operation mode: fetch prebuilt or build from source (default: fetch)")
    parser.add_argument("--output-dir", type=Path, default=Path("./dist"),
                        help="Output directory (default: ./dist)")
    parser.add_argument("--source-url", default=VLC_REPO_URL,
                        help=f"VLC source repository URL (default: {VLC_REPO_URL})")
    parser.add_argument("--branch", default="master",
                        help="Git branch/tag to build (default: master)")
    parser.add_argument("--package", action="store_true",
                        help="Create zip package of output")
    parser.add_argument("--verbose", "-v", action="store_true",
                        help="Enable verbose output")
    
    args = parser.parse_args()
    
    if not validate_os_arch(args.target_os, args.arch):
        Logger.error(f"Invalid combination: {args.target_os}-{args.arch}")
        Logger.error(f"Valid architectures for {args.target_os}: {OS_ARCH_MAP[args.target_os]}")
        return 1
    
    args.output_dir.mkdir(parents=True, exist_ok=True)
    
    Logger.info(f"Target: {args.target_os}-{args.arch} | Mode: {args.mode}")
    Logger.info(f"Output: {args.output_dir.absolute()}")
    
    success = False
    if args.mode == "fetch":
        success = fetch_prebuilt(args.target_os, args.arch, args.output_dir)
    else:
        success = build_from_source(args.target_os, args.arch, args.output_dir, args.source_url, args.branch)
    
    if not success:
        Logger.error("Operation failed")
        return 1
    
    dist_dir = args.output_dir / f"{args.target_os}-{args.arch}"
    print_summary(dist_dir, args.target_os, args.arch)
    
    if args.package:
        create_package(dist_dir, args.target_os, args.arch, args.mode)
    
    Logger.success("Done!")
    return 0


if __name__ == "__main__":
    sys.exit(main())