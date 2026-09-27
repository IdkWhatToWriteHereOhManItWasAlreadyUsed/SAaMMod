cmake_minimum_required(VERSION 3.20)
project(Lab2_Code)

set(CMAKE_CXX_STANDARD 20)

# подмодули
add_subdirectory(runner)
add_subdirectory(math)
add_subdirectory(logging)

find_package(PkgConfig REQUIRED)
pkg_check_modules(JSONCPP REQUIRED jsoncpp)

# основной executable
add_executable(${PROJECT_NAME}
        src/main.cpp
        src/road_1_lane_model/road_1_lane_model.cpp
        src/road_1_lane_model/agents/car.cpp
        src/road_1_lane_model/agents/car.h
        src/road_1_lane_model/agents/car_generator.cpp
        src/road_1_lane_model/agents/car_generator.h
        src/road_1_lane_model/agents/traffic_light.cpp
        src/road_1_lane_model/agents/traffic_light.h
        src/road_1_lane_model/resources/road_segment.cpp
        src/road_1_lane_model/resources/road_segment.h
        src/simple_runner/simple_runner.cpp
        src/simple_runner/simple_runner.h
)

target_include_directories(${PROJECT_NAME} PRIVATE
        "${CMAKE_CURRENT_SOURCE_DIR}/src"
         ${JSONCPP_INCLUDE_DIRS}
)

target_link_libraries(${PROJECT_NAME} PRIVATE
        runner
        math
        logging
        ${JSONCPP_LIBRARIES}
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