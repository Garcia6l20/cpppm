import setuptools

with open("README.md", "r") as fh:
    long_description = fh.read()

package = "cpppm"

setuptools.setup(
    name=package,
    version="0.2.3",
    license='MIT',
    author="Garcia Sylvain",
    author_email="garcia.6l20@gmail.com",
    description="CPP Package Manager",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/Garcia6l20/cpppm",
    keywords=["c++", "project-manager", "cmake", "conan"],
    packages=setuptools.find_packages(),
    package_dir={package: package},
    package_data={package: ['templates/*.j2']},
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "Topic :: Software Development :: Build Tools",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3.8",
    ],
    python_requires='>=3.8',
    install_requires=[
        'Click>=7.1.2',
        'conan>=1.31.2'
    ],
)
