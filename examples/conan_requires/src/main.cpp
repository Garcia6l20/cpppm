#define DOCTEST_CONFIG_IMPLEMENT_WITH_MAIN
#include <doctest/doctest.h>

#include <spdlog/spdlog.h>

TEST_CASE("cpppm_loves_conan") {
    spdlog::info("Hi spdlog !");
    CHECK(fmt::format("{1} loves {0} !!!", "conan", "cpppm") == "cpppm loves conan !!!");
}
