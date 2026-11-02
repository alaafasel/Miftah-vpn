#!/usr/bin/env bash
# Builds the two native artifacts the MIFTAH app needs:
#   1. app/libs/libXray.aar        (Xray-core via gomobile)
#   2. app/src/main/jniLibs/<abi>/libmiftah-tun.so  (hev-socks5-tunnel JNI)
#
# Requirements: Go >= 1.22, Android SDK + NDK r26+, cmake, git, JDK 17.
# Run from miftah/android/native:  ./build-native.sh
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
APP_DIR="$(cd "${HERE}/.." && pwd)"
XRAY_VERSION="${XRAY_VERSION:-v1.8.24}"
ANDROID_API="${ANDROID_API:-26}"
ABIS="${ABIS:-arm64-v8a armeabi-v7a}"

log() { printf '\n\033[1;33m[miftah]\033[0m %s\n' "$*"; }
die() { printf '\n\033[1;31m[miftah] ERROR:\033[0m %s\n' "$*" >&2; exit 1; }

# ---------------------------------------------------------------- prerequisites
command -v go >/dev/null || die "go not found (install Go 1.22+)"
command -v git >/dev/null || die "git not found"
command -v cmake >/dev/null || die "cmake not found (sdkmanager 'cmake;3.22.1')"
[ -n "${ANDROID_HOME:-}" ] || die "ANDROID_HOME is not set"
[ -d "${ANDROID_HOME}/ndk" ] || die "Android NDK not installed under \$ANDROID_HOME/ndk"

NDK_DIR="$(ls -d "${ANDROID_HOME}"/ndk/* 2>/dev/null | sort -V | tail -1)"
[ -n "${NDK_DIR}" ] || die "no NDK directory found"
log "NDK: ${NDK_DIR}"
log "Go:  $(go version)"

# ------------------------------------------------------------- 1) Xray-core AAR
log "Building Xray-core ${XRAY_VERSION} AAR (this takes a while)"
cd "${HERE}/xraymobile"

if [ ! -f go.sum ]; then
  go mod tidy
fi

MOBILE_VERSION="v0.0.0-20261011034528-197770444867"
go get "golang.org/x/mobile@${MOBILE_VERSION}"
if ! command -v gomobile >/dev/null; then
  log "installing gomobile"
  go install "golang.org/x/mobile/cmd/gomobile@${MOBILE_VERSION}"
  go install "golang.org/x/mobile/cmd/gobind@${MOBILE_VERSION}"
  export PATH="${PATH}:$(go env GOPATH)/bin"
fi
gomobile init

TARGETS=""
for abi in ${ABIS}; do
  case "${abi}" in
    arm64-v8a)   TARGETS="${TARGETS},android/arm64" ;;
    armeabi-v7a) TARGETS="${TARGETS},android/arm" ;;
    x86_64)      TARGETS="${TARGETS},android/amd64" ;;
    *) die "unsupported ABI ${abi}" ;;
  esac
done
TARGETS="${TARGETS#,}"

mkdir -p "${APP_DIR}/app/libs"
gomobile bind \
  -target "${TARGETS}" \
  -androidapi "${ANDROID_API}" \
  -ldflags="-checklinkname=0" \
  -o "${APP_DIR}/app/libs/libXray.aar" \
  .

log "AAR written to app/libs/libXray.aar"

# --------------------------------------------------------- 2) tun2socks JNI .so
log "Building hev-socks5-tunnel JNI library"
cd "${HERE}/tun2socks"

if [ ! -d third_party/hev-socks5-tunnel ]; then
  git clone --depth 1 --recursive \
    https://github.com/heiher/hev-socks5-tunnel.git \
    third_party/hev-socks5-tunnel
fi
# Submodules are needed even when the parent repo already exists.
git -C third_party/hev-socks5-tunnel submodule update --init --recursive

for abi in ${ABIS}; do
  log "cmake ${abi}"
  BUILD="build-${abi}"
  rm -rf "${BUILD}"
  cmake -S . -B "${BUILD}" \
    -DCMAKE_TOOLCHAIN_FILE="${NDK_DIR}/build/cmake/android.toolchain.cmake" \
    -DANDROID_ABI="${abi}" \
    -DANDROID_PLATFORM="android-${ANDROID_API}" \
    -DCMAKE_BUILD_TYPE=Release
  cmake --build "${BUILD}" --parallel

  mkdir -p "${APP_DIR}/app/src/main/jniLibs/${abi}"
  cp "${BUILD}/libmiftah-tun.so" "${APP_DIR}/app/src/main/jniLibs/${abi}/"
done

log "Done."
log "  app/libs/libXray.aar"
for abi in ${ABIS}; do log "  app/src/main/jniLibs/${abi}/libmiftah-tun.so"; done
log "Next: ./gradlew assembleDebug"
