import setuptools

with open("README.md", "r") as fh:
    long_description = fh.read()

setuptools.setup(
    name="pri3o_dmenu_desktop", # Replace with your own username
    version="0.1.2",
    author="Johannes Battenberg",
    author_email="joe@chaoticneutral.eu",
    description="Drop-in replacement for i3-dmenu-desktop with simple app priorization ",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/joe-batt/pri3o-dmenu-desktop",
    packages=setuptools.find_packages(),
    entry_points={
        "console_scripts": [
            "pri3o-dmenu-desktop=pri3o_dmenu_desktop:main",
        ]
    },
    classifiers=[
        "License :: OSI Approved :: BSD License",
        "Operating System :: POSIX :: Linux",
        "Programming Language :: Python",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.5",
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3 :: Only",
    ],
    python_requires='>=3.5',
)
