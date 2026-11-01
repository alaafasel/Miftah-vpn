cmake_minimum_required(VERSION 3.18)
project(miftah-tun C)

set(HEV "${CMAKE_CURRENT_SOURCE_DIR}/third_party/hev-socks5-tunnel")

add_library(miftah-tun SHARED miftah_tun.c)

target_include_directories(miftah-tun PRIVATE
    "${HEV}/src"
    "${HEV}/third-party/hev-socks5-tproxy/src"
    "${HEV}/third-party/yaml/src"
)

file(GLOB HEV_SOURCES
    "${HEV}/src/*.c"
    "${HEV}/third-party/hev-socks5-tproxy/src/*.c"
    "${HEV}/third-party/yaml/src/*.c"
)

target_sources(miftah-tun PRIVATE ${HEV_SOURCES})
target_link_libraries(miftah-tun log)
