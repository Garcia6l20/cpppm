#define CATCH_CONFIG_MAIN
#include <catch2/catch.hpp>
#include <header_lib/header_lib.hpp>

TEST_CASE("A simple header test", "[header_only]") {
  REQUIRE(header_only::always_true);
}
