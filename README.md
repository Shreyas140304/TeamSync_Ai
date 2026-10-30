# TeamSync AI

TeamSync AI turns meeting notes into summaries, decisions, and assigned action
items. It also provides task management, meeting-history search, and personalized
handover briefs.

## Features

- Analyze meeting notes with Gemini and review results before saving.
- Store meetings and action items in SQLite.
- Update task owners, statuses, and outcomes.
- Search meeting history with Sentence Transformers and FAISS.
- Generate teammate handover briefs using open tasks and relevant meeting context.

## Technology

- Python and Streamlit
- SQLite
- Google Gemini (`gemini-2.5-flash`)
- Pydantic
- Sentence Transformers and FAISS

## Run locally

1. Install Python 3.11 or newer.
2. Clone the repository and open its directory:

   ```powershell
   git clone https://github.com/Shreyas140304/TeamSync_Ai.git
   cd TeamSync_Ai
   ```

3. Create and activate a virtual environment:

   ```powershell
   python -m venv .venv
   .\.venv\Scripts\Activate.ps1
   ```

4. Install dependencies:

   ```powershell
   python -m pip install -r requirements.txt
   ```

5. Create `.streamlit/secrets.toml` with your own Gemini API key:

   ```toml
   GEMINI_API_KEY = "your-gemini-api-key"
   ```

   Keep this file private. It is excluded from Git by `.gitignore`.

6. Start the app:

   ```powershell
   streamlit run app.py
   ```

Streamlit prints a local URL (usually `http://localhost:8501`). The first start
may take longer because the sentence-embedding model is downloaded.

## Deploy on Streamlit Community Cloud

### 1. Push the project to GitHub

From the project directory, confirm `.streamlit/secrets.toml`, `data/*.db`,
`logs/*.log`, and virtual environments are not staged. The repository's
`.gitignore` excludes these local files.

```powershell
git status
git add .
git commit -m "Prepare TeamSync AI for deployment"
git push -u origin master
```

If Git reports that there is nothing to commit, push the current branch:

```powershell
git push -u origin master
```

Do not commit or push API keys. If a key has ever been committed, revoke it and
create a replacement before deploying.

### 2. Create the Streamlit app

1. Sign in at [share.streamlit.io](https://share.streamlit.io/) using the
   GitHub account that can access the repository.
2. Choose **Create app**.
3. Select repository `Shreyas140304/TeamSync_Ai`, branch `master`, and main file
   path `app.py`.
4. In **Advanced settings**, choose Python 3.11 if a Python version is
   requested.
5. Open the app's **Settings → Secrets** and add:

   ```toml
   GEMINI_API_KEY = "your-gemini-api-key"
   ```

   Use your real key in the Streamlit dashboard only; do not put it in this
   README, application source, or a committed file.
6. Deploy. The initial build can take several minutes while Python packages
   and the embedding model are installed/downloaded.

### 3. Verify deployment

- Wait for Streamlit Community Cloud to report that the app is running.
- Open the app URL and analyze a short test meeting.
- Confirm that Gemini returns an analysis and that the meeting can be saved.
- Try Task Management and Smart Handover after creating a task.

If deployment fails, check **Manage app → Logs**. Dependency installation or
memory limits may be an issue because `sentence-transformers` and `faiss-cpu`
are comparatively large packages.

## Data and deployment notes

The app creates `data/teamsync.db` locally. Streamlit Community Cloud's app
filesystem should not be treated as durable storage: local SQLite data may be
lost when the app is rebuilt or its environment is reset. The deployed app
starts with its own database; local meetings are not automatically uploaded.
Use a managed persistent database before relying on this app for important or
production data.

The app loads the Sentence Transformers model from Hugging Face when the
application starts. The first startup can therefore be slower and requires
network access.

## Project files

| File | Purpose |
| --- | --- |
| `app.py` | Streamlit dashboard and user interface |
| `database.py` | SQLite schema, queries, and task updates |
| `ai_service.py` | Gemini meeting analysis |
| `rag.py` | Meeting-history retrieval and question answering |
| `handover.py` | Personalized handover brief generation |
| `logging_config.py` | Rotating application logs |
| `requirements.txt` | Python package dependencies |

## Focused owner-assignment tests

Run the owner extraction contract and database reassignment tests with:

```powershell
python -m unittest -v test_owner_assignment
```

These tests mock Gemini and do not require a live API key. Live AI behavior must
be verified separately using the Streamlit app and a valid `GEMINI_API_KEY`.
