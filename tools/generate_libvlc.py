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
VLC_STABLE_BASE = "https://get.videolan.org/vlc"

TARGET_OS_CHOICES = ["ios", "android", "macos", "linux", "windows", "freebsd"]
ARCH_CHOICES = ["arm64", "armv7", "x86_64", "x86"]

OS_ARCH_MAP: Dict[str, List[str]] = {
    "ios": ["arm64", "armv7"],
    "android": ["arm64", "armv7", "x86_64", "x86"],
    "macos": ["arm64", "x86_64"],
    "linux": ["arm64", "x86_64", "x86"],
    "windows": ["arm64", "x86_64", "x86"],
    "freebsd": ["arm64", "x86_64"],
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
    elif target_os == "freebsd":
        return fetch_freebsd_prebuilt(arch, output_dir)
    return False


def try_download(url: str, archive: Path) -> bool:
    """Try to download a file, return False on 404 or other errors."""
    try:
        response = requests.get(url, stream=True, timeout=30)
        if response.status_code == 404:
            Logger.warning(f"Not found (404): {url}")
            return False
        response.raise_for_status()
        total = int(response.headers.get('content-length', 0))
        with open(archive, 'wb') as f, tqdm(total=total, unit='B', unit_scale=True, desc=archive.name) as pbar:
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)
                    pbar.update(len(chunk))
        return True
    except requests.RequestException as e:
        Logger.warning(f"Download failed: {url} - {e}")
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

    urls = [
        f"{VLC_NIGHTLY_BASE}/android/{abi}/libvlc-android-{abi}.zip",
        f"{VLC_STABLE_BASE}/latest/android/{abi}/libvlc-android-{abi}.zip",
    ]
    
    with tempfile.TemporaryDirectory() as tmp:
        archive = Path(tmp) / f"libvlc-android-{abi}.zip"
        for url in urls:
            Logger.info(f"Trying: {url}")
            if try_download(url, archive):
                break
        else:
            Logger.error(f"All download attempts failed for Android {abi}")
            return False
        
        extract_dir = Path(tmp) / "extracted"
        if not extract_archive(archive, extract_dir):
            return False
        libs, headers = find_vlc_artifacts(extract_dir, "android")
        if not libs and not headers:
            Logger.warning(f"No LibVLC artifacts found in Android {abi} package")
            return False
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

    urls = [
        f"{VLC_NIGHTLY_BASE}/ios/{ios_arch}/libvlc-ios-{ios_arch}.zip",
        f"{VLC_STABLE_BASE}/latest/ios/{ios_arch}/libvlc-ios-{ios_arch}.zip",
    ]
    
    with tempfile.TemporaryDirectory() as tmp:
        archive = Path(tmp) / f"libvlc-ios-{ios_arch}.zip"
        for url in urls:
            Logger.info(f"Trying: {url}")
            if try_download(url, archive):
                break
        else:
            Logger.error(f"All download attempts failed for iOS {ios_arch}")
            return False
        
        extract_dir = Path(tmp) / "extracted"
        if not extract_archive(archive, extract_dir):
            return False
        libs, headers = find_vlc_artifacts(extract_dir, "ios")
        if not libs and not headers:
            Logger.warning(f"No LibVLC artifacts found in iOS {ios_arch} package")
            return False
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

    urls = [
        f"{VLC_NIGHTLY_BASE}/macos/{mac_arch}/libvlc-macos-{mac_arch}.tar.gz",
        f"{VLC_STABLE_BASE}/latest/macos/{mac_arch}/libvlc-macos-{mac_arch}.tar.gz",
    ]
    
    with tempfile.TemporaryDirectory() as tmp:
        archive = Path(tmp) / f"libvlc-macos-{mac_arch}.tar.gz"
        for url in urls:
            Logger.info(f"Trying: {url}")
            if try_download(url, archive):
                break
        else:
            Logger.error(f"All download attempts failed for macOS {mac_arch}")
            return False
        
        extract_dir = Path(tmp) / "extracted"
        if not extract_archive(archive, extract_dir):
            return False
        libs, headers = find_vlc_artifacts(extract_dir, "macos")
        if not libs and not headers:
            Logger.warning(f"No LibVLC artifacts found in macOS {mac_arch} package")
            return False
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

    urls = [
        f"{VLC_NIGHTLY_BASE}/linux/{linux_arch}/libvlc-linux-{linux_arch}.tar.gz",
        f"{VLC_STABLE_BASE}/latest/linux/{linux_arch}/libvlc-linux-{linux_arch}.tar.gz",
    ]
    
    with tempfile.TemporaryDirectory() as tmp:
        archive = Path(tmp) / f"libvlc-linux-{linux_arch}.tar.gz"
        for url in urls:
            Logger.info(f"Trying: {url}")
            if try_download(url, archive):
                break
        else:
            Logger.error(f"All download attempts failed for Linux {linux_arch}")
            return False
        
        extract_dir = Path(tmp) / "extracted"
        if not extract_archive(archive, extract_dir):
            return False
        libs, headers = find_vlc_artifacts(extract_dir, "linux")
        if not libs and not headers:
            Logger.warning(f"No LibVLC artifacts found in Linux {linux_arch} package")
            return False
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

    urls = [
        f"{VLC_NIGHTLY_BASE}/win64/libvlc-win64-{win_arch}.zip",
        f"{VLC_STABLE_BASE}/latest/win64/libvlc-win64-{win_arch}.zip",
    ]
    
    with tempfile.TemporaryDirectory() as tmp:
        archive = Path(tmp) / f"libvlc-win64-{win_arch}.zip"
        for url in urls:
            Logger.info(f"Trying: {url}")
            if try_download(url, archive):
                break
        else:
            Logger.error(f"All download attempts failed for Windows {win_arch}")
            return False
        
        extract_dir = Path(tmp) / "extracted"
        if not extract_archive(archive, extract_dir):
            return False
        libs, headers = find_vlc_artifacts(extract_dir, "windows")
        if not libs and not headers:
            Logger.warning(f"No LibVLC artifacts found in Windows {win_arch} package")
            return False
        organize_output(libs, headers, output_dir, "windows", arch)
    return True

def fetch_freebsd_prebuilt(arch: str, output_dir: Path) -> bool:
    Logger.warning("FreeBSD prebuilt binaries not available from official sources")
    return False


def build_from_source(target_os: str, arch: str, output_dir: Path, source_url: str, branch: str = "master", compiler: str = "gcc") -> bool:
    Logger.info(f"Building LibVLC from source for {target_os}-{arch} (compiler: {compiler})")
    
    with tempfile.TemporaryDirectory() as tmp:
        src_dir = Path(tmp) / "vlc"
        Logger.info(f"Cloning {source_url} (branch: {branch})")
        result = run_cmd(["git", "clone", "--depth", "1", "--branch", branch, source_url, str(src_dir)])
        if result.returncode != 0:
            return False
        
        if target_os == "android":
            return build_android(src_dir, arch, output_dir)
        elif target_os == "ios":
            return build_ios(src_dir, arch, output_dir)
        elif target_os == "macos":
            return build_macos(src_dir, arch, output_dir)
        elif target_os == "linux":
            return build_linux(src_dir, arch, output_dir, compiler)
        elif target_os == "windows":
            return build_windows(src_dir, arch, output_dir, compiler)
        elif target_os == "freebsd":
            return build_freebsd(src_dir, arch, output_dir)
    return False


def build_android(src_dir: Path, arch: str, output_dir: Path) -> bool:
    ndk_home = os.environ.get("ANDROID_NDK_HOME")
    if not ndk_home:
        Logger.error("ANDROID_NDK_HOME not set. Install Android NDK r27b+ and set ANDROID_NDK_HOME")
        return False
    
    abi_map = {"arm64": "arm64-v8a", "armv7": "armeabi-v7a", "x86_64": "x86_64", "x86": "x86"}
    ndk_arch_map = {"arm64": "aarch64", "armv7": "arm", "x86_64": "x86_64", "x86": "i686"}
    api_map = {"arm64": 21, "armv7": 21, "x86_64": 21, "x86": 21}
    
    abi = abi_map.get(arch)
    ndk_arch = ndk_arch_map.get(arch)
    api = api_map.get(arch)
    
    if not all([abi, ndk_arch, api]):
        Logger.error(f"Unsupported Android arch: {arch}")
        return False
    
    build_dir = src_dir / f"build-android-{arch}"
    build_dir.mkdir(exist_ok=True)
    
    cross_file = src_dir / f"cross-android-{arch}.meson"
    cross_content = f"""
[binaries]
c = '{ndk_arch}-linux-android{api}-clang'
cpp = '{ndk_arch}-linux-android{api}-clang++'
ar = '{ndk_arch}-linux-android-ar'
strip = '{ndk_arch}-linux-android-strip'
pkg-config = 'pkg-config'

[host_machine]
system = 'linux'
cpu_family = '{'aarch64' if arch == 'arm64' else 'arm' if arch == 'armv7' else arch}'
cpu = '{ndk_arch}'
endian = 'little'

[built-in options]
c_args = ['-fPIC']
cpp_args = ['-fPIC', '-frtti', '-fexceptions']
link_args = ['-fPIC']
"""
    cross_file.write_text(cross_content.strip())
    
    env = os.environ.copy()
    env["PATH"] = f"{ndk_home}/toolchains/llvm/prebuilt/linux-x86_64/bin:" + env["PATH"]
    env["ANDROID_NDK_HOME"] = ndk_home
    
    meson_args = [
        "meson", "setup", str(build_dir),
        f"--cross-file={cross_file}",
        "-Dbuildtype=release",
        "-Dvulkan=disabled",
        "-Dlua=disabled",
    ]
    
    result = run_cmd(meson_args, cwd=src_dir, env=env)
    if result.returncode != 0:
        return False
    
    result = run_cmd(["ninja", "-C", str(build_dir), f"-j{os.cpu_count()}"], cwd=src_dir, env=env)
    if result.returncode != 0:
        return False
    
    libs, headers = find_vlc_artifacts(build_dir, "android")
    organize_output(libs, headers, output_dir, "android", arch)
    return True


def build_ios(src_dir: Path, arch: str, output_dir: Path) -> bool:
    sdk_map = {"arm64": "iphoneos", "armv7": "iphoneos"}
    deployment_map = {"arm64": "13.0", "armv7": "13.0"}
    
    sdk = sdk_map.get(arch)
    deployment = deployment_map.get(arch)
    
    if not sdk:
        Logger.error(f"Unsupported iOS arch: {arch}")
        return False
    
    build_dir = src_dir / f"build-ios-{arch}"
    build_dir.mkdir(exist_ok=True)
    
    cross_file = src_dir / f"cross-ios-{arch}.meson"
    cpu_family = "aarch64" if arch == "arm64" else "arm"
    sdk_path = f'/Applications/Xcode.app/Contents/Developer/Platforms/{sdk}.platform/Developer/SDKs/{sdk}.sdk'
    cross_content = f"""
[binaries]
c = 'clang'
cpp = 'clang++'
objc = 'clang'
objcpp = 'clang++'
ar = 'xcrun -sdk {sdk} ar'
strip = 'xcrun -sdk {sdk} strip'
pkg-config = 'pkg-config'

[host_machine]
system = 'darwin'
cpu_family = '{cpu_family}'
cpu = '{arch}'
endian = 'little'

[built-in options]
c_args = ['-arch', '{arch}', '-isysroot', '{sdk_path}', '-miphoneos-version-min={deployment}']
cpp_args = ['-arch', '{arch}', '-isysroot', '{sdk_path}', '-miphoneos-version-min={deployment}']
objc_args = ['-arch', '{arch}', '-isysroot', '{sdk_path}', '-miphoneos-version-min={deployment}']
objcpp_args = ['-arch', '{arch}', '-isysroot', '{sdk_path}', '-miphoneos-version-min={deployment}']
link_args = ['-arch', '{arch}', '-isysroot', '{sdk_path}', '-miphoneos-version-min={deployment}']
"""
    cross_file.write_text(cross_content.strip())
    
    meson_args = [
        "meson", "setup", str(build_dir),
        f"--cross-file={cross_file}",
        "-Dbuildtype=release",
        "-Dvulkan=disabled",
        "-Dlua=disabled",
    ]
    
    result = run_cmd(meson_args, cwd=src_dir)
    if result.returncode != 0:
        return False
    
    result = run_cmd(["ninja", "-C", str(build_dir), f"-j{os.cpu_count()}"], cwd=src_dir)
    if result.returncode != 0:
        return False
    
    libs, headers = find_vlc_artifacts(build_dir, "ios")
    organize_output(libs, headers, output_dir, "ios", arch)
    return True


def build_macos(src_dir: Path, arch: str, output_dir: Path) -> bool:
    deployment_map = {"arm64": "11.0", "x86_64": "10.15"}
    deployment = deployment_map.get(arch, "10.15")
    
    build_dir = src_dir / f"build-macos-{arch}"
    build_dir.mkdir(exist_ok=True)
    
    cross_file = src_dir / f"cross-macos-{arch}.meson"
    cpu_family = "aarch64" if arch == "arm64" else "x86_64"
    cross_content = f"""
[binaries]
c = 'clang'
cpp = 'clang++'
objc = 'clang'
objcpp = 'clang++'
ar = 'ar'
strip = 'strip'
pkg-config = 'pkg-config'

[host_machine]
system = 'darwin'
cpu_family = '{cpu_family}'
cpu = '{arch}'
endian = 'little'

[built-in options]
c_args = ['-arch', '{arch}', '-mmacosx-version-min={deployment}']
cpp_args = ['-arch', '{arch}', '-mmacosx-version-min={deployment}']
objc_args = ['-arch', '{arch}', '-mmacosx-version-min={deployment}']
objcpp_args = ['-arch', '{arch}', '-mmacosx-version-min={deployment}']
link_args = ['-arch', '{arch}', '-mmacosx-version-min={deployment}']
"""
    cross_file.write_text(cross_content.strip())
    
    meson_args = [
        "meson", "setup", str(build_dir),
        f"--cross-file={cross_file}",
        "-Dbuildtype=release",
        "-Dvulkan=disabled",
    ]
    
    result = run_cmd(meson_args, cwd=src_dir)
    if result.returncode != 0:
        return False
    
    result = run_cmd(["ninja", "-C", str(build_dir), f"-j{os.cpu_count()}"], cwd=src_dir)
    if result.returncode != 0:
        return False
    
    libs, headers = find_vlc_artifacts(build_dir, "macos")
    organize_output(libs, headers, output_dir, "macos", arch)
    return True


def build_linux(src_dir: Path, arch: str, output_dir: Path, compiler: str = "gcc") -> bool:
    build_dir = src_dir / f"build-linux-{arch}-{compiler}"
    build_dir.mkdir(exist_ok=True)
    
    meson_args = ["meson", "setup", str(build_dir), "-Dbuildtype=release", "-Dvulkan=disabled"]
    
    if arch != "x86_64":
        cross_file = src_dir / f"cross-linux-{arch}-{compiler}.meson"
        if compiler == "clang":
            if arch == "arm64":
                cross_content = """
[binaries]
c = 'clang'
cpp = 'clang++'
ar = 'llvm-ar'
strip = 'llvm-strip'
pkg-config = 'pkg-config'

[host_machine]
system = 'linux'
cpu_family = 'aarch64'
cpu = 'arm64'
endian = 'little'

[built-in options]
c_args = ['-fPIC']
cpp_args = ['-fPIC', '-frtti', '-fexceptions']
link_args = ['-fPIC']
"""
            elif arch == "x86":
                cross_content = """
[binaries]
c = 'clang'
cpp = 'clang++'
ar = 'llvm-ar'
strip = 'llvm-strip'
pkg-config = 'pkg-config'

[host_machine]
system = 'linux'
cpu_family = 'x86'
cpu = 'i686'
endian = 'little'

[built-in options]
c_args = ['-fPIC']
cpp_args = ['-fPIC', '-frtti', '-fexceptions']
link_args = ['-fPIC']
"""
            else:
                Logger.error(f"Unsupported Linux cross-compile arch for clang: {arch}")
                return False
        else:  # gcc
            if arch == "arm64":
                cross_content = """
[binaries]
c = 'aarch64-linux-gnu-gcc'
cpp = 'aarch64-linux-gnu-g++'
ar = 'aarch64-linux-gnu-ar'
strip = 'aarch64-linux-gnu-strip'
pkg-config = 'aarch64-linux-gnu-pkg-config'

[host_machine]
system = 'linux'
cpu_family = 'aarch64'
cpu = 'arm64'
endian = 'little'

[built-in options]
c_args = ['-fPIC']
cpp_args = ['-fPIC', '-frtti', '-fexceptions']
link_args = ['-fPIC']
"""
            elif arch == "x86":
                cross_content = """
[binaries]
c = 'i686-linux-gnu-gcc'
cpp = 'i686-linux-gnu-g++'
ar = 'i686-linux-gnu-ar'
strip = 'i686-linux-gnu-strip'
pkg-config = 'i686-linux-gnu-pkg-config'

[host_machine]
system = 'linux'
cpu_family = 'x86'
cpu = 'i686'
endian = 'little'

[built-in options]
c_args = ['-fPIC']
cpp_args = ['-fPIC', '-frtti', '-fexceptions']
link_args = ['-fPIC']
"""
            else:
                Logger.error(f"Unsupported Linux cross-compile arch for gcc: {arch}")
                return False
        cross_file.write_text(cross_content.strip())
        meson_args.extend([f"--cross-file={cross_file}"])
    else:
        # Native build - set compiler via environment
        if compiler == "clang":
            env = os.environ.copy()
            env["CC"] = "clang"
            env["CXX"] = "clang++"
        else:
            env = os.environ.copy()
            env["CC"] = "gcc"
            env["CXX"] = "g++"
    
    result = run_cmd(meson_args, cwd=src_dir, env=env if arch == "x86_64" else None)
    if result.returncode != 0:
        return False
    
    result = run_cmd(["ninja", "-C", str(build_dir), f"-j{os.cpu_count()}"], cwd=src_dir, env=env if arch == "x86_64" else None)
    if result.returncode != 0:
        return False
    
    libs, headers = find_vlc_artifacts(build_dir, "linux")
    organize_output(libs, headers, output_dir, "linux", f"{arch}-{compiler}")
    return True


def build_windows(src_dir: Path, arch: str, output_dir: Path, compiler: str = "msvc") -> bool:
    build_dir = src_dir / f"build-windows-{arch}-{compiler}"
    build_dir.mkdir(exist_ok=True)
    
    vs_arch_map = {"x86_64": "x64", "arm64": "arm64", "x86": "x86"}
    meson_arch_map = {"x86_64": "x86_64", "arm64": "arm64", "x86": "x86"}
    
    vs_arch = vs_arch_map.get(arch)
    meson_arch = meson_arch_map.get(arch)
    
    if not vs_arch or not meson_arch:
        Logger.error(f"Unsupported Windows arch: {arch}")
        return False
    
    cross_file = src_dir / f"cross-windows-{arch}-{compiler}.meson"
    
    if compiler == "clang-cl":
        cross_content = f"""
[binaries]
c = 'clang-cl'
cpp = 'clang-cl'
ar = 'llvm-lib'
link = 'lld-link'
pkg-config = 'pkg-config'

[host_machine]
system = 'windows'
cpu_family = '{meson_arch}'
cpu = '{meson_arch}'
endian = 'little'

[built-in options]
c_args = ['/MD', '/D_CRT_SECURE_NO_WARNINGS']
cpp_args = ['/MD', '/D_CRT_SECURE_NO_WARNINGS', '/EHsc']
link_args = ['/MANIFEST:NO']
"""
    else:  # msvc
        cross_content = f"""
[binaries]
c = 'cl'
cpp = 'cl'
ar = 'lib'
link = 'link'
pkg-config = 'pkg-config'

[host_machine]
system = 'windows'
cpu_family = '{meson_arch}'
cpu = '{meson_arch}'
endian = 'little'

[built-in options]
c_args = ['/MD', '/D_CRT_SECURE_NO_WARNINGS']
cpp_args = ['/MD', '/D_CRT_SECURE_NO_WARNINGS', '/EHsc']
link_args = ['/MANIFEST:NO']
"""
    cross_file.write_text(cross_content.strip())
    
    meson_args = [
        "meson", "setup", str(build_dir),
        f"--cross-file={cross_file}",
        "-Dbuildtype=release",
        "-Dvulkan=disabled",
        "-Dlua=disabled",
    ]
    
    # Setup MSVC environment
    vcvars_path = r"C:\Program Files\Microsoft Visual Studio\2022\Enterprise\VC\Auxiliary\Build\vcvarsall.bat"
    if not os.path.exists(vcvars_path):
        vcvars_path = r"C:\Program Files\Microsoft Visual Studio\2022\Community\VC\Auxiliary\Build\vcvarsall.bat"
    if not os.path.exists(vcvars_path):
        vcvars_path = r"C:\Program Files (x86)\Microsoft Visual Studio\2022\Enterprise\VC\Auxiliary\Build\vcvarsall.bat"
    
    if os.path.exists(vcvars_path):
        env = os.environ.copy()
        # Run vcvarsall to set up environment
        result = run_cmd(["cmd", "/c", f"\"{vcvars_path}\" {vs_arch} && set"], cwd=src_dir, capture=True)
        if result.returncode == 0:
            for line in result.stdout.splitlines():
                if "=" in line:
                    key, value = line.split("=", 1)
                    env[key] = value
    else:
        Logger.warning("vcvarsall.bat not found, using default environment")
        env = os.environ.copy()
    
    result = run_cmd(meson_args, cwd=src_dir, env=env)
    if result.returncode != 0:
        return False
    
    result = run_cmd(["ninja", "-C", str(build_dir), f"-j{os.cpu_count()}"], cwd=src_dir, env=env)
    if result.returncode != 0:
        return False
    
    libs, headers = find_vlc_artifacts(build_dir, "windows")
    organize_output(libs, headers, output_dir, "windows", f"{arch}-{compiler}")
    return True


def build_freebsd(src_dir: Path, arch: str, output_dir: Path) -> bool:
    build_dir = src_dir / f"build-freebsd-{arch}"
    build_dir.mkdir(exist_ok=True)
    
    meson_args = ["meson", "setup", str(build_dir), "-Dbuildtype=release", "-Dvulkan=disabled"]
    
    if arch == "arm64":
        cross_file = src_dir / f"cross-freebsd-{arch}.meson"
        cross_content = """
[binaries]
c = 'clang'
cpp = 'clang++'
ar = 'llvm-ar'
strip = 'llvm-strip'
pkg-config = 'pkgconf'

[host_machine]
system = 'freebsd'
cpu_family = 'aarch64'
cpu = 'arm64'
endian = 'little'

[built-in options]
c_args = ['-fPIC', '--target=aarch64-unknown-freebsd14']
cpp_args = ['-fPIC', '-frtti', '-fexceptions', '--target=aarch64-unknown-freebsd14']
link_args = ['-fPIC', '--target=aarch64-unknown-freebsd14']
"""
        cross_file.write_text(cross_content.strip())
        meson_args.extend([f"--cross-file={cross_file}"])
    else:
        # Native x86_64 build with clang
        env = os.environ.copy()
        env["CC"] = "clang"
        env["CXX"] = "clang++"
    
    result = run_cmd(meson_args, cwd=src_dir, env=env if arch == "x86_64" else None)
    if result.returncode != 0:
        return False
    
    result = run_cmd(["ninja", "-C", str(build_dir), f"-j{os.cpu_count()}"], cwd=src_dir, env=env if arch == "x86_64" else None)
    if result.returncode != 0:
        return False
    
    libs, headers = find_vlc_artifacts(build_dir, "freebsd")
    organize_output(libs, headers, output_dir, "freebsd", arch)
    return True


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
    parser.add_argument("--compiler", choices=["gcc", "clang", "msvc", "clang-cl"], default="gcc",
                        help="Compiler to use for build (default: gcc for Linux/FreeBSD, msvc for Windows)")
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
    if args.mode == "build":
        Logger.info(f"Compiler: {args.compiler}")
    Logger.info(f"Output: {args.output_dir.absolute()}")
    
    success = False
    if args.mode == "fetch":
        success = fetch_prebuilt(args.target_os, args.arch, args.output_dir)
    else:
        success = build_from_source(args.target_os, args.arch, args.output_dir, args.source_url, args.branch, args.compiler)
    
    if not success:
        Logger.error("Operation failed")
        return 1
    
    # Determine output directory name based on compiler for multi-compiler builds
    if args.mode == "build" and args.target_os in ["linux", "windows"]:
        dist_dir = args.output_dir / f"{args.target_os}-{args.arch}-{args.compiler}"
    else:
        dist_dir = args.output_dir / f"{args.target_os}-{args.arch}"
    print_summary(dist_dir, args.target_os, args.arch)
    
    if args.package:
        create_package(dist_dir, args.target_os, args.arch, args.mode)
    
    Logger.success("Done!")
    return 0


if __name__ == "__main__":
    sys.exit(main())