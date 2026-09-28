cmake_minimum_required(VERSION 3.20)
project(logging)

set(CMAKE_CXX_STANDARD 20)

find_package(PkgConfig REQUIRED)
pkg_check_modules(JSONCPP REQUIRED jsoncpp)

add_library(${PROJECT_NAME}
        # .cpp
        logger.cpp
        stats_logger.cpp
        # headers (для IDE)
        record.cpp
        record.h
        logger.h
        stats_logger.h
)

# logger.h публично тянет <json/json.h>, поэтому include-директории jsoncpp
# и сама библиотека доступны всем, кто подключает logging
target_include_directories(${PROJECT_NAME} PUBLIC
        "${CMAKE_CURRENT_SOURCE_DIR}"
        ${JSONCPP_INCLUDE_DIRS}
)

target_link_libraries(${PROJECT_NAME} PUBLIC
        ${JSONCPP_LIBRARIES}
)
