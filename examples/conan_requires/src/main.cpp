#define DOCTEST_CONFIG_IMPLEMENT_WITH_MAIN
#include <doctest/doctest.h>

#include <fmt/format.h>

TEST_CASE("cpppm_loves_conan") {
    CHECK(fmt::format("{1} loves {0} !!!", "conan", "cpppm") == "cpppm loves conan !!!");
}
