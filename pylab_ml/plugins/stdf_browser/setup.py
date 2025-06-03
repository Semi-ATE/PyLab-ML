from setuptools import find_packages, setup
from pathlib import Path
from stdf_browser import __version__

version = __version__
requirements_path = Path(Path(__file__).parents[0], "requirements/run.txt")

with requirements_path.open("r") as f:
    install_requires = list(f)
readme_path = Path(Path(__file__).parent, "./stdf_browser/README.md")
with readme_path.open("r") as f:
    long_description = f.read()
setup(
    name="stdf-browser",
    version=version,
    requires=["spyder"],
    description="Spyder STDF plugin for display and explore STDF data",
    long_description=long_description,
    long_description_content_type="text/markdown",
    author="The Semi-ATE Project Contributors",
    author_email="ate.organization@gmail.com",
    license="GPL-2.0-only",
    packages=find_packages(),
    install_requires=install_requires,
    include_package_data=True,
    entry_points={"spyder.plugins": ["Stdf = stdf_browser.plugin:StdfBrowser"]}
)
