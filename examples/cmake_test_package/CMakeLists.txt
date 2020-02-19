cmake_minimum_required(VERSION 3.14)

project(cpppm-examples-cmake-test-package)

include(${CMAKE_CURRENT_BINARY_DIR}/conanbuildinfo.cmake)
conan_basic_setup(TARGETS)
conan_include_build_modules()

add_executable(${PROJECT_NAME}
    main.cpp
)
target_link_libraries(${PROJECT_NAME} CONAN_PKG::cpppm-examples)
