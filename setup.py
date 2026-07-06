import setuptools

with open("README.md", "r") as fh:
    long_description = fh.read()

setuptools.setup(
    name="holidays_co_full",
    version="1.0.0",
    author="Carlos Visbal",
    author_email="carlosvisbal66@gmail.com",
    description="Librería de festivos y días hábiles para Colombia, con precisión histórica desde 1970",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/carlosvisbal/holidays_co_full",
    keywords=[
        "colombia", "festivos", "holidays", "dias habiles", "business days",
        "ley emiliani", "nomina", "calendario laboral",
    ],
    packages=setuptools.find_packages(),
    python_requires=">=3.7",
    install_requires=[],
    license="MIT",
    classifiers=[
        "Development Status :: 5 - Production/Stable",
        "Intended Audience :: Developers",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Programming Language :: Python :: 3.13",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Topic :: Office/Business :: Scheduling",
        "Natural Language :: Spanish",
    ],
)