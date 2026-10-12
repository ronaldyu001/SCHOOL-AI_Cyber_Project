# Collaboration Guidelines

### Language

Python 3.12

### Setting Up Your Environment

**Linux**

```Shell
python3.12 -m venv .venv

source .venv bin activate

pip install pip-tools
```

**Windows**

```
```

### Managing Your Environment

Once the environment is created, we'll be using a shared list of dependencies to make sure our environments match.

`requirements.in`: **Manually** edited list of libraries.

`requirements.txt`: **Compiled** list of libraries for dependency installation.

**Steps:**

1. Manually add the relevant library/libraries and versioning (if needed) to the requirements.in
2. Compile the requirements.txt with: `pip-compile requirements.in`
3. Update your environment's dependencies with: `pip install -r requirements.txt`

##### Why not do a `pip install` and `pip freeze` loop with just a requirements.txt?

- Doing a pip-compile **automatically resolves version compatability** between a library and its dependencies.
- requirements.txt contains all package dependencies as well as pinned versioning (**messy** to read and edit).
- requirements.in should just be the top level packages and high level versioning information, making it **easy to manage** the libraries that matter, and make any version changes easily.

### Repo Structure



### Documentation

Documentation is guidelined in: `Documentation/README.md`
