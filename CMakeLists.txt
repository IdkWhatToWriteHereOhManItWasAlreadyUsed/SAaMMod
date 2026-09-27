cmake_minimum_required(VERSION 3.20)
project(Lab2_Code)

set(CMAKE_CXX_STANDARD 20)

# подмодули
add_subdirectory(runner)
add_subdirectory(math)


# основной executable
add_executable(${PROJECT_NAME}
        src/main.cpp
)

target_include_directories(${PROJECT_NAME} PRIVATE
        "${CMAKE_CURRENT_SOURCE_DIR}/src"
)

target_link_libraries(${PROJECT_NAME} PRIVATE
        runner
)

# тесты
enable_testing()

add_executable(test_mock
        src/test/test_main.cpp
)

target_include_directories(test_mock PRIVATE
        "${CMAKE_CURRENT_SOURCE_DIR}/src"
)

target_link_libraries(test_mock PRIVATE
        runner
)

add_test(NAME mock_test COMMAND test_mock)