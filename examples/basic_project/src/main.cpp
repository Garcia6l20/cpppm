#include <basic.hpp>

int main(int argc, char** argv) {
    std::string who = "cpppm";
    if (argc > 1)
        who = argv[1];
    basic::say_hello(who);
    return 0;
}