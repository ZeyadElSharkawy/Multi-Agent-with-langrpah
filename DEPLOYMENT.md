# 🚀 Deployment Guide for Streamlit Cloud

## Prerequisites

1. GitHub account with this repository
2. Streamlit Cloud account ([Sign up here](https://share.streamlit.io/))
3. Google Gemini API key ([Get one here](https://makersuite.google.com/app/apikey))

## Steps to Deploy

### 1. Push to GitHub

```bash
# Initialize git (if not already done)
git init

# Add all files
git add .

# Commit
git commit -m "Initial commit: Multi-Agent Research System"

# Add remote (replace with your repo URL)
git remote add origin https://github.com/ZeyadElSharkawy/Multi-Agent-with-langrpah.git

# Push to GitHub
git push -u origin main
```

### 2. Deploy on Streamlit Cloud

1. **Go to** [share.streamlit.io](https://share.streamlit.io/)

2. **Click** "New app"

3. **Configure your app:**
   - Repository: `ZeyadElSharkawy/Multi-Agent-with-langrpah`
   - Branch: `main`
   - Main file path: `app.py`

4. **Advanced settings** → Click "Advanced settings"

5. **Add Secrets:**
   In the "Secrets" section, add:
   ```toml
   GOOGLE_API_KEY = "your_actual_gemini_api_key_here"
   ```

6. **Python version:** Select `3.10` or higher

7. **Click** "Deploy!"

### 3. Wait for Deployment

- Initial deployment takes 5-10 minutes
- Streamlit will install all dependencies from `requirements.txt`
- You'll see build logs in real-time

### 4. Your App is Live! 🎉

Once deployed, you'll get a URL like:
```
https://your-app-name.streamlit.app
```

## Important Notes

### Vector Store Setup

⚠️ **Important:** The vector store files are too large for GitHub. You have two options:

#### Option 1: Pre-process documents locally
1. Run the document processing locally
2. Upload vector store to cloud storage (AWS S3, Google Cloud Storage, etc.)
3. Update code to download from cloud storage on startup

#### Option 2: Process on first run
1. Include documents in a separate cloud storage
2. Add initialization code to process documents on first run
3. Store vector embeddings in Streamlit's persistent storage

### Environment Variables

Required environment variable:
- `GOOGLE_API_KEY`: Your Google Gemini API key

To access in code:
```python
import os
api_key = os.getenv("GOOGLE_API_KEY")
```

### File Storage

Streamlit Cloud has limited storage. Consider:
- Using cloud storage for large files (S3, GCS)
- Keeping only essential files in the repo
- Using caching for expensive operations

### Secrets Management

**Never commit:**
- `.env` files
- API keys
- Credentials

**Always use:**
- Streamlit Secrets (in deployment settings)
- Environment variables
- `.gitignore` to exclude sensitive files

## Troubleshooting

### App won't start?

1. Check requirements.txt for any missing dependencies
2. Verify Python version is 3.10+
3. Check build logs for errors

### Out of memory?

1. Reduce model sizes
2. Use lighter embeddings
3. Implement lazy loading

### API errors?

1. Verify API key is set in Streamlit Secrets
2. Check API key has proper permissions
3. Monitor API usage/quotas

## Updating Your App

```bash
# Make changes to your code
git add .
git commit -m "Your update message"
git push origin main
```

Streamlit Cloud will automatically redeploy when you push to GitHub!

## Custom Domain (Optional)

1. Go to your app settings on Streamlit Cloud
2. Click "Settings" → "General"
3. Add your custom domain
4. Follow DNS configuration instructions

## Monitoring

- View app logs in Streamlit Cloud dashboard
- Monitor resource usage
- Check deployment history

## Support

- [Streamlit Documentation](https://docs.streamlit.io/)
- [Streamlit Community Forum](https://discuss.streamlit.io/)
- [GitHub Issues](https://github.com/ZeyadElSharkawy/Multi-Agent-with-langrpah/issues)

---

**Need help?** Open an issue on GitHub or reach out to the community!

