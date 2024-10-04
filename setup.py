import setuptools


def long_description():
    with open("README.md") as fp:
        return fp.read()


def parse_requirements_file(path):
    with open(path) as fp:
        dependencies = (d.strip() for d in fp.read().split("\n") if d.strip())
        return [d for d in dependencies if not d.startswith("#")]


setuptools.setup(
    name="koleo-cli",
    version="0.2.137.6",
    description="Koleo CLI",
    long_description=long_description(),
    long_description_content_type="text/markdown",
    author="Zoey !",
    maintainer_email="cb98uzhd@duck.com",
    license="GNU General Public License v3.0",
    url="https://github.com/lzgirlcat/koleo-cli",
    python_requires=">=3.12",
    entry_points={"console_scripts": ["koleo = koleo.cli:main"]},
    install_requires=parse_requirements_file("requirements.txt"),
    include_package_data=True,
    keywords=["koleo", "timetable", "trains", "rail", "poland"],
    project_urls={
        "Source (GitHub)": "https://github.com/lzgirlcat/koleo-cli",
        "Issue Tracker": "https://github.com/lzgirlcat/koleo-cli/issues",
    },
    classifiers=[
        "Programming Language :: Python :: 3",
        "Operating System :: OS Independent",
    ],
)
