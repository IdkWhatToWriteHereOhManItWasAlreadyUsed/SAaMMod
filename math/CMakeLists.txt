cmake_minimum_required(VERSION 4.2)
project(math)

set(CMAKE_CXX_STANDARD 20)

add_library(math
        rng.cpp
        rng.h
)

target_include_directories(math PUBLIC
        "${CMAKE_CURRENT_SOURCE_DIR}"
)
