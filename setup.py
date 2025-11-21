from setuptools import setup, find_packages

setup(
    name="marketpilot",
    version="0.1.0",
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    install_requires=open("requirements.txt").read().splitlines(),
    entry_points={
        "console_scripts": [
            "marketpilot-cli=cli.main:main",  # CLI entry point
        ],
    },
    python_requires=">=3.12",
)
