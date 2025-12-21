# GitHub Repository Setup Instructions

Your local git repository is initialized and ready. To connect it to GitHub:

## Option 1: Create Repository via GitHub Web Interface

1. Go to https://github.com/Duds (or your organization/user)
2. Click "New repository"
3. Repository name: `hydro_automation`
4. Description: `Tapo P100 hydroponic flood and drain automation controller`
5. Set to **Private** (recommended, as it contains device credentials)
6. **DO NOT** initialize with README, .gitignore, or license (we already have these)
7. Click "Create repository"

Then run these commands:

```bash
git remote add origin https://github.com/Duds/hydro_automation.git
git push -u origin main
```

## Option 2: Create Repository via GitHub CLI

If you have GitHub CLI installed:

```bash
gh repo create Duds/hydro_automation \
  --private \
  --description "Tapo P100 hydroponic flood and drain automation controller" \
  --source=. \
  --remote=origin \
  --push
```

## Option 3: Create Repository via API/Manual Setup

If you prefer to set up the remote manually after creating the repo:

```bash
# Add remote (replace with your actual repo URL)
git remote add origin https://github.com/Duds/hydro_automation.git

# Push to GitHub
git push -u origin main
```

## Verification

After pushing, verify the remote is set correctly:

```bash
git remote -v
```

You should see:
```
origin  https://github.com/Duds/hydro_automation.git (fetch)
origin  https://github.com/Duds/hydro_automation.git (push)
```

## Important Notes

- The `.gitignore` file already excludes sensitive files:
  - `config/config.json` (contains your device credentials)
  - `logs/*.log` (log files)
  - `venv/` (virtual environment)

- Make sure `config/config.json` is never committed (it's already in .gitignore)
- Only `config/config.json.example` should be in the repository

