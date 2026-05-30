from setuptools import setup, find_packages

setup(
    name="basketball-analyzer",
    version="0.1.0",
    description="Identify basketball player weaknesses through stat analysis against position benchmarks",
    author="",
    packages=find_packages(),
    python_requires=">=3.10",
    entry_points={
        "console_scripts": [
            "basketball-analyzer=src.cli:main",
        ],
    },
)
