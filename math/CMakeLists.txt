cmake_minimum_required(VERSION 4.2)
project(math)

set(CMAKE_CXX_STANDARD 20)

add_library(${PROJECT_NAME}
    rng.cpp distributions.cpp
)

target_include_directories(${PROJECT_NAME} PRIVATE
        "${CMAKE_CURRENT_SOURCE_DIR}/"
)

