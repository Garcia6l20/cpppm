#include <iostream>
#include <fstream>

#include <fmt/chrono.h>

int main() {
    std::time_t t = std::time(nullptr);
    std::ofstream out("config.hpp");
    out << fmt::format(R"(#pragma once
#define GENERATED_TIME "{:%Y-%m-%d}"
)", *std::localtime(&t));
    return 0;
}
