#include <iostream>
#include <fstream>
#include <filesystem>

#include <cassert>

#include <fmt/chrono.h>

int main(int argc, char **argv) {
    assert(argc > 1);
    std::time_t t = std::time(nullptr);
    std::ofstream out(argv[1]);
    out << fmt::format(R"(#pragma once
#define GENERATED_TIME "{:%Y-%m-%d}"
)", *std::localtime(&t));
    return 0;
}
