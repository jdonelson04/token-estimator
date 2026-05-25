# 🚀 GitHub Setup Instructions

Your local git repository is ready! Follow these steps to push it to GitHub.

## Step 1: Create a New Repository on GitHub

1. Go to [github.com/new](https://github.com/new)
2. **Repository name:** `token-estimator` (or your preferred name)
3. **Description:** "A decision-driven Claude skill to estimate token usage before execution"
4. **Visibility:** Public (recommended for sharing) or Private
5. **DO NOT initialize with README** (you already have one)
6. Click **"Create repository"**

GitHub will show you commands like:
```
git remote add origin https://github.com/YOUR_USERNAME/token-estimator.git
git branch -M main
git push -u origin main
```

## Step 2: Push Your Local Repository

Copy the commands from GitHub and run them in your terminal:

```bash
# Navigate to the repo directory
cd /mnt/user-data/outputs/token-estimator-repo

# Add GitHub as remote (replace YOUR_USERNAME)
git remote add origin https://github.com/YOUR_USERNAME/token-estimator.git

# Rename branch to main (GitHub default)
git branch -M main

# Push to GitHub
git push -u origin main
```

**If you prefer SSH** (more secure):
```bash
git remote add origin git@github.com:YOUR_USERNAME/token-estimator.git
git branch -M main
git push -u origin main
```

## Step 3: Verify

Go to your repo URL: `https://github.com/YOUR_USERNAME/token-estimator`

You should see:
- ✓ All files (README.md, LICENSE, .gitignore, skill/SKILL.md, skill/manifest.json)
- ✓ Commit message: "Initial commit: Token Estimation Planning Skill v1.0"
- ✓ License badge showing Apache 2.0

## What's Included

Your repo is set up with:
- **SKILL.md** — The optimized skill (copy this to Claude to use)
- **README.md** — Full documentation with examples and usage
- **LICENSE** — Apache 2.0 (open source)
- **.gitignore** — Standard ignores for Python, Node, IDE, OS files
- **manifest.json** — Metadata for distribution

## Next Steps

### To use the skill:
1. Go to your GitHub repo
2. Copy the raw URL of `skill/SKILL.md`
3. Or download it and upload to Claude Settings > Customize > Skills

### To share:
- **GitHub link:** Share your repo URL directly
- **Clone:** Users can `git clone` your repo
- **Skill file:** Share just `skill/SKILL.md` file

### To improve:
- Add your own improvements as commits
- Create branches for experiments (`git checkout -b feature-name`)
- Update version in SKILL.md frontmatter as you iterate

## Troubleshooting

**"remote origin already exists"**
```bash
git remote remove origin
# Then run the git remote add command again
```

**Authentication failed**
- Check your GitHub credentials are saved
- Use `gh auth login` (GitHub CLI) to authenticate
- Or generate a personal access token: https://github.com/settings/tokens

**"Permission denied (publickey)"**
- You're using SSH but haven't set up SSH keys
- Use HTTPS instead, or set up SSH: https://docs.github.com/en/authentication/connecting-to-github-with-ssh

## Questions?

- GitHub Docs: https://docs.github.com/en/repositories/creating-and-managing-repositories
- Git Basics: https://git-scm.com/book/en/v2

---

Once pushed, your token-estimator repo is live and shareable! 🎉
