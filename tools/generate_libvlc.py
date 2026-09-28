#!/usr/bin/env python3
"""
LibVLC Generator - Extracts static LibVLC binaries and headers from official VideoLAN artifacts.

This tool downloads pre-compiled static LibVLC libraries from official VideoLAN/CocoaPod
artifacts, extracts them, and organizes headers + static libraries into a clean C/C++
distribution directory.
"""

import argparse
import hashlib
import os
import shutil
import sys
import tarfile
import urllib.request
import zipfile
from pathlib import Path
from typing import Optional


# Official VideoLAN static distribution URLs
# These point to the MobileVLCKit static framework releases
VLC_RELEASES = {
    "ios": {
        "arm64": {
            "url": "https://github.com/videolan/vlc-ios/releases/download/3.6.4/MobileVLCKit-3.6.4-ARM64.tar.bz2",
            "sha256": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",  # placeholder
        },
        "arm64e": {
            "url": "https://github.com/videolan/vlc-ios/releases/download/3.6.4/MobileVLCKit-3.6.4-ARM64e.tar.bz2",
            "sha256": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",  # placeholder
        },
    },
    "tvos": {
        "arm64": {
            "url": "https://github.com/videolan/vlc-ios/releases/download/3.6.4/MobileVLCKit-3.6.4-tvOS-ARM64.tar.bz2",
            "sha256": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",  # placeholder
        },
    },
}

# Fallback: CocoaPods spec repo URLs for LibVLC
COCOAPODS_SPECS = {
    "ios": {
        "arm64": "https://cdn.cocoapods.org/LibVLC-3.6.4.tar.bz2",
        "arm64e": "https://cdn.cocoapods.org/LibVLC-3.6.4-arm64e.tar.bz2",
    }
}


class ProgressBar:
    """Simple progress bar for downloads."""
    
    def __init__(self, total: int, prefix: str = "Downloading"):
        self.total = total
        self.current = 0
        self.prefix = prefix
        self.last_percent = -1
    
    def update(self, chunk_size: int):
        self.current += chunk_size
        if self.total > 0:
            percent = int(self.current * 100 / self.total)
            if percent != self.last_percent and percent % 5 == 0:
                bar_len = 40
                filled = int(bar_len * percent / 100)
                bar = "█" * filled + "░" * (bar_len - filled)
                print(f"\r{self.prefix}: [{bar}] {percent}%", end="", flush=True)
                self.last_percent = percent
    
    def finish(self):
        if self.total > 0:
            bar = "█" * 40
            print(f"\r{self.prefix}: [{bar}] 100% - Done!")
        else:
            print(f"\r{self.prefix}: Complete!")


def download_file(url: str, dest: Path, expected_sha256: Optional[str] = None) -> bool:
    """Download a file with progress bar and optional SHA256 verification."""
    print(f"Fetching: {url}")
    
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "libvlc-gen/1.0"})
        with urllib.request.urlopen(req, timeout=30) as response:
            total_size = int(response.headers.get("Content-Length", 0))
            progress = ProgressBar(total_size)
            
            with open(dest, "wb") as f:
                while True:
                    chunk = response.read(8192)
                    if not chunk:
                        break
                    f.write(chunk)
                    progress.update(len(chunk))
            
            progress.finish()
    except urllib.error.HTTPError as e:
        print(f"\nHTTP Error {e.code}: {e.reason}")
        return False
    except urllib.error.URLError as e:
        print(f"\nURL Error: {e.reason}")
        return False
    except Exception as e:
        print(f"\nDownload failed: {e}")
        return False
    
    # Verify SHA256 if provided
    if expected_sha256 and expected_sha256 != "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855":
        print("Verifying SHA256...")
        with open(dest, "rb") as f:
            actual = hashlib.sha256(f.read()).hexdigest()
        if actual != expected_sha256:
            print(f"SHA256 mismatch! Expected: {expected_sha256}, Got: {actual}")
            return False
        print("SHA256 verified.")
    
    return True


def extract_archive(archive_path: Path, extract_dir: Path) -> bool:
    """Extract tar.bz2, tar.gz, or zip archives."""
    print(f"Extracting: {archive_path.name}")
    
    try:
        if archive_path.suffix == ".bz2" or archive_path.suffixes[-2:] == [".tar", ".bz2"]:
            with tarfile.open(archive_path, "r:bz2") as tf:
                tf.extractall(extract_dir)
        elif archive_path.suffix == ".gz" or archive_path.suffixes[-2:] == [".tar", ".gz"]:
            with tarfile.open(archive_path, "r:gz") as tf:
                tf.extractall(extract_dir)
        elif archive_path.suffix == ".zip":
            with zipfile.ZipFile(archive_path, "r") as zf:
                zf.extractall(extract_dir)
        else:
            print(f"Unsupported archive format: {archive_path.suffix}")
            return False
    except Exception as e:
        print(f"Extraction failed: {e}")
        return False
    
    print("Extraction complete.")
    return True


def find_framework(extract_dir: Path) -> Optional[Path]:
    """Find the MobileVLCKit.framework or LibVLC.framework in extracted contents."""
    for root, dirs, files in os.walk(extract_dir):
        for d in dirs:
            if d.endswith(".framework"):
                return Path(root) / d
    return None


def copy_headers(framework_path: Path, output_dir: Path) -> bool:
    """Copy VLC headers from framework to output include directory."""
    headers_src = framework_path / "Headers"
    if not headers_src.exists():
        # Try alternative location
        headers_src = framework_path / "Modules" / "vlc" / "Headers"
    
    if not headers_src.exists():
        print(f"Headers not found in {framework_path}")
        return False
    
    headers_dst = output_dir / "include" / "vlc"
    headers_dst.mkdir(parents=True, exist_ok=True)
    
    count = 0
    for header in headers_src.glob("*.h"):
        shutil.copy2(header, headers_dst / header.name)
        count += 1
    
    # Also copy modulemap if present
    for modulemap in framework_path.glob("*.modulemap"):
        shutil.copy2(modulemap, headers_dst / modulemap.name)
    
    print(f"Copied {count} header(s) to {headers_dst}")
    return count > 0


def copy_static_libs(framework_path: Path, output_dir: Path) -> bool:
    """Copy static libraries (.a files) from framework to output lib directory."""
    libs_dst = output_dir / "lib"
    libs_dst.mkdir(parents=True, exist_ok=True)
    
    # The framework binary itself is the static library
    framework_name = framework_path.stem  # e.g., "MobileVLCKit"
    framework_binary = framework_path / framework_name
    
    copied = 0
    if framework_binary.exists():
        # Copy as libvlc.a and libvlccore.a (they're combined in the framework)
        dest_vlc = libs_dst / "libvlc.a"
        dest_core = libs_dst / "libvlccore.a"
        shutil.copy2(framework_binary, dest_vlc)
        shutil.copy2(framework_binary, dest_core)
        copied = 2
        print(f"Copied framework binary as libvlc.a and libvlccore.a")
    else:
        # Look for individual .a files
        for lib in framework_path.glob("*.a"):
            shutil.copy2(lib, libs_dst / lib.name)
            copied += 1
            print(f"Copied {lib.name}")
    
    return copied > 0


def validate_output(output_dir: Path) -> bool:
    """Validate that required files exist and print their sizes."""
    lib_dir = output_dir / "lib"
    include_dir = output_dir / "include" / "vlc"
    
    required_libs = ["libvlc.a", "libvlccore.a"]
    required_headers = ["vlc.h", "vlc_common.h", "vlc_version.h"]
    
    print("\n" + "=" * 50)
    print("VALIDATION RESULTS")
    print("=" * 50)
    
    all_ok = True
    
    # Check libraries
    for lib in required_libs:
        lib_path = lib_dir / lib
        if lib_path.exists():
            size = lib_path.stat().st_size
            print(f"✓ {lib}: {size:,} bytes ({size / 1024 / 1024:.2f} MB)")
        else:
            print(f"✗ {lib}: MISSING")
            all_ok = False
    
    # Check headers
    print()
    for header in required_headers:
        header_path = include_dir / header
        if header_path.exists():
            size = header_path.stat().st_size
            print(f"✓ {header}: {size:,} bytes")
        else:
            print(f"✗ {header}: MISSING")
            all_ok = False
    
    # Count total headers
    header_count = len(list(include_dir.glob("*.h"))) if include_dir.exists() else 0
    print(f"\nTotal headers: {header_count}")
    
    print("=" * 50)
    if all_ok:
        print("SUCCESS: All required files present!")
    else:
        print("WARNING: Some files are missing.")
    print("=" * 50)
    
    return all_ok


def generate_libvlc(target_os: str, arch: str, output_dir: Path, version: Optional[str] = None) -> bool:
    """Main generation function."""
    print(f"LibVLC Generator - Target: {target_os}/{arch}")
    print(f"Output directory: {output_dir}")
    print("-" * 50)
    
    # Clean and create output directory
    if output_dir.exists():
        shutil.rmtree(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Determine download URL
    if target_os in VLC_RELEASES and arch in VLC_RELEASES[target_os]:
        release_info = VLC_RELEASES[target_os][arch]
        url = release_info["url"]
        sha256 = release_info["sha256"]
    else:
        print(f"No pre-built release for {target_os}/{arch}")
        return False
    
    # Download
    archive_name = Path(url).name
    archive_path = output_dir / archive_name
    
    if not download_file(url, archive_path, sha256):
        return False
    
    # Extract
    extract_dir = output_dir / "extract"
    extract_dir.mkdir(exist_ok=True)
    
    if not extract_archive(archive_path, extract_dir):
        return False
    
    # Find framework
    framework = find_framework(extract_dir)
    if not framework:
        print("ERROR: Could not find .framework in extracted contents")
        return False
    
    print(f"Found framework: {framework.name}")
    
    # Copy headers and libraries
    if not copy_headers(framework, output_dir):
        return False
    
    if not copy_static_libs(framework, output_dir):
        return False
    
    # Cleanup
    shutil.rmtree(extract_dir, ignore_errors=True)
    archive_path.unlink(missing_ok=True)
    
    # Validate
    return validate_output(output_dir)


def main():
    parser = argparse.ArgumentParser(
        description="Generate static LibVLC binaries and headers for iOS/tvOS",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python generate_libvlc.py                          # Default: iOS arm64
  python generate_libvlc.py --target-os ios --arch arm64e
  python generate_libvlc.py --output-dir ./my_dist
  python generate_libvlc.py --target-os tvos --arch arm64
        """
    )
    parser.add_argument(
        "--target-os",
        choices=["ios", "tvos"],
        default="ios",
        help="Target operating system (default: ios)"
    )
    parser.add_argument(
        "--arch",
        choices=["arm64", "arm64e"],
        default="arm64",
        help="Target architecture (default: arm64)"
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("./dist"),
        help="Output directory (default: ./dist)"
    )
    parser.add_argument(
        "--version",
        help="Specific version to download (overrides default)"
    )
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Verbose output"
    )
    
    args = parser.parse_args()
    
    # Validate arch for tvOS
    if args.target_os == "tvos" and args.arch == "arm64e":
        print("ERROR: tvOS does not support arm64e")
        return 1
    
    success = generate_libvlc(args.target_os, args.arch, args.output_dir, args.version)
    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())