#include <fmt/format.h>
#include <generated/config.hpp>
#include <generated/git_config.hpp>

int main() {
  fmt::print("-- generated at: {}\n", GENERATED_TIME);
  fmt::print("-- git version: {}\n", GIT_VERSION);
}
