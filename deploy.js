import { execSync } from "node:child_process";

const repoUrl = "https://github.com/jianzhnie/jianzhnie.github.io.git";
const distDir = "dist";

console.log("Deploying dist/ to GitHub Pages...");

execSync(
  `rm -rf ${distDir}/.git && cd ${distDir} && git init && git checkout -b main && git add -A && git commit -m "deploy" && git push -f ${repoUrl} main`,
  { stdio: "inherit" }
);

console.log("Deployed!");
