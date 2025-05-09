from setuptools import find_packages, setup

setup(
    name="gateway",
    version="2.0.0",
    description="Gateway Community Management Platform",
    author="danoctua",
    packages=find_packages(),
    classifiers=[
        "Programming Language :: Python :: 3",
    ],
    entry_points={
        "console_scripts": [
            "load-sticker-collections = indexer.cli.load_sticker_collections:main"
        ]
    },
)
