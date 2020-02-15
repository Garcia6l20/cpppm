#include <iostream>
#include <gtest/gtest.h>
#include <fmt/format.h>

TEST(cpppm_loves_conan, easy_pz) {
    ASSERT_EQ(fmt::format("{1} loves {0} !!!", "conan", "cpppm"), "cpppm loves conan !!!");
}
