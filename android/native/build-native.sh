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

# --------------------------------------------------------- 2) tun2socks JNI
log "Building hev-socks5-tunnel JNI library"

cd "${HERE}/tun2socks"

HEV_DIR="${HERE}/tun2socks/third_party/hev-socks5-tunnel"

if [ ! -d "${HEV_DIR}/third-part/hev-task-system" ]; then
  rm -rf "${HEV_DIR}"
  git clone --depth 1 --recursive \
    https://github.com/heiher/hev-socks5-tunnel.git \
    "${HEV_DIR}"
fi

git -C "${HEV_DIR}" submodule update --init --recursive

mkdir -p "${HERE}/tun2socks/jni"

mkdir -p "${HERE}/tun2socks/jni"

cat > "${HERE}/tun2socks/jni/Android.mk" <<'EOF'
LOCAL_PATH := $(call my-dir)
HEV_PATH := $(LOCAL_PATH)/../third_party/hev-socks5-tunnel

include $(CLEAR_VARS)
LOCAL_MODULE := hev-task-system
SRCDIR := $(HEV_PATH)/third-part/hev-task-system
include $(HEV_PATH)/third-part/hev-task-system/Android.mk

include $(CLEAR_VARS)
LOCAL_MODULE := lwip
SRCDIR := $(HEV_PATH)/third-part/lwip
include $(HEV_PATH)/third-part/lwip/Android.mk

include $(CLEAR_VARS)
LOCAL_MODULE := yaml
SRCDIR := $(HEV_PATH)/third-part/yaml
include $(HEV_PATH)/third-part/yaml/Android.mk

include $(CLEAR_VARS)
LOCAL_MODULE := miftah-tun
LOCAL_SRC_FILES := ../miftah_tun.c
LOCAL_C_INCLUDES := \
    $(HEV_PATH)/src \
    $(HEV_PATH)/third-part/hev-task-system/include
LOCAL_STATIC_LIBRARIES := hev-socks5-tunnel
LOCAL_LDLIBS := -llog
include $(BUILD_SHARED_LIBRARY)

include $(CLEAR_VARS)
LOCAL_MODULE := hev-socks5-tunnel
SRCDIR := $(HEV_PATH)
include $(HEV_PATH)/Android.mk
EOF

cat > "${HERE}/tun2socks/jni/Application.mk" <<'EOF'
APP_OPTIM := release
APP_PLATFORM := android-26
APP_ABI := arm64-v8a armeabi-v7a
APP_CFLAGS := -O3
NDK_TOOLCHAIN_VERSION := clang
EOF

for abi in ${ABIS}; do
  log "ndk-build ${abi}"
  APP_ABI="${abi}" ndk-build \
    NDK_PROJECT_PATH="${HERE}/tun2socks" \
    APP_BUILD_SCRIPT="${HERE}/tun2socks/jni/Android.mk" \
    NDK_APPLICATION_MK="${HERE}/tun2socks/jni/Application.mk" \
    NDK_OUT="${HERE}/tun2socks/obj-${abi}" \
    NDK_LIBS_OUT="${APP_DIR}/app/src/main/jniLibs" \
    clean
  APP_ABI="${abi}" ndk-build \
    NDK_PROJECT_PATH="${HERE}/tun2socks" \
    APP_BUILD_SCRIPT="${HERE}/tun2socks/jni/Android.mk" \
    NDK_APPLICATION_MK="${HERE}/tun2socks/jni/Application.mk" \
    NDK_OUT="${HERE}/tun2socks/obj-${abi}" \
    NDK_LIBS_OUT="${APP_DIR}/app/src/main/jniLibs"
done

log "Done."
log "  app/libs/libXray.aar"
for abi in ${ABIS}; do log "  app/src/main/jniLibs/${abi}/libmiftah-tun.so"; done
log "Next: ./gradlew assembleDebug"
