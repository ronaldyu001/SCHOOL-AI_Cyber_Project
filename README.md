# Collaboration Guidelines

---

**Contributing**: Feature branches are preferred when relevant.

**Language**: Python 3.12

**Documentation**: Documentation is guidelined in`Documentation/README.md`

---

### Repo Structure

```
____ Documentation
  |
  |____ Datasets_And_Models

____ src
  |
  |____ backend
  |
  |____ deployment
  |
  |____ frontend
```

#### Folder Content

`Documentation/`: Project, dataset, and model documentation.

`Training/`: Data preprocessing, model training, documentation. Jupyter notebooks capture all three.

`src/backend/`: Python backend source and dependencies.

`src/deployment/`: Docker Compose orchestration.

`src/frontend/`: React and TypeScript frontend.

---

### Launching the Stack

> Docker Files and Compose takes care of environment setup.

From the repository root:

```Shell
cd src/deployment

docker compose up --build -d	# -- build forces the docker services to rebuild. -d runs detached so it doesn't hog your terminal.
```

Open `http://localhost:5173`. Stop the stack with `docker compose down`.

---

### Setting Up the Frontend

> Only relevant when running the frontend without Docker.

Install Node.js 20.19+ (or 22.12+) and npm. From the repository root:

```Shell
cd src/frontend

npm ci
npm run dev
```

Open `http://localhost:5173`.

---

### Setting Up Your Environment

> Only relevant if wanting to test services without Docker orchestration.

**Linux**

```Shell
python3.12 -m venv .venv

source .venv bin activate

pip install pip-tools
```

**Windows**

```
py -3.12 -m venv .venv

.\.venv\Scripts\Activate.ps1

python -m pip install pip-tools
```

---

### Managing Your Environment

> Docker takes care of dependency installation during the build phase.
> Pip install to your environment if testing services without Docker orchestration.

We'll be using a shared list of dependencies to make sure our environments match.

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

---
