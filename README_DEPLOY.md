# 🚀 NPGC Assistant Deployment Guide

Your chatbot is now automated for cloud deployment! We have set up a GitHub Action to sync your code with Hugging Face Spaces.

## Step 1: Create Hugging Face Space
1. Go to [Hugging Face Spaces](https://huggingface.co/spaces).
2. Click **Create new Space**.
3. Name: `npgc-assistant`.
4. SDK: Select **Docker**.
5. License: Open (e.g., Apache 2.0).

## Step 2: Set Hugging Face Secrets
In your Space, go to **Settings > Variables and secrets** and add these **Secrets**:

| Secret Name | Value |
| :--- | :--- |
| `MYSQL_HOST` | `mysql-2c4b3d45-clg-chatbot-ps7.d.aivencloud.com` |
| `MYSQL_PORT` | `15297` |
| `MYSQL_USER` | `avnadmin` |
| `MYSQL_PASSWORD` | (Your Aiven Password) |
| `MYSQL_DB` | `defaultdb` |
| `GEMINI_API_KEY` | (Your API Key) |
| `GROQ_API_KEY` | (Your API Key) |

## Step 3: Setup GitHub Automation
Since you don't have a repo yet, follow these steps:
1. **Create a new GitHub Repository**: Name it `npgc-assistant`.
2. **Add GitHub Secret**:
   - Go to [Hugging Face Settings > Tokens](https://huggingface.co/settings/tokens) and create a **New API Token** with **Write** permissions.
   - In your GitHub repo, go to **Settings > Secrets and variables > Actions**.
   - Add a new secret named `HF_TOKEN` and paste your token.
3. **Push your code**:
   ```bash
   git add .
   git commit -m "Initial commit for HF automation"
   git branch -M main
   git remote add origin https://github.com/YOUR_USERNAME/npgc-assistant.git
   git push -u origin main
   ```

## Step 4: Verification
- Once you push to GitHub, go to the **Actions** tab in your GitHub repo to see the sync in progress.
- Your Hugging Face Space will automatically pick up the changes and start building!

---
**Note**: The bot will connect directly to your Aiven Cloud Database. Make sure the database is running!
