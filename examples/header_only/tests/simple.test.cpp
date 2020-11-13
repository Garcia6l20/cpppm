#define CATCH_CONFIG_MAIN
#include <catch2/catch.hpp>
#include <header_lib/header_lib.hpp>

TEST_CASE("Simple header test", "[header_only]") {
  REQUIRE(true);
}

