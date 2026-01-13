This is a project template! Rewrite this read-me to fit to your project.

This repository provides a template for organizing code and data in social science projects, inspired by recommendations from J. Shapiro and M. Gentzkow in their guide "[Code and Data for the Social Sciences: A Practitioner's Guide](https://web.stanford.edu/%7Egentzkow/research/CodeAndData.pdf)". They recommend these main folders:
1. input (for input files not to be touched)
2. intermed (for intermediary outputs, optional for most languages)
3. output (for all kinds of output files for the manuscript)
Although the original guide recommends a separate `code/` folder for scripts, this can complicate reading centralized configuration files—especially outside of Stata. To simplify this:
Instead, place all scripts in the root folder and use numbers to enforce ordering. The numbers should indicate the order in which steps should be executed. For scripts with intermediary output, use folders with corresponding numbers. Since Python cannot import from scripts starting with numbers, it is advisable to prepend the file names with say an underscore. Do the same for scripts of other languages to keep the ordering.

Store project metadata in your `pyproject.toml`, as this is standard according to [PEP 518](https://peps.python.org/pep-0518/) and others. However, only [standard sections](https://packaging.python.org/en/latest/specifications/pyproject-toml/) are allowed. Keep the LICENSE and the license keyword in sync. At the end of the project, add some other [classifiers](https://pypi.org/classifiers/) for automatic categorization. Also consider adding keywords to help search engines.

Store all other configuration in your `config.toml`. Storing "moving parts" here makes the project more maintainable and transparent. toml is preferred over cfg/ini (configparser style), json, yaml, or even python literals. The latter, typically stored in a .py file, which makes it a python module, bears security risks and shades packages with the same name. toml files can be read by R and other languages, too.

Create a file called `.env` to store access credentials. This is a file that can be read by Python's "python-env", R's "read.env()", etc. The `.env` must not be shared; it is ignored by `.gitignore`. Then document the `.env` file in this read-me.
