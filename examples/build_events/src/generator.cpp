#include <iostream>
#include <fstream>
#include <filesystem>

#include <cassert>

#include <fmt/chrono.h>

namespace fs = std::filesystem;

int main(int argc, char **argv) {
    assert(argc > 1);
    std::time_t t = std::time(nullptr);
    fs::path p = argv[1];
    fs::create_directories(p.parent_path());
    std::ofstream out(p.c_str());
    out << fmt::format(R"(#pragma once
#define GENERATED_TIME "{:%Y-%m-%d}"
)", *std::localtime(&t));
    return 0;
}
