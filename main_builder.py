#!/usr/bin/env python3
# RetroArch AppImage Builder
# Copyright (C) 2026  retrogamermaster666
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

import os
import json
import shutil
import subprocess
import sys
import datetime
from pathlib import Path
import urllib.request

# Configuration
CONFIG_FILE = Path("config/config.json")
BUILD_DIR = Path("build_artifacts")
DIST_DIR = Path("dist")
APPDIR = BUILD_DIR / "RetroArch.AppDir"
LOG_FILE = Path("build.log")
JOBS = os.cpu_count() or 4

APPIMAGE_TOOL_URL = "https://github.com/AppImage/appimagetool/releases/download/continuous/appimagetool-aarch64.AppImage"
APPIMAGE_TOOL = BUILD_DIR / "appimagetool"

# Initialize Log File
log_stream = open(LOG_FILE, "a")

def log(message, end="\n"):
    """Logs a message to both stdout and the log file."""
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    formatted_msg = f"[{timestamp}] {message}"
    print(formatted_msg, end=end, flush=True)
    log_stream.write(formatted_msg + end)
    log_stream.flush()

def run(cmd, cwd=None, env=None, check=True):
    """Executes a command, streaming output to stdout and the log file in real-time."""
    cmd_str = ' '.join(map(str, cmd))
    log(f"RUNNING: {cmd_str}")
    
    process = subprocess.Popen(
        cmd,
        cwd=cwd,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1
    )
    
    for line in process.stdout:
        print(line, end='', flush=True)
        log_stream.write(line)
        log_stream.flush()
        
    process.wait()
    
    if check and process.returncode != 0:
        log(f"ERROR: Command failed with exit code {process.returncode}")
        raise subprocess.CalledProcessError(process.returncode, cmd)
    
    return process

def load_config():
    log(f"Loading configuration from {CONFIG_FILE}...")
    if not CONFIG_FILE.exists():
        log(f"FATAL ERROR: {CONFIG_FILE} not found!")
        sys.exit(1)
    with open(CONFIG_FILE, "r") as f:
        return json.load(f)

def setup_directories():
    log("Setting up build and distribution directories...")
    for d in [BUILD_DIR, DIST_DIR]:
        if not d.exists():
            d.mkdir(parents=True, exist_ok=True)
    
    APPDIR.mkdir(parents=True, exist_ok=True)
    (APPDIR / "usr" / "bin").mkdir(parents=True, exist_ok=True)
    (APPDIR / "usr" / "lib").mkdir(parents=True, exist_ok=True)
    (APPDIR / "usr" / "share" / "applications").mkdir(parents=True, exist_ok=True)
    (APPDIR / "usr" / "share" / "icons" / "hicolor" / "scalable" / "apps").mkdir(parents=True, exist_ok=True)

def install_dependencies():
    log("Checking and installing system dependencies...")
    deps = [
        "build-essential", "cmake", "git", "pkg-config", "libsdl2-dev", 
        "libasound2-dev", "libegl1-mesa-dev", "libgles2-mesa-dev", 
        "libudev-dev", "libx11-dev", "libvulkan-dev", "mesa-vulkan-drivers",
        "libgbm-dev", "libdrm-dev", "libpulse-dev", "libavcodec-dev", 
        "libavformat-dev", "libswscale-dev", "libfreetype6-dev", "libxml2-dev",
        "libusb-1.0-0-dev", "libhidapi-dev", "libzip-dev", "libass-dev", "vulkan-tools"
    ]
    try:
        run(["sudo", "apt-get", "update"])
        run(["sudo", "apt-get", "install", "-y"] + deps)
    except Exception as e:
        log(f"Warning: Dependency installation encountered an issue: {e}")

def build_retroarch(config):
    ra_config = config["retroarch"]
    ra_dir = BUILD_DIR / "RetroArch"
    
    log(f"--- Building RetroArch ({ra_config['version']}) ---")
    
    if ra_dir.exists():
        log("Updating existing RetroArch repository...")
        run(["git", "fetch", "--all"], cwd=ra_dir)
        run(["git", "checkout", ra_config["version"]], cwd=ra_dir)
    else:
        log(f"Cloning RetroArch repository...")
        run(["git", "clone", "--branch", ra_config["version"], "--depth", "1", ra_config["repo"], str(ra_dir)])

    log("Configuring RetroArch build...")
    configure_cmd = [
        "./configure",
        "--prefix=/usr",
        "--disable-videocore",
        "--disable-opengl1",
        "--enable-opengles",
        "--enable-opengles3",
        "--enable-opengles3_1",
        "--enable-vulkan",
        "--enable-kms",
        "--enable-egl",
        "--enable-udev",
        "--enable-hid",
        "--enable-alsa",
        "--enable-pulse",
        "--enable-ffmpeg",
        "--enable-freetype",
        "--enable-slang",
        "--enable-threads",
        "--enable-libusb",
        "--enable-networking"
    ]
    run(configure_cmd, cwd=ra_dir)

    log(f"Compiling RetroArch with {JOBS} jobs...")
    run(["make", f"-j{JOBS}"], cwd=ra_dir)
    
    log("Installing RetroArch to AppDir...")
    run(["make", "install", f"DESTDIR={APPDIR.resolve()}"], cwd=ra_dir)

def build_filters():
    log("--- Building Audio and Video Filters from Source ---")
    ra_dir = BUILD_DIR / "RetroArch"
    if not ra_dir.exists():
        log("ERROR: RetroArch source not found. Cannot build filters.")
        return

    # Audio Filters
    audio_filters_src = ra_dir / "libretro-common" / "audio" / "dsp_filters"
    if audio_filters_src.exists():
        log("Compiling audio filters...")
        try:
            run(["make", f"-j{JOBS}"], cwd=audio_filters_src)
            
            audio_filters_dest = APPDIR / "usr" / "share" / "retroarch" / "filters" / "audio"
            audio_filters_dest.mkdir(parents=True, exist_ok=True)
            
            # Copy .dsp and .so files
            for f in audio_filters_src.glob("*.dsp"):
                shutil.copy2(f, audio_filters_dest)
            for f in audio_filters_src.glob("*.so"):
                shutil.copy2(f, audio_filters_dest)
            log("Audio filters built and installed.")
        except Exception as e:
            log(f"Warning: Failed to build audio filters: {e}")
    else:
        log("Warning: Audio filters source not found.")

    # Video Filters
    video_filters_src = ra_dir / "gfx" / "video_filters"
    if video_filters_src.exists():
        log("Compiling video filters...")
        try:
            run(["make", f"-j{JOBS}"], cwd=video_filters_src)
            
            video_filters_dest = APPDIR / "usr" / "share" / "retroarch" / "filters" / "video"
            video_filters_dest.mkdir(parents=True, exist_ok=True)
            
            # Copy .filt and .so files
            for f in video_filters_src.glob("*.filt"):
                shutil.copy2(f, video_filters_dest)
            for f in video_filters_src.glob("*.so"):
                shutil.copy2(f, video_filters_dest)
                
            # Also copy snes_ntsc subdirectory if it exists
            snes_ntsc_src = video_filters_src / "snes_ntsc"
            if snes_ntsc_src.exists():
                shutil.copytree(snes_ntsc_src, video_filters_dest / "snes_ntsc", dirs_exist_ok=True)
            log("Video filters built and installed.")
        except Exception as e:
            log(f"Warning: Failed to build video filters: {e}")
    else:
        log("Warning: Video filters source not found.")

def build_cores(config):
    cores = config.get("core_to_build", [])
    if not cores:
        log("No cores specified to build in config.json.")
        return

    log(f"--- Building Cores: {', '.join(cores)} ---")
    
    super_dir = BUILD_DIR / "libretro-super"
    if super_dir.exists():
        log("Updating libretro-super repository...")
        run(["git", "pull"], cwd=super_dir)
    else:
        log("Cloning libretro-super repository...")
        run(["git", "clone", "--depth", "1", "https://github.com/libretro/libretro-super.git", str(super_dir)])

    log("Fetching core source codes...")
    for core in cores:
        log(f"Fetching {core}...")
        run(["./libretro-fetch.sh", core], cwd=super_dir)

    log(f"Compiling cores with {JOBS} jobs...")
    env = os.environ.copy()
    run(["./libretro-build.sh", f"-j{JOBS}"] + cores, cwd=super_dir, env=env)

    log("Copying built cores to AppDir...")
    cores_dest = APPDIR / "usr" / "lib" / "libretro"
    cores_dest.mkdir(parents=True, exist_ok=True)
    
    dist_dir = super_dir / "dist" / "unix"
    if dist_dir.exists():
        for core_file in dist_dir.glob("*.so"):
            log(f"Packaging core: {core_file.name}")
            shutil.copy2(core_file, cores_dest)
            
    log("Copying core info files...")
    info_dest = APPDIR / "usr" / "share" / "libretro" / "info"
    info_dest.mkdir(parents=True, exist_ok=True)
    info_src = super_dir / "dist" / "info"
    if info_src.exists():
        for info_file in info_src.glob("*.info"):
            shutil.copy2(info_file, info_dest)

def fetch_assets():
    log("--- Fetching Bundled Assets ---")
    assets_map = {
        "assets": "https://github.com/libretro/retroarch-assets.git",
        "database": "https://github.com/libretro/libretro-database.git",
        "autoconfig": "https://github.com/libretro/retroarch-joypad-autoconfig.git",
        "shaders/shaders_slang": "https://github.com/libretro/slang-shaders.git",
        "overlays": "https://github.com/libretro/common-overlays.git"
    }
    
    for name, url in assets_map.items():
        dest = APPDIR / "usr" / "share" / "retroarch" / name
        if not dest.exists():
            log(f"Cloning {name} bundle...")
            run(["git", "clone", "--depth", "1", url, str(dest)])
        else:
            log(f"Updating {name} bundle...")
            run(["git", "pull"], cwd=dest)

def prepare_appdir(config):
    log("--- Preparing AppImage Metadata ---")
    app_name = config["appimage"]["name"]
    version = config["retroarch"]["version"]
    clean_version = version.lstrip('v')
    
    log(f"Installing and configuring AppRun script for version {clean_version}...")
    with open("src/AppRun", "r") as f:
        apprun_content = f.read()
    
    # Inject actual version and app name into the script
    apprun_content = apprun_content.replace("VERSION_PLACEHOLDER", clean_version)
    apprun_content = apprun_content.replace("APP_NAME_PLACEHOLDER", app_name)
    apprun_content = apprun_content.replace("app-name-placeholder", app_name.lower().replace(" ", "-"))
    
    with open(APPDIR / "AppRun", "w") as f:
        f.write(apprun_content)
        
    run(["chmod", "+x", str(APPDIR / "AppRun")])
    
    log("Creating desktop entry...")
    desktop_content = f"""[Desktop Entry]
Name={app_name} {clean_version}
Exec=retroarch
Icon=retroarch
Type=Application
Categories=Game;Emulator;
Comment=Play classic games
"""
    with open(APPDIR / "retroarch.desktop", "w") as f:
        f.write(desktop_content)
    
    log("Locating and installing icon...")
    icon_name = config["appimage"].get("icon", "RetroArch.svg")
    possible_paths = [
        Path("resource") / icon_name,
    ]
    
    icon_installed = False
    for p in possible_paths:
        if p.exists():
            log(f"Icon found at: {p}")
            # Install to AppDir root for AppRun to find
            shutil.copy2(p, APPDIR / "retroarch.svg")
            # Also install to standard location
            shutil.copy2(p, APPDIR / "usr/share/icons/hicolor/scalable/apps/retroarch.svg")
            icon_installed = True
            break
            
    if not icon_installed:
        log(f"Warning: Icon {icon_name} not found in searched paths.")
    
    if not (APPDIR / ".DirIcon").exists() and (APPDIR / "retroarch.svg").exists():
        (APPDIR / ".DirIcon").symlink_to("retroarch.svg")

def download_appimagetool():
    if not APPIMAGE_TOOL.exists():
        log(f"Downloading appimagetool (aarch64) from GitHub...")
        urllib.request.urlretrieve(APPIMAGE_TOOL_URL, APPIMAGE_TOOL)
        run(["chmod", "+x", str(APPIMAGE_TOOL)])

def collect_build_info(config):
    """Gathers detailed system and library information about the build environment."""
    log("Collecting comprehensive build environment information...")
    info = []
    info.append("==========================================================")
    info.append("        RetroArch AppImage Build Information")
    info.append("==========================================================")
    info.append(f"Build Date:        {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    info.append(f"RetroArch Version: {config['retroarch']['version']}")
    info.append(f"Target Arch:       {config['appimage']['arch']}")
    
    # Included Cores
    cores = config.get("core_to_build", [])
    info.append(f"\n--- Included Cores ({len(cores)}) ---")
    info.append(", ".join(cores) if cores else "None")

    # OS Info
    try:
        os_info = subprocess.check_output(["cat", "/etc/os-release"], text=True)
        info.append("\n--- OS Information ---")
        for line in os_info.splitlines():
            if line.startswith(("PRETTY_NAME=", "NAME=", "VERSION=")):
                info.append(line.replace('"', '').strip())
    except: info.append("OS Info: Not available")

    # Critical Library Versions (Compatibility Check)
    info.append("\n--- Library & Tool Versions ---")
    
    # Glibc version (Most important for AppImage compatibility)
    try:
        ldd_out = subprocess.check_output(["ldd", "--version"], text=True).splitlines()[0]
        info.append(f"Glibc: {ldd_out}")
    except: pass

    # GCC version
    try:
        gcc_out = subprocess.check_output(["gcc", "--version"], text=True).splitlines()[0]
        info.append(f"Compiler: {gcc_out}")
    except: pass

    # SDL2 version
    try:
        sdl_out = subprocess.check_output(["sdl2-config", "--version"], text=True).strip()
        info.append(f"SDL2: {sdl_out}")
    except: pass

    # Hardware & Kernel
    try:
        kernel = subprocess.check_output(["uname", "-sr"], text=True)
        info.append(f"Kernel: {kernel.strip()}")
        if os.path.exists("/proc/device-tree/model"):
            with open("/proc/device-tree/model", "r") as f:
                info.append(f"Hardware Model: {f.read().strip()}")
        
        # Raspberry Pi specific memory split
        try:
            gpu_mem = subprocess.check_output(["vcgencmd", "get_mem", "gpu"], text=True).strip()
            arm_mem = subprocess.check_output(["vcgencmd", "get_mem", "arm"], text=True).strip()
            info.append(f"Pi GPU Allocated Memory: {gpu_mem}")
            info.append(f"Pi ARM Allocated Memory: {arm_mem}")
        except: pass
    except: pass

    # CPU & Graphics
    try:
        lscpu = subprocess.check_output(["lscpu"], text=True)
        info.append("\n--- CPU Information ---")
        for line in lscpu.splitlines():
            if line.startswith(("Architecture:", "CPU(s):", "Model name:")):
                info.append(line.strip())
        
        glx = subprocess.run(["glxinfo", "-B"], capture_output=True, text=True)
        if glx.returncode == 0:
            info.append("\n--- Graphics Information ---")
            for line in glx.stdout.splitlines():
                if line.strip().startswith("Device:"):
                    info.append(line.strip())
                if line.strip().startswith("Video memory:"):
                    # Clarify that this is shared memory
                    info.append(f"{line.strip()} (Shared System RAM)")
                if line.strip().startswith("OpenGL version string:"):
                    info.append(line.strip())
        
        # Try to get Vulkan version
        vulkan = subprocess.run(["vulkaninfo", "--summary"], capture_output=True, text=True)
        if vulkan.returncode == 0:
            info.append("\n--- Vulkan Information ---")
            for line in vulkan.stdout.splitlines():
                if "Vulkan Instance Version" in line:
                    info.append(line.strip())
                if "deviceName" in line or "driverName" in line or "apiVersion" in line:
                    # Only add if not redundant
                    line_strip = line.strip()
                    if line_strip not in info:
                        info.append(line_strip)
    except: pass

    # Compatibility Note for End Users
    info.append("\n" + "="*58)
    info.append("                COMPATIBILITY NOTE")
    info.append("="*58)
    info.append("1. OS: This AppImage requires a 64-bit Linux distribution.")
    info.append("2. Glibc: The target system must have a Glibc version equal to")
    info.append(f"   or newer than the one used during build ({ldd_out.split()[-1]}).")
    info.append("3. Drivers: Mesa drivers (Vulkan/OpenGL) are required for")
    info.append("   hardware acceleration.")
    info.append("4. Portable: Move the 'retroarch_portable_config' folder")
    info.append("   along with the AppImage to keep your saves and settings.")
    info.append("="*58)

    return "\n".join(info)

def create_appimage(config):
    log("--- Packaging AppImage ---")
    app_name = config["appimage"]["name"]
    arch = config["appimage"]["arch"]
    version = config["retroarch"]["version"]
    
    # Strip leading 'v' for the folder name
    display_version = version.lstrip('v')
    
    # Create the versioned folder: dist/RetroArch-1.21.0/
    versioned_folder = DIST_DIR / f"RetroArch-{display_version}"
    versioned_folder.mkdir(parents=True, exist_ok=True)
    
    # Define the final AppImage path
    output_name = versioned_folder / f"{app_name}-{arch}.AppImage"
    
    download_appimagetool()
    
    log(f"Generating AppImage: {output_name}...")
    env = os.environ.copy()
    env["ARCH"] = arch
    run([str(APPIMAGE_TOOL.resolve()), str(APPDIR.resolve()), str(output_name.resolve())], env=env)
    
    # Write build_info.txt next to the AppImage
    build_info = collect_build_info(config)
    with open(versioned_folder / "build_info.txt", "w") as f:
        f.write(build_info)
    
    log(f"SUCCESS: AppImage and build_info.txt created at {versioned_folder}")

def bundle_dependencies():
    log("--- Bundling Shared Library Dependencies ---")
    ra_bin = APPDIR / "usr" / "bin" / "retroarch"
    if not ra_bin.exists():
        log(f"ERROR: RetroArch binary not found at {ra_bin}")
        return

    # Standard AppImage exclusion list (libs that should come from the host OS)
    EXCLUDE_LIST = {
        "libc.so.6", "libm.so.6", "libdl.so.2", "libpthread.so.0", "librt.so.1",
        "libgcc_s.so.1", "libstdc++.so.6", "libutil.so.1", "libcrypt.so.1",
        "libX11.so.6", "libXext.so.6", "libXau.so.6", "libXdmcp.so.6",
        "libxcb.so.1", "libGL.so.1", "libEGL.so.1", "libGLESv2.so.2",
        "libvulkan.so.1", "libdrm.so.2", "libgbm.so.1", "libudev.so.1",
        "libasound.so.2", "libwayland-client.so.0", "libwayland-server.so.0",
        "libwayland-egl.so.1", "libwayland-cursor.so.0", "libglapi.so.0",
        "linux-vdso.so.1", "ld-linux-aarch64.so.1"
    }

    lib_dest = APPDIR / "usr" / "lib"
    lib_dest.mkdir(parents=True, exist_ok=True)

    def get_deps(obj_path):
        deps = {}
        try:
            output = subprocess.check_output(["ldd", str(obj_path)], text=True)
            for line in output.splitlines():
                if "=>" in line:
                    parts = line.split("=>")
                    lib_name = parts[0].strip()
                    lib_path = parts[1].split("(")[0].strip()
                    if lib_path and lib_path != "not found":
                        deps[lib_name] = lib_path
        except Exception as e:
            # log(f"Note: Could not run ldd on {obj_path}")
            pass
        return deps

    # Fully recursive dependency search
    to_check = [str(ra_bin)]
    for core in (lib_dest / "libretro").glob("*.so"):
        to_check.append(str(core))
    
    checked_paths = set()
    all_deps = {}
    
    while to_check:
        current_path = to_check.pop(0)
        if current_path in checked_paths:
            continue
        checked_paths.add(current_path)
        
        deps = get_deps(current_path)
        for name, path in deps.items():
            if name not in EXCLUDE_LIST and name not in all_deps:
                all_deps[name] = path
                if path not in checked_paths:
                    to_check.append(path)

    copied_count = 0
    for lib_name, lib_src in all_deps.items():
        target_path = lib_dest / lib_name
        if not target_path.exists():
            log(f"Bundling: {lib_name}")
            shutil.copy2(lib_src, target_path)
            copied_count += 1

    log(f"Bundled {copied_count} shared libraries.")

def main():
    log("=== RetroArch AppImage Build Started ===")
    try:
        config = load_config()
        setup_directories()
        install_dependencies()
        build_retroarch(config)
        build_filters()
        build_cores(config)
        bundle_dependencies()
        fetch_assets()
        prepare_appdir(config)
        create_appimage(config)
        log("=== Build Process Completed Successfully ===")
    except Exception as e:
        log(f"FATAL ERROR: {str(e)}")
        sys.exit(1)
    finally:
        log_stream.close()

if __name__ == "__main__":
    main()
