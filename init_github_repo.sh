#!/bin/bash

set -e

FOLDER_NAME=$(basename "$(pwd)")

echo "Initializing Git repository for folder: $FOLDER_NAME"

git init

echo "Creating GitHub repository: $FOLDER_NAME"
gh repo create "$FOLDER_NAME" --public --source=. --remote=origin --push

echo "Adding all files to Git"
echo "# Init" >> README.md
git add .

echo "Making initial commit"
git commit -m "Initial"
git branch -M main
git remote add origin git@github.com:badiattila/"$FOLDER_NAME".git

echo "Pushing to GitHub"
git push -u origin main

echo "Repository setup complete!"
echo "GitHub repository URL: https://github.com/$(gh api user --jq .login)/$FOLDER_NAME"
