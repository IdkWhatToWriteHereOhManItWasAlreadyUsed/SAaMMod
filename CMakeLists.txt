cmake_minimum_required(VERSION 4.2)
project(Lab2_Code)

set(CMAKE_CXX_STANDARD 20)


file(GLOB_RECURSE SOURCE_FILES
        "src/*.cpp"
)

add_executable(${PROJECT_NAME}
        ${SOURCE_FILES}
)

target_include_directories(${PROJECT_NAME} PRIVATE
        "${CMAKE_CURRENT_SOURCE_DIR}/src"
)

