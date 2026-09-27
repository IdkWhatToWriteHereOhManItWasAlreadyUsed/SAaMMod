cmake_minimum_required(VERSION 3.20)
project(road_visualizer)

set(CMAKE_CXX_STANDARD 20)

find_package(PkgConfig REQUIRED)
pkg_check_modules(SDL3 REQUIRED sdl3)
pkg_check_modules(JSONCPP REQUIRED jsoncpp)

add_executable(${PROJECT_NAME}
        src/main.cpp
        src/trace.cpp
        src/scene.cpp
        src/render.cpp
        src/font.cpp
        # headers (для IDE)
        src/trace.h
        src/scene.h
        src/render.h
        src/font.h
)

target_include_directories(${PROJECT_NAME} PRIVATE
        "${CMAKE_CURRENT_SOURCE_DIR}/src"
        ${SDL3_INCLUDE_DIRS}
        ${JSONCPP_INCLUDE_DIRS}
)

target_link_libraries(${PROJECT_NAME} PRIVATE
        ${SDL3_LIBRARIES}
        ${JSONCPP_LIBRARIES}
)
