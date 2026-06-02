import { execSync } from "node:child_process";

const repoUrl = "https://github.com/jianzhnie/ai-news-daily.git";
const distDir = "dist";

console.log("Deploying dist/ to GitHub Pages...");

execSync(
  `rm -rf ${distDir}/.git && cd ${distDir} && git init && git checkout -b gh-pages && git add -A && git commit -m "deploy" && git push -f ${repoUrl} gh-pages`,
  { stdio: "inherit" }
);

console.log("Deployed!");
