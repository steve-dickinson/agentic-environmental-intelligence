# GitHub Pages Setup Guide

## Enable GitHub Pages

1. Go to your repository: https://github.com/steve-dickinson/agentic-environmental-intelligence

2. Click **Settings** (top navigation)

3. Scroll down to **Pages** (left sidebar)

4. Under **Build and deployment**:
   - Source: **Deploy from a branch**
   - Branch: **main**
   - Folder: **/docs**

5. Click **Save**

6. Wait 1-2 minutes for GitHub to build the site

7. Your site will be available at:
   **https://steve-dickinson.github.io/agentic-environmental-intelligence/**

## What's Included

✅ **Main Page** (index.md)
- Overview and key features
- Architecture summary
- Example incident report
- Performance metrics
- Quick start guide

✅ **Architecture Page** (architecture.md)
- Detailed system diagrams
- Data flow explanations
- Client patterns
- Performance optimizations

✅ **Theme**: GitHub Cayman theme (professional, clean)

✅ **Navigation**: Links between pages

## Next Steps (Optional)

### Add Dashboard Screenshot
1. Take a screenshot of your Streamlit dashboard
2. Save as `docs/images/dashboard.png`
3. Commit and push
4. The image will automatically show on the site

### Customize Theme
Edit `docs/_config.yml`:
```yaml
title: Your Custom Title
description: Your custom description
```

### Add More Pages
Create new `.md` files in `docs/`:
```markdown
---
layout: default
title: Your Page Title
---

# Content here
```

Then link from other pages:
```markdown
[Link text](your-page.md)
```

## Preview Locally (Optional)

```bash
# Install Jekyll
gem install bundler jekyll

# Serve locally
cd docs
bundle exec jekyll serve

# View at http://localhost:4000
```

## Troubleshooting

**Site not showing?**
- Check Settings → Pages shows "Your site is live at..."
- Wait a few minutes after enabling
- Check Actions tab for build errors

**Broken links?**
- Use relative paths: `[Link](page.md)` not `[Link](/page.md)`

**Theme not loading?**
- Ensure `_config.yml` has `remote_theme` specified
- Wait for GitHub Actions to complete

---

Your documentation site is now ready! 🎉
