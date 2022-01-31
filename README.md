[![pipeline status](https://forge.dgfip.finances.rie.gouv.fr/raphaelventura/sf_datalake/badges/main/pipeline.svg)](https://forge.dgfip.finances.rie.gouv.fr/raphaelventura/sf_datalake/-/commits/main)

This is the python codebase for the "Signaux Faibles" project's failure prediction algorithms on the DGFiP-hosted datalake.

# Installation

## Cloning the repository

``` shell
git clone https://forge.dgfip.finances.rie.gouv.fr/raphaelventura/sf_datalake.git

```

## Prepare a virtual environment

The virtual environment allows one to install specific version of python packages independantly without messing with the system installation.

Create a virtual environment

``` shell
virtualenv -p `which python3` <virtualenv_dir>
```

Source the new virtual environment to begin working inside this environment

``` shell
source <virtualenv_dir>/bin/activate
```

Make sure the pip version packaged with the env is up to date (it should be >= 19)

``` shell
pip install -U pip
```

Install the sf-datalake package inside the environment

``` shell
pip install .
```

from the repository root.

## Activate git hooks

Activate git hooks using

``` shell
pre-commit install
```

This will install git hooks that should enforce a set of properties before committing / pushing code. These properties can be customized through the `pre-commit` config file and can cover a wide scope : coding style, code linting, tests, etc.

# Repository structure

- `.ci/` - Contains configuration associated with the maacdo API in order to execute jobs on the datalake using a CI pipeline.
- `datasets_handling/` - Production of datasets from raw data. Datasets loading and handling, exploration and feature engineering utilities.
- `docs/` - Sphinx auto-documentation sources (see `datascience_workflow.md`) and textual / tabular documentation of the data used for training and prediction.
- `notebooks/` - Jupyter notebooks that leverage the package code. These may typically be used for tutorials / presentations.
- `src/` Contains all the package code:
    - `config/` - Configuration and model parameters that will be used during execution.
    - `processing/` - Data processing and models execution.
    - `__init__.py` - Some data-related variables definitions.
    - `__main__.py` - Main entry point script, which can be used to launch end-to-end predictions.
    - `evaluation.py` - Scores computations.
    - `exploration.py `- Data exploration-dedicated functions.
    - `io.py` - I/O functions.
    - `model.py` - Model utilities and classes.
    - `sampler.py` - Data sampling functions.
    - `transform.py` - Utilities and classes for handling and transforming datasets.
    - `utils.py` - Utility functions for spark session and data handling.
- `test/` - Tests (unitary, integration) associated with the code. They may be executed anytime using `pytest`.
- `datalake DGFiP.md` - Info about handing jobs over to the datalake and use of the jupyter lab.
- `datascience_workflow.md`- describes the workflow for data scientists working on the project.
- `.gitlab-ci.yml` - The gitlab CI/CD tools configuration file.
- `LICENSE` - The legal license associated with this repository.
- `MANIFEST.in` - Declaration of data resources used by the package.
- `.pre-commit-config.yaml` - Configuration file for the `pre-commit` package, responsible for pre-commit and pre-push git hooks.
- `.pylintrc` - Configuration file for the python linter.
- `pyproject.toml` and `setup.cfg` are configuration files for this package's setup.
- `README.md` - This file.

# Documentation

Documentation can be generated by executing

``` shell
make html
```

from the `docs/` folder. This will produce a directory containing an html-formatted documentation "readthedocs-style". This doc can be browsed by opening `docs/build_/html/index.html`.

Other formats are available for export (e.g., pdf, man, texinfo); for more info, execute

``` shell
make help
```

from the `docs/` folder as well.

Documentation is generated based on the `.rst` files contained inside `docs/source`. If needed, these files can be automatically generated using `sphinx`: from the `docs/` repository, execute

``` shell
sphinx-apidoc -fP -o source/ ../sf_datalake
```
# Continuous integration (CI), pipelines

Gitlab embedded CI/CD tools are used in order to test and automate various operations, especially cumbersome operations related to the `maacdo` APIs. Jobs are defined and associated with 4 main stages:
- `.pre`
- `test`
- `deploy`
- `.pre`

Each job may depend on one or more earlier jobs, some may be run only on failure / manually… For more info, see the gitlab CI/CD [documentation](https://docs.gitlab.com/ee/ci/).

## Configuration

CI pipelines use the following configuration files:
- `.gitlab-ci.yml`: the main configuration file. It describes jobs, stages, dependencies, caches, etc.
- `.ci/datalake/maacdo_version.json` configures which `maacdo` version to use.
- `.ci/datalake/spark_config.json` specifies Spark configuration (computation specifications) to be passed to [`spark-submit`](https://spark.apache.org/docs/2.3.2/submitting-applications.html) and command line parameters to be passed to the executed `python` script.
- `.ci/datalake/datalake_config_template.par` is the configuration file passed to all `maacdo` calls.

## Gitlab runners

Runners are installed on a virtual machine dedicated to the "signaux faibles" project.

Pipelines leverage 2 different types gitlab runners:
- A `docker` runner, which is assigned to python-related tasks: we use a specific python image in order to install packages through `pip` and be able to export archives that will be compatible with the  lake python installation.
- The `shell` runner mainly takes care of calls to the `maacdo` APIs.

This gitlab instance does not allow the use of registry, so it's not possible to use the `artifacts` instruction. We need a folder that will allow both runners to share data. The docker gitlab runner has a mounted volume at `HOST:$HOME/.ci-python_packages/ = CONTAINER:/packages`. This is configured through the runners [configuration file](https://docs.gitlab.com/runner/configuration/advanced-configuration.html).

For example, when a docker job pushes a file to `/packages`, this file is available in `~/.ci-python_packages/` for subsequent shell jobs. These folders are cleaned on a regular basis (only the last 10 are kept.)

A folder associated with every pipeline is created at `$HOME/.ci-python_packages/#pipelineId`. Inside this folder:
- The `maacdo` repository is checked out and configured.
- Results (in case of success) / yarn logs (in case of failure) are downloaded and stored.

### Docker images

Docker images are stored on the vm, but will not be deleted automatically. This can saturate the available disk space. Images can be listed using:

```sh
docker image ls
```

Then, a given image can be deleted using:

``` shell
docker image rm <tag>
```

To remove all images, including not dangling ones, use:
```sh
docker image prune -a
```

### Clearing the cache

Runners caches are used inside python-related jobs. As soon as a branch is created, a cache is associated with it. It is used to keep downloaded sources for pip and packages installed inside the created virtual environments.

Caches may have to be cleared manually, see [this](https://docs.gitlab.com/ee/ci/caching/index.html#clearing-the-cache) page.

## Variables

Some extra variables are defined in this CI/CD to configure proxy and access to the [maac-do](https://forge.dgfip.finances.rie.gouv.fr/raphaelventura/maac-do/) utility and scripts repository. See the `Variables` section in the [CI/CD settings](https://forge.dgfip.finances.rie.gouv.fr/raphaelventura/sf_datalake/-/settings/ci_cd) page. In order to access the `maac-do` code, an `Active Deploy Token` has been created in the `maac-do` repository with scope `read_repository`.

Learn more about [variables](https://forge.dgfip.finances.rie.gouv.fr/help/ci/variables/index) in Gitlab.
