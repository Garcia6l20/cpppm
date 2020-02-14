#include <iostream>

int main(int argc, char** argv) {
    std::string who = "cpppm";
    if (argc > 1)
        who = argv[1];
    std::cout << "Hello " << who << "\n";
    return 0;
}