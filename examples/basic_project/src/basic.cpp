#include <basic.hpp>
#include <iostream>

namespace basic {
void say_hello(const std::string& who) {
    std::cout << "Hello " << who << " !\n";
}
}
