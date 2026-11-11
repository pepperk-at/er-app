# Deploying the ER Wait Dashboard

How we put the app on GitHub and published it with Streamlit Community Cloud.

- **GitHub repo:** https://github.com/pepperk-at/er-app
- **Main file:** `Home.py`

---

## 1. Project files

The `er-app` folder must contain:

| File / folder | Purpose |
|---|---|
| `Home.py` | Entry point and main dashboard (the file Streamlit runs) |
| `pages/` | Sub-pages, shown automatically in the sidebar |
| `utils.py` | Shared helpers for data loading and calculations (not run directly) |
| `data/` | CSV/Excel data files the app reads |
| `requirements.txt` | Python libraries Streamlit Cloud installs (`streamlit`, `pandas`, `openpyxl`) |
| `.gitignore` | Keeps `.venv/`, `then/`, `__pycache__/` and `*.pyc` out of GitHub |

> If you add a new library to the code, also add it to `requirements.txt`, or the online app will crash.

## 2. Test locally first

In PowerShell, from the `er-app` folder:

```powershell
.\.venv\Scripts\python.exe -m streamlit run Home.py
```

Click through every page. If something breaks locally, it will break online too.

If PowerShell blocks scripts, run this once:

```powershell
Set-ExecutionPolicy -Scope CurrentUser RemoteSigned
```

## 3. Install GitHub Desktop and sign in

1. Download it from https://desktop.github.com and install it.
2. Sign in with your GitHub account (File → Options → Accounts).

## 4. Use your private (noreply) email

GitHub blocks pushes when your email is set to private and a commit uses your real email.

- In GitHub Desktop, go to **File → Options → Git** and set the email to your GitHub noreply address. It looks like `ID+username@users.noreply.github.com`, and you can find it at https://github.com/settings/emails.

## 5. Commit and push

1. In GitHub Desktop, add the `er-app` folder as a repository.
2. Write a commit summary, for example "Initial commit", and click **Commit to main**.
3. Click **Publish repository** the first time, or **Push origin** after that.
4. Check that it worked: open the repo on GitHub and make sure `Home.py`, `pages/`, `data/` and `requirements.txt` are there.

### Common problems

| Error | Fix |
|---|---|
| Hundreds of changed files, "Permission denied", path in `then/...` | A virtual environment is being committed. Add the folder to `.gitignore`. |
| Push rejected: "would publish a private email address" | Set the noreply email (step 4), then amend the commit. |
| LF/CRLF warnings | Harmless. Ignore them. |

## 6. Deploy on Streamlit Community Cloud

1. Go to https://share.streamlit.io and click **Continue with GitHub**. Allow access, including private repos if the repo is private.
2. Click **Create app**, then **Deploy a public app from GitHub**.
3. Fill in:
   - **Repository:** `pepperk-at/er-app`
   - **Branch:** `main`
   - **Main file path:** `Home.py`
   - **App URL:** pick a name, e.g. `er-wait-dashboard`
   - *(Optional)* **Advanced settings → Python version:** 3.11 or 3.12
4. Click **Deploy** and wait a few minutes for the first build.
5. Copy the app link (e.g. `https://er-wait-dashboard.streamlit.app`). This is the link to share.

To find the link again, go to share.streamlit.io, click **⋮** next to the app, and choose **Copy URL**.

### Second app: the AFTER version (`app_v2/`)

Both versions deploy from the same repo, so there are two links: before and after.
Repeat the steps above with:
- **Main file path:** `app_v2/Home.py`
- **App URL:** a different name, e.g. `er-wait-dashboard-after`

Streamlit uses `app_v2/requirements.txt` for this app. Pushing to `main` redeploys both apps.
Teammates who upload data for the after app use the `app_v2/data/` folder.

## 7. Sharing

- If the repo is private, open the app's **Settings → Sharing** and make it public, or invite the instructor by email.
- To let group members push code, add them on GitHub under **Settings → Collaborators**. Everyone should **Fetch/Pull** before making changes.

## 8. Updating the app

Edit the code, then **Commit** and **Push origin** in GitHub Desktop. Streamlit Cloud redeploys automatically, so there's no need to create a new app.

### Updating a data file without GitHub Desktop

Group members who only own a data file can upload it in the browser:

1. Open the repo on GitHub and go into the `data/` folder.
2. Click **Add file → Upload files** and drop in the file. It must have the same name as the one it replaces.
3. Write a short message, such as "Update forecast.csv", and click **Commit changes**.
4. Wait a minute or two, then open the app link and check your page.

If the page shows an error after the upload, check the file against the format rules in `README.md`.

## 9. How long the app stays online

- It stays online free for as long as the app and the GitHub repo exist.
- After a period with no visitors it **goes to sleep**. Anyone opening it can click **"Yes, get this app back up!"**, and it wakes in under a minute without losing anything.
- **Before a presentation or grading, open the link a few minutes early** to wake it up.
- It stops working only if you delete the app, delete or rename the repo, or remove Streamlit's access to a private repo.
