import setuptools

with open("README.md", "r") as fh:
    long_description = fh.read()

setuptools.setup(
    name="holidays_co_full",
    version="1.1.0",
    author="Carlos Visbal",
    author_email="carlosvisbal66@gmail.com",
    description="Librería de festivos y días hábiles para Colombia, con precisión histórica desde 1970",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/carlosvisbal/holidays_co_full",
    project_urls={
        "Código fuente": "https://github.com/carlosvisbal/holidays_co_full",
        "Reporte de errores": "https://github.com/carlosvisbal/holidays_co_full/issues",
        "Changelog": "https://github.com/carlosvisbal/holidays_co_full/releases",
    },
    keywords=[
        "colombia", "festivos", "holidays", "dias habiles", "business days",
        "ley emiliani", "nomina", "calendario laboral", "puentes", "ical",
    ],
    packages=setuptools.find_packages(),
    package_data={"holidays_co_full": ["py.typed"]},
    python_requires=">=3.7",
    install_requires=[],
    extras_require={
        "pandas": ["pandas>=1.0"],
    },
    entry_points={
        "console_scripts": [
            "holidays-co=holidays_co_full.cli:main",
        ],
    },
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
        "Topic :: Software Development :: Libraries :: Python Modules",
        "Natural Language :: Spanish",
        "Typing :: Typed",
    ],
)
