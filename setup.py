import setuptools

with open("README.md", "r") as fh:
    long_description = fh.read()

package = "cpppm"

setuptools.setup(
    name=package,
    version="0.0.1",
    author="Garcia Sylvain",
    author_email="garcia.6l20@gmail.com",
    description="CPP package manager",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/Garcia6l20/cpppm",
    packages=[package],
    package_dir={package: package},
    package_data={package: ['templates/*.j2']},
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires='>=3.7',
)
